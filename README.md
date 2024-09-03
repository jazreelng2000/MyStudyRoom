# MyStudyRoom
This is an IoT application that is used for constructing a conducive environment for studying and it is mainly targeted on students who study at home. The application is divided into 4 parts, which are temperature and humidity program, light program, laptop viewing distance program, and scheduling program. 

Check out the Wiki tab for our documentation on its set-up. We also have a video demonstration and walkthrough [here.](https://www.youtube.com/watch?v=3Ot7J2-nlC8)

## Program Features
* **Temperature and Humidity Program**
<br> The main goal of this program is to maintain room temperature and humidity at a certain range, where the range can be defined by the user. The program will change the RGB LED light to different colours according to the current temperature and humidity status to warn the user. To give more details on the event where the temperature and humidity are not within the normal range, the program will send an alert message with details such as detection date and current temperature or humidity status to the user through Telegram. With this Telegram alert message, the user can be alerted even if they are not in the room as well.

* **Light Program**
<br> This program is to protect the users' eyes when they are studying. It provides an option to turn on and turn off the LED light so that user can turn it off when not using it. When the LED light is turned on, the website will show the current brightness value of the room received from the LDR sensor. The LED light will automatically adjust its brightness according to the current brightness value too.

* **Laptop Viewing Distance Program**
<br> Similar to the light program, this program is used for protecting the users' eyes while using laptop by monitoring the laptop viewing distance. It provides an option to turn off monitoring mode so that the user can stop monitoring when they are not using their laptop. When the monitoring mode is on, the buzzer will ring if the laptop viewing distance is lower than 25cm to alert the user. The buzzer will only stop ringing when the distance is back to above 25cm.

* **Scheduling Program**
<br> With this program, users can use to set alarms for when they want to study. The schedules can be added through a form on the website and after running the scheduler program and waiting for the alarm time to reach, the AWS Polly service will be used to say the name of the schedule as well as the current time to alert the user.

## Team Member
Jazreel Ng Wen Shin <br>
Lim Shu Fen
