import RPi.GPIO as GPIO
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
import serial
import sys

# clean up All GPIO on RPI
def cleanGPIO():
  GPIO.cleanup()

# connect to arduino
def setupArduino():
  ser=serial.Serial("/dev/ttyUSB0",9600)  #change ACM number as found from ls /dev/tty/ACM*
  ser.baudrate=9600
  return ser

# disconnect from arduino
def disconnectArduino(ser):
  ser = setupArduino()
  ser.write(b"PROGRAM END\n")

# connect to aws
def setupAWS(pubsub):
  host = "a26XXXXXXXXmrk-ats.iot.us-east-1.amazonaws.com"
  rootCAPath = "rootca.pem"
  certificatePath = "certificate.pem.crt"
  privateKeyPath = "private.pem.key"

  my_rpi = AWSIoTMQTTClient(pubsub)
  my_rpi.configureEndpoint(host, 8883)
  my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

  my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
  my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
  my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
  my_rpi.configureMQTTOperationTimeout(5)  # 5 sec

  return my_rpi




