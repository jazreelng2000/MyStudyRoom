import sys
from datetime import datetime
from time import sleep, time
import Adafruit_DHT
import RPi.GPIO as GPIO
from gpiozero import Buzzer
import telepot
import boto3
from boto3.dynamodb.conditions import Key, Attr
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
import utils
import serial
from multiprocessing import Process
import random

start_light_program = False
start_distance_program = False

def customCallback(client, userdata, message):
  if message.topic == "operation/light":
    print(message.payload)
    print(type(message.payload))
    global start_light_program
    if str(message.payload) == "startlight":
      start_light_program = True
    if str(message.payload) == "stoplight":
      start_light_program = False

  if message.topic == "operation/distance":
    print(message.payload)
    print(type(message.payload))
    global start_distance_program
    if str(message.payload) == "startdistance":
      start_distance_program = True
    if str(message.payload) == "stopdistance":
      start_distance_program = False

########################### DHT SENSOR ###########################

# function for turning on different light
def blink(pin):
  GPIO.setmode(GPIO.BCM)      # define BCM numbering
  GPIO.setup(pin, GPIO.OUT)   # define pin as output
  GPIO.PWM(pin, 100)          # set to full brightness

def redOn(red):
  blink(red)

def greenOn(green):
  blink(green)

def blueOn(blue):
  blink(blue)

def yellowOn(red,green):
  blink(red)
  blink(green)

# function for sending alert message to user
def sendAlertSMS(type, date_time, currvalue, lowestvalue, highestvalue):
  # define telegram bot token and chat ID
  my_bot_token = '104XXXXXXXXXXXXXXXXXXXXXXXXXXXAU5Y'
  chat_id = 6XXXXXXX6
  bot = telepot.Bot(my_bot_token)

  # as we allow user to define same value (both lowest and higest value) for normal range
  # we will check whether the value is the same before deciding the range value to be displayed
  normalrange = ""
  if lowestvalue == highestvalue:
    normalrange = str(lowestvalue)
  else:
    normalrange = str(lowestvalue) + " - " + str(highestvalue)

  # check whether the current value (for temperature or humidity) is higher or lower than normal range 
  # to decide the title for the alert message
  title = ""
  if int(currvalue) < lowestvalue:
    title = "Low " + type + " detected!!"
  if int(currvalue) > highestvalue:
    title = "High " + type + " detected!!"

  # send alert message if humidity/temperature is NOT in normal range
  sms = "ALERT MESSAGE\n\n" + title + "\n\nDate and Time: " + date_time + \
        "\nCurrent " + type + ": " + currvalue + \
        "\nNormal " + type + " Range: " + normalrange
  bot.sendMessage(chat_id, sms)

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
    datetime = item["lastupdated_datetime"]
    low_t = int(item["lowest_t"])
    high_t = int(item["highest_t"])
    low_h = int(item["lowest_h"])
    high_h = int(item["highest_h"])
  # return the retreived data
  return low_t, high_t, low_h, high_h

# main function for dht program
def dhtmain():
  # define pins
  dhtpin = 16
  red = 23
  green = 24
  blue = 25

  # connect to aws
  my_rpi = utils.setupAWS("MyStudyRoom-RPI-dht")
  my_rpi.connect()

  update = True
  while update:
    try:     
      # get the values needed (current temperature,humidity and datetime)
      #humidity, temperature = Adafruit_DHT.read_retry(11, dhtpin)
      humidity, temperature = random.randint(50,55), random.randint(24,26)
      n = datetime.now()
      date_time = n.strftime("%Y-%m-%d %H:%M:%S") # type:string
      humidity = int(humidity)                    # type:int
      temperature = int(temperature)              # type:int
      lightcolour = ""                            # type:string
      
      # retreive normal range from dynamodb
      lowest_t, highest_t, lowest_h, highest_h = normalrange()

      # check whether the current temperature and humidity value is in normal range
      # change the colour for RGB LED and send alert message if needed
      # if both humidity and temperature NOT in normal range, turn on RED light, send alert messages
      if (humidity < lowest_h or humidity > highest_h) and (temperature < lowest_t or temperature > highest_t):
        lightcolour = "red"
        GPIO.setwarnings(False)
        utils.cleanGPIO()
        redOn(red)
        sendAlertSMS("humidity", date_time, str(humidity), lowest_h, highest_h)     
        sendAlertSMS("temperature", date_time, str(temperature), lowest_t, highest_t)

      # if only humidity NOT in normal range, turn on BLUE light, send alert message
      elif humidity < lowest_h or humidity > highest_h:
        lightcolour = "blue"
        GPIO.setwarnings(False)
        utils.cleanGPIO()
        blueOn(blue)
        sendAlertSMS("humidity", date_time, str(humidity), lowest_h, highest_h) 

      # if only temperature NOT in normal range, turn on YELLOW light, send alert message
      elif temperature < lowest_t or temperature > highest_t:
        lightcolour = "yellow"
        GPIO.setwarnings(False)
        utils.cleanGPIO()
        yellowOn(red,green)
        sendAlertSMS("temperature", date_time, str(temperature), lowest_t, highest_t)

      # if both humidity and temperature in normal range, turn on GREEN light
      else:
        lightcolour = "green"
        GPIO.setwarnings(False)
        utils.cleanGPIO()
        greenOn(green)
    
      # publish message to sensors/dht topic and save to dynamodb
      message = {}
      message["deviceid"] = 1
      message["datetime"] = date_time
      message["humidity"] = humidity
      message["temperature"] = temperature
      message["rgbled_colour"] = lightcolour
      my_rpi.publish("sensors/dht", json.dumps(message), 1)
      print(message)

      sleep(1800) # loop every 30 minutes
    except KeyboardInterrupt:
      update = False
      utils.cleanGPIO()

########################### LDR SENSOR ###########################

# main function for light program
def lightmain():
  # send message to arduino to start retreiving ldr value
  ser = utils.setupArduino()

  # connect to aws
  my_rpi = utils.setupAWS("MyStudyRoom-RPI-light")
  my_rpi.connect()

  update = True
  while update:
    try:
      # subscribe to topic to check whether the on or off LED button is pressed
      my_rpi.subscribe("operation/light", 1, customCallback)
      global start_light_program

      # if on led button is pressed, start program in arduino
      if start_light_program == True:
        ser.write(b"PROGRAM START\n")
        ser.flush()
        # if there's message from arduino
        if ser.in_waiting > 0:
          light_value = int(ser.readline())           # type: int
          n = datetime.now()
          date_time = n.strftime("%Y-%m-%d %H:%M:%S") # type:string
          
          # publish message to sensors/light topic and save to dynamodb
          message = {}
          message["deviceid"] = 1
          message["datetime"] = date_time
          message["lightvalue"] = light_value
          my_rpi.publish("sensors/light", json.dumps(message), 1)
          print(message)       
      
      # if off led button is pressed, stop program in arduino
      if start_light_program == False:
        ser.write(b"OFFLED\n")
          
      sleep(1)  # loop every second
    except KeyboardInterrupt:
      start_light_program = False
      utils.cleanGPIO()

####################### ULTRASONIC SENSOR ######################

# main function for distance program
def distancemain():
  # setup pins for ultrasonic sensor and buzzer
  TRIG = 17
  ECHO = 27
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(TRIG,GPIO.OUT)
  GPIO.setup(ECHO,GPIO.IN)
  bz = Buzzer(22)

  # connect to aws
  my_rpi = utils.setupAWS("MyStudyRoom-RPI-distance")
  my_rpi.connect()

  update = True
  while update:
    try:
      # subscribe to topic to check whether the start or stop monitoring button is pressed
      my_rpi.subscribe("operation/distance", 1, customCallback)
      global start_distance_program

      # if start monitoring button is pressed, start program
      if start_distance_program == True:
        # get the values needed (current distance value and datetime)
        GPIO.output(TRIG, True)
        sleep(0.00001)
        GPIO.output(TRIG, False)

        while GPIO.input(ECHO)==0:
          pulse_start = time()
        while GPIO.input(ECHO)==1:
          pulse_end = time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        distance = round(distance, 2)               # type: float
        n = datetime.now()
        date_time = n.strftime("%Y-%m-%d %H:%M:%S") # type:string

        # publish message to sensors/distance topic and save to dynamodb
        message = {}
        message["deviceid"] = 1
        message["datetime"] = date_time
        message["distance_cm"] = distance
        my_rpi.publish("sensors/distance", json.dumps(message), 1)
        print(message)
        
        # check whether the distance is lower than 25 cm
        # if distance lower than 25
        if distance <= 25:     
          # on buzzer
          bz.on()
          sleep(1)
          bz.off()
        # else off buzzer
        else:
          bz.off()

    except KeyboardInterrupt:
      start_distance_program = False
      utils.cleanGPIO()

if __name__ == '__main__':
  try:
    while True:
      # run three sensors program at the same time by using multiprocessing
      dhtmain = Process(name='dhtmain', target=dhtmain)
      lightmain = Process(name='lightmain', target=lightmain)       
      distancemain = Process(name='distancemain',target=distancemain) 
      dhtmain.start()
      lightmain.start()
      distancemain.start()     
      dhtmain.join()
      lightmain.join()
      distancemain.join()
  except:
    print("Exception")
    print(sys.exc_info()[0])
    print(sys.exc_info()[1])
    utils.disconnectArduino(utils.setupArduino()) # disconnect arduino
    utils.cleanGPIO() # clean gpio