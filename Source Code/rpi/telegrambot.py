import telepot
import trigger
import socket
import sys
import boto3
from time import sleep
from datetime import datetime

# Replace the following 2 with your own token & id
my_bot_token = '104XXXXXXXXXXXXXXXXXXXXXXXXXXXAU5Y'

def getFreq(recurrent_check, repeat_freq, custom_freq):
    if recurrent_check == 0:
        return "None"
    else:
        if repeat_freq == 'custom':
            return "Every %s" % custom_freq
        else:
            return "Every %s" % repeat_freq


def getTasks(chat_id):
    # Connect to 'schedules' table in dynamodb
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('schedules')

    # Response to get all rows in 'schedules'
    response = table.scan()
    items = response['Items']

    i = 0
    for item in items:
        i = i+1
        name = item["name"]
        description = item["description"]
        setdatetime = item["setdatetime"]
        recurrent_check = int(item["recurrent"])  # (check if they ticked recurrent or not)
        repeat_freq = item["repeatfreq"]  # (standard repeat)
        custom_freq = item["customfreq"]  # (custom repeat intervals)
        freq = getFreq(recurrent_check, repeat_freq, custom_freq)
        message = "Task %s: %s\nDescription: %s\nDatetime Set: %s\nRepetition: %s" % \
                  (i, name, description, setdatetime, freq)
        bot.sendMessage(chat_id, message)

def respondToMsg(msg):
    # This function handles how the telegram bot replies to messages.
    chat_id = msg['chat']['id']
    command = msg['text']

    print('Got command: {}'.format(command))

    if command == '/start':
        bot.sendMessage(chat_id, "Nice to meet you! Type /help for more information.")

    elif command == '/myschedules':
        bot.sendMessage(chat_id, "Getting your tasks...")
        getTasks(chat_id)

    elif command == '/help':
        bot.sendMessage(chat_id, "I will send users alert messages if the temperature and/or humidity is not within"
                                 " the normal range that is defined by the user. "
                                 "I will also alert users when their alarm is ringing.\n\n"
                                 "Some commands you can use with me:\n"
                                 "/myschedules: I will tell you about the schedules you have added in the database.\n"
                                 "/getchatid: I will send you the chat ID.")

    elif command == '/getchatid':
        reply = "Your chat ID is " + str(chat_id)
        bot.sendMessage(chat_id, reply)

    else:
        bot.sendMessage(chat_id, "Sorry, I don't understand.")

bot = telepot.Bot(my_bot_token)
bot.message_loop(respondToMsg)
print("Waiting for commands..")

while True:
    sleep(2)