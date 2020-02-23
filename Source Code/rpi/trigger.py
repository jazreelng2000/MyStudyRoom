from datetime import datetime
from gpiozero import Buzzer
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
from time import sleep
import os
import sys
import subprocess

def synthesize_text(task_name):
    # Create directory 'audio' if it doesn't exist
    if not os.path.exists('audio'):
        os.makedirs('audio')

    # Create a client using the credentials and region defined in the [default]
    # section of the AWS credentials file (~/.aws/credentials).
    session = Session(profile_name="default")
    polly = session.client("polly")
    # Get current time
    now = datetime.now()
    current_dt = now.strftime("%d %B %I %M %p")

    try:
        # Request speech synthesis
        response = polly.synthesize_speech(Text="It is now "+ current_dt + ".Your task "
                                                + task_name + " is due", OutputFormat="mp3",
                                           VoiceId="Joanna")
    except (BotoCoreError, ClientError) as error:
        # The service returned an error, exit gracefully
        print(error)
        sys.exit(-1)

    # Access the audio stream from the response
    if "AudioStream" in response:
        # Note: Closing the stream is important because the service throttles on the
        # number of parallel connections. Here we are using contextlib.closing to
        # ensure the close method of the stream object will be called automatically
        # at the end of the with statement's scope.
        # with closing(response["AudioStream"]) as stream:
        with closing(response["AudioStream"]) as stream:
            output = os.path.join("audio", "alarm")

            try:
                # Open a file for writing the output as a binary stream
                # with open(output, "wb") as file:
                with open("audio/alarm", "wb") as file:
                    file.write(stream.read())
            except IOError as error:
                # Could not write to file, exit gracefully
                print(error)
                sys.exit(-1)

    else:
        # The response didn't contain audio data, exit gracefully
        print("Could not stream audio")
        sys.exit(-1)

    # Play the audio using the platform's default player
    if sys.platform == "win32":
        os.startfile(output)
    else:
        # The following works on macOS and Linux. (Darwin = mac, xdg-open = linux).
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, output])

def alarm_sequence(task_name):
    # This is the job the schedulers in scheduler.py executes
    # Sounds the alarm
    bz = Buzzer(26)
    synthesize_text(task_name)
    bz.on()
    print("Buzzer off in 3 seconds")
    sleep(3)
    bz.off()
    print("Buzzer off")


