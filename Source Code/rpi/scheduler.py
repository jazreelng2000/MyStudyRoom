import sys
import boto3
import telepot
from time import sleep
from datetime import datetime
from trigger import alarm_sequence
from apscheduler.schedulers.background import BackgroundScheduler

# function for sending alert message to user
def sendAlertSMS(name):
    # define telegram bot token and chat ID
    my_bot_token = '104XXXXXXXXXXXXXXXXXXXXXXXXXXXAU5Y'
    chat_id = 6XXXXXXX6
    bot = telepot.Bot(my_bot_token)
    now = datetime.now()
    current_dt = now.strftime("%d %B %I:%M %p")

    # send alert message when job is due i.e. alarm is ringing
    sms = "Your alarm is ringing!\nTask due: " + name + "\nTime: " + current_dt
    bot.sendMessage(chat_id, sms)

def remove_schedule(device_id, setdatetime):
    # Connect to dynamoDB table 'schedules'
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('schedules')

    # Another response to delete the items with specified keys
    response = table.delete_item(
        Key={
            'deviceid': device_id,
            'setdatetime': setdatetime
        }
    )

def recurrent_job(name):
    # Schedulers execute this function when the set time is reached for recurrent tasks.
    # Start the alarm
    sendAlertSMS(name)
    alarm_sequence(name)

def job(device_id, name, setdatetime):
    # Schedulers execute this function when the set time is reached for non-recurrent tasks.
    # Start the alarm
    sendAlertSMS(name)
    alarm_sequence(name)
    # Remove schedule from schedules table
    remove_schedule(device_id, setdatetime)

def schedule_once(scheduler, device_id, name, setdatetime):
    # print("Starting one time scheduler")
    scheduler.add_job(job, 'date', args=(device_id, name, setdatetime), run_date=setdatetime)
    # print("Scheduled once")

def schedule_standard(scheduler, name, setdatetime, repeat_freq):
    # print("Starting standard scheduler")
    # Get the repeatfreq from database
    # print(repeat_freq)

    # Every minute
    if repeat_freq == "minute":
        scheduler.add_job(recurrent_job, 'interval', args=(name,), minutes=1, start_date=setdatetime)

    # Every hour
    if repeat_freq == "hour":
        scheduler.add_job(recurrent_job, 'interval', args=(name,), hours=1, start_date=setdatetime)

    # For daily
    if repeat_freq == "day":
        scheduler.add_job(recurrent_job, 'interval', args=(name,), days=1, start_date=setdatetime)
        # print("Scheduled a daily job")

    # For weekly
    if repeat_freq == "week":
        scheduler.add_job(recurrent_job, 'interval', args=(name,), weeks=1, start_date=setdatetime)
        # print("Scheduled a weekly job")

    # For monthly
    # Monthly periodicity is not recommended due to its potential to crash
    if repeat_freq == "month":
        scheduler.add_job(recurrent_job, 'interval', args=(name,), months=1, start_date=setdatetime)
        # print("Scheduled a monthly job")

    # For yearly
    # Yearly periodicity is not recommended due to its potential to crash
    if repeat_freq == "yearly":
        scheduler.add_job(recurrent_job, 'interval', args=(name,), years=1, start_date=setdatetime)
        # print("Scheduled a yearly job")


def schedule_custom(scheduler, name, setdatetime, custom_freq):
    # print("Starting custom scheduler")
    # Get the customfreq from database
    # print(custom_freq)
    # Split the custom freq
    after_split = custom_freq.split()
    custom_int = int(after_split[0])
    custom_interval = after_split[1]

    # For minutes
    if custom_interval == 'minutes':
        scheduler.add_job(recurrent_job, 'interval', args=(name,), minutes=custom_int, start_date=setdatetime)
        # print("Scheduled a job with custom minutes")

    # For hours
    if custom_interval == 'hours':
        scheduler.add_job(recurrent_job, 'interval', args=(name,), hours=custom_int, start_date=setdatetime)
        # print("Scheduled a job with custom hours")

    # For day intervals
    if custom_interval == 'days':
        scheduler.add_job(recurrent_job, 'interval', args=(name,), days=custom_int, start_date=setdatetime)
        # print("Scheduled a job with custom days")

    # For week intervals
    if custom_interval == 'weeks':
        scheduler.add_job(recurrent_job, 'interval', args=(name,), weeks=custom_int, start_date=setdatetime)
        # print("Scheduled a job with custom weeks")

    # For month intervals
    if custom_interval == 'months':
        scheduler.add_job(recurrent_job, 'interval', args=(name,), months=custom_int, start_date=setdatetime)
        # print("Scheduled a job with custom months")

    # For yearly intervals
    if custom_interval == 'years':
        scheduler.add_job(recurrent_job, 'interval', args=(name,), years=custom_int, start_date=setdatetime)
        # print("Scheduled a job with custom years")


def main():
    try:
        scheduler = BackgroundScheduler()
        print("Starting scheduler")
        scheduler.start()

        # Connect to dynamoDB table 'schedules'
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('schedules')

        while True:
            # Search db for the inputted row
            response = table.scan()
            items = response['Items']
            for item in items:
                #print(item)
                device_id = int(item["deviceid"])
                setdatetime = item["setdatetime"]
                name = item["name"]
                recurrent_check = int(item["recurrent"])
                custom_freq = item["customfreq"]
                repeat_freq = item["repeatfreq"]

                # Check the recurrency of the scheduled task
                if recurrent_check == 0:  # If not recurrent, schedule job once
                    schedule_once(scheduler, device_id, name, setdatetime)

                elif recurrent_check == 1:  # If it is recurrent, check for custom or standard frequency
                    if repeat_freq == "custom":
                        # print("Custom Frequency")
                        schedule_custom(scheduler, name, setdatetime, custom_freq)
                    else:  # If repeat_freq is a standard day/week/month/year
                        #print("Standard Frequency")
                        schedule_standard(scheduler, name, setdatetime, repeat_freq)

            # Print scheduled jobs after scheduling each time from incomingtasks
            sleep(2)
            scheduler.print_jobs()
            # To keep the update real-time, constantly remove and add jobs to act as a replacing mechanism
            scheduler.remove_all_jobs()

    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])


if __name__ == '__main__':
    main()
