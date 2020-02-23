// define pins and variables
#define LDRpin A0
int LEDpin = 6;
int LDRvalue = 0;
int LEDvalue = 0;

// set serial port for communication
void setup() {
  Serial.begin(9600); 
}

// loop to read LDR value every 2 seconds
void loop() {
  // read LDR value
  LDRvalue = analogRead(LDRpin);
  if (Serial.available() > 0) {    
    String data = Serial.readStringUntil('\n');

    if (data.equals("PROGRAM START")) {
      // print LDR value
      Serial.println(LDRvalue);
      // adjust LED brightness according to LDR value
      // by constraining and mapping the LDR value from range (0 - 1023) to range (255,0)
      LEDvalue = constrain(LDRvalue,0,1023);
      LEDvalue = map(LEDvalue,0,1023,255,0);

      // if LDR value > 950, adjust LED brightness, else, turn off LED
      if (LDRvalue > 950) {
        analogWrite(LEDpin,0);
      } else {
        analogWrite(LEDpin,LEDvalue);
      }
          
    }
    if (data.equals("OFFLED")) {
      analogWrite(LEDpin,0);
    }
    if (data.equals("PROGRAM END")) {
      analogWrite(LEDpin,0);
    }
  }
  delay(1000);
}
