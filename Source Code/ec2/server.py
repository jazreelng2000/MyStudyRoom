from flask import Flask, render_template, jsonify, request,Response, url_for,redirect,flash

import sys
import boto3
from boto3.dynamodb.conditions import Key, Attr
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

import json
import numpy
import datetime
import decimal

import gevent
import gevent.monkey
from gevent.pywsgi import WSGIServer

gevent.monkey.patch_all()

host = "a26XXXXXXXXmrk-ats.iot.us-east-1.amazonaws.com"
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"

dht_topic_dt = ""
dht_topic_temp = 0
dht_topic_hum = 0
light_topic = 0
distance_topic = 0

my_rpi = AWSIoTMQTTClient("MyStudyRoom-server1")
my_rpi.configureEndpoint(host, 8883)
my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
my_rpi.configureMQTTOperationTimeout(5)  # 5 sec

my_rpi.connect()

class GenericEncoder(json.JSONEncoder):
    
    def default(self, obj):  
        if isinstance(obj, numpy.generic):
            return numpy.asscalar(obj) 
        elif isinstance(obj, datetime.datetime):  
            return obj.strftime('%Y-%m-%d %H:%M:%S') 
        elif isinstance(obj, datetime.date):  
            return obj.strftime('%Y-%m-%d') 
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:  
            return json.JSONEncoder.default(self, obj)

def data_to_json(data):
    json_data = json.dumps(data,cls=GenericEncoder)
    #print(json_data)
    return json_data

def customCallback(client, userdata, message):
    msg = json.loads(message.payload)
    if message.topic == "sensors/dht":
        global dht_topic_dt
        global dht_topic_temp
        global dht_topic_hum
        dht_topic_dt = str(msg.get("datetime", ""))
        dht_topic_temp = msg.get("temperature", 0)
        dht_topic_hum = msg.get("humidity", 0)
        print(dht_topic_dt)
        print(dht_topic_temp)
        print(dht_topic_hum)
    
    if message.topic == "sensors/light":
        global light_topic
        light_topic = msg.get("lightvalue", 0)

    if message.topic == "sensors/distance":
        global distance_topic
        distance_topic = msg.get("distance_cm", 0)

#################### Used for incoming tasks table ############################
def fetch_fromdb_as_json_incoming(items):

    try:
        data = {'data': items}
        json_data = json.dumps(data, indent=4, cls=GenericEncoder)
        #print(json_data)
        return json_data

    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        return None

def get_dht_data_from_dynamodb():
    try:
        # connect to 'dht_values' table in dynamodb
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('dht_values')
        response = table.query(
            KeyConditionExpression=Key('deviceid').eq(1), ScanIndexForward=False
        )
        # retreive the 10 latest records
        items = response['Items']
        n = 10  # limit to last 10 items
        data = items[:n]
        data_reversed = data[::-1]
        return data_reversed
    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])

def get_distance_data_from_dynamodb():
    try:
        # connect to 'distance_values' table in dynamodb
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('distance_values')
        startdate = str(datetime.date.today())
        response = table.query(
            KeyConditionExpression=Key('deviceid').eq(1) & Key('datetime').begins_with(startdate),
            ScanIndexForward=False
        )
        items = response['Items']
        count = response['Count']

        # if the items retreived are more than 10
        if count > 10:
            n = 10  # limit to last 10 items
            data = items[:n]
            data_reversed = data[::-1]
            return data_reversed
        # if the items retreived are lesser than 10
        else:
            data_reversed = items[::-1]
            return data_reversed
    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])

# retreive dht normal range from dynamodb
def normalrange():
    # Connect to 'dht_option' table in dynamodb
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('dht_option')
    response = table.query(
            KeyConditionExpression=Key('deviceid').eq(1), ScanIndexForward=False
    )
    # retreive the latest record of dht normal range
    items = response['Items']
    items = items[:1]
    for item in items:
        dt = item["lastupdated_datetime"]
        lowest_t = int(item["lowest_t"])
        highest_t = int(item["highest_t"])
        lowest_h = int(item["lowest_h"])
        highest_h = int(item["highest_h"])

    # check whether the lowest and highest value is the same and save the range into variables 
    temprange = ""
    humidrange = ""
    if lowest_t == highest_t:
        temprange = str(lowest_t)
    else:
        temprange = str(lowest_t) + "-" + str(highest_t)
    if lowest_h == highest_h:
        humidrange = str(lowest_h)
    else:
        humidrange = str(lowest_h) + "-" + str(highest_h)
        
    # return the retreived data
    return dt, temprange, humidrange

app = Flask(__name__)

######################### For DHT Box ##############################
@app.route("/getdhtrealtime",methods = ['POST', 'GET'])
def getdhtvalue():
    # retreive latest record from 'dht_option' table in dynamodb
    dt, temprange, humidrange = normalrange()
    # get sensor data from topic
    my_rpi.subscribe("sensors/dht", 1, customCallback)
    global dht_topic_dt
    global dht_topic_temp
    global dht_topic_hum
    dhtdata = {'dhtdatetime':dht_topic_dt,'temperature':dht_topic_temp,'humidity': dht_topic_hum,'temprange': temprange,'humidrange': humidrange}
    return jsonify(dhtdata)

################### For Current Light Value Box ##########################
@app.route("/getlightrealtime",methods = ['POST', 'GET'])
def getlightrealtime():
    # publish message to topic to start light program
    my_rpi.publish("operation/light", "startlight", 1)
    # get sensor data from topic
    my_rpi.subscribe("sensors/light", 1, customCallback)
    global light_topic
    lightdata = {'lightvalue':light_topic}    
    return jsonify(lightdata)

@app.route("/writeLED/<status>")
def writePin(status):
    if status == 'ON':
        response = "ON"
    else:
        # publish message to topic to stop light program
        my_rpi.publish("operation/light", "stoplight", 1)
        response = "OFF"
    return response

################### For Laptop Viewing Distance Box ###################
@app.route("/getdistancerealtime",methods = ['POST', 'GET'])
def getdistancevalue():
    # publish message to topic to start distance program
    my_rpi.publish("operation/distance", "startdistance", 1)
    # get sensor data from topic
    my_rpi.subscribe("sensors/distance", 1, customCallback)
    global distance_topic
    distancedata = {'distance':distance_topic}
    return jsonify(distancedata)

@app.route("/monitor/<status>")
def distancemonitorstatus(status):
    if status == 'ON':
        response = "ON"
    else:
        # publish message to topic to stop distance program
        my_rpi.publish("operation/distance", "stopdistance", 1)
        response = "OFF"
    return response

######################### For DHT chart ##############################
@app.route("/api/getdhtdata",methods = ['POST', 'GET'])
def apidata_getdhtdata():
    if request.method == 'POST':
        try:
            data = {'chart_data': data_to_json(get_dht_data_from_dynamodb()), 'title': "dht data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])
    

######################### For distance chart ############################
@app.route("/api/getdistancedata",methods = ['POST', 'GET'])
def apidata_getdistancedata():
    if request.method == 'POST':
        try:
            data = {'chart_data': data_to_json(get_distance_data_from_dynamodb()), 'title': "distance data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])


############ Get table from DB for manageschedules.html ################
@app.route("/api/getincomingtasks", methods=['POST', 'GET'])
def apidata_getincoming():
    # Display incomingtasks
    if request.method == 'POST':
        try:
            # Connect to 'schedules' table in dynamodb
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table('schedules')

            # Response to get all rows in 'schedules'
            response = table.scan()
            items = response['Items']
            json_data = fetch_fromdb_as_json_incoming(items)
            loaded_r = json.loads(json_data)

            data = {'chart_data': loaded_r, 'title': "IOT Data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])


################### Scheduling Form Handling #########################
@app.route("/api/insertdata", methods=['POST', 'GET'])
def getForm():
    # Allow users to add schedules through a form
    if request.method == 'POST':
        try:
            # Connect to 'schedules' table in dynamodb
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table('schedules')

            device_id = 1
            task_name = request.form['taskname']
            task_description = request.form['taskdescription']
            trigger_time = request.form['triggertime']
            recurrent_check = request.form['recurrentcheck']
            repeat_freq = request.form['repeatfreq']
            custom_number = request.form['recurrentint']
            custom_interval = request.form['recurrentfreq']

            # List of submissions gotten from form
            items = [task_name, task_description, trigger_time, recurrent_check, repeat_freq, custom_number,
                     custom_interval]
            encoded_items = []  # Create a new list for encoded strings
            for item in items:  # Encode each submission into utf8 and append to encoded_items
                utf8string = item.encode("utf-8")
                encoded_items.append(utf8string)

            # print(encoded_items)
            # Ensure if recurrent_check is unticked, all frequencies are nothing
            if encoded_items[3] == '0':
                encoded_items[4] = "none"
                encoded_items[5] = ""
                encoded_items[6] = "none"

                # Some form validation - Not really used but just in case
                if encoded_items[4] == "custom":
                    if encoded_items[5] == "":
                        print("Custom frequency checked but no integers entered.")
                        return redirect("/", code=302)
                    else:
                        print("No issues")
                else:
                    print("No issues")

            # Formats time from submission into datetime object
            formatted_time = datetime.datetime.strptime(encoded_items[2],
                                                        "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")

            # Combines custom_interval and custom_interval2 into custom_freq to place in database
            custom_freq = ("%s %s") % (str(encoded_items[5]), encoded_items[6])

            # Response to input item in db
            response = table.put_item(
                Item={
                    'deviceid': device_id,
                    'setdatetime': formatted_time,
                    'name': encoded_items[0],
                    'description': encoded_items[1],
                    'recurrent': encoded_items[3],
                    'repeatfreq': encoded_items[4],
                    'customfreq': custom_freq
                }
            )

            #print("Data inserted successfully.")
            #print(json.dumps(response, indent=4, cls=GenericEncoder))
            return redirect('/manageschedules')

        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])


@app.route("/api/deletetask", methods = ['POST', 'GET'])
def deleterow():
    if request.method == 'GET':
        try:
            # Get row of schedule user wants to delete
            row = int(request.args.get('row'))

            # Connect to dynamoDB table 'schedules'
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table('schedules')

            # Search db for the inputted row
            response = table.scan()
            items = response['Items']
            item = (items[row])
            # Get the keys
            deviceid = item["deviceid"]
            setdatetime = item["setdatetime"]

            # Another response to delete the items with specified keys
            response = table.delete_item(
                Key={
                    'deviceid': deviceid,
                    'setdatetime': setdatetime
                }
            )

            #print("DeleteItem succeeded:")
            #print(json.dumps(response, indent=4, cls=GenericEncoder))
            return redirect('/manageschedules')

        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])


########################### index.html ##############################
@app.route("/")
def index():
    return render_template('index.html')


########################## addschedule.html #############################
@app.route("/addschedule")
def addschedule():
    return render_template('addschedule.html')


########################## manageschedules.html #############################
@app.route("/manageschedules")
def manageschedules():
    return render_template('manageschedules.html')


####### For changing html page after clicking "change" button in index.html ############
@app.route("/changeoption", methods=['POST', 'GET'])
def changeoption():
    # retreive latest record from 'dht_option' table in dynamodb
    dt, temprange, humidrange = normalrange()
    # refer user to changeoption.html and return the normal range data there
    return render_template('changeoption.html', dt=dt, temprange=temprange, humidrange=humidrange)


########################## DHT Form Handling #############################
@app.route("/", methods=['POST'])
def processoption():
    # get the variable to be saved into dynamodb
    n = datetime.datetime.now()
    date_time = n.strftime("%Y-%m-%d %H:%M:%S")  # type:string
    dt = str(date_time)
    low_t = int(request.form['low_t'])
    high_t = int(request.form['high_t'])
    low_h = int(request.form['low_h'])
    high_h = int(request.form['high_h'])
    
    # connect to 'dht_option' table in dynamodb
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('dht_option')

    msg = None
    error = None
    # validate user input
    # if the lowest value is higher than highest value, redirect user back to changeoption.html and display error msg
    if (low_t > high_t) or (low_h > high_h):
        error = "Failed to make changes. The lowest value must lower than or equal to highest value. Please try again."
    else:
        # else if correct, save the data to dynamodb
        response = table.put_item(
            Item={
                'deviceid': 1,
                'lastupdated_datetime': dt,
                'lowest_t': low_t,
                'highest_t': high_t,
                'lowest_h': low_h,
                'highest_h': high_h
            }
        )
        # redirect user back to index.html and display msg indicates changes are made successfully
        msg = "Changes on normal range (temperature and humidity) were saved successfully!"
        return render_template('index.html', msg=msg)

    return render_template('index.html', error=error)

if __name__ == '__main__':
    try:
        print('Server waiting for requests')
        http_server = WSGIServer(('0.0.0.0', 8001), app)
        app.debug = True
        http_server.serve_forever()
    except:
        print("Exception")
        import sys
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])