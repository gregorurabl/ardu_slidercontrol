/* Slider Control V2.1 for 3.5" Parallel TFT-tft Shield Display with Adafruit_GFX
// Loosely based on a Project by Mega-Testberichte.de - Marco Kleine-Albers
// Variant for Adafruit TFT & Moba Tools by Gregorurabl.at - Gregor Urabl
// Optimized for Rollei/iFootage Shark S1 Slider & Stepperonline 17HS19-1684s-PG14 Planetary Geared Stepper Motor

//1,8°, 360/1,8 = 200
//200 steps is a full turn in fullstep mode
//use microstepping for smoother motion. see later in code

Standard TFT tft Pin Mappings:

*pin usage as follow:
*                  tft_CS  tft_CD  tft_WR  tft_RD  tft_RST  SD_SS  SD_DI  SD_DO  SD_SCK 
*     Arduino Uno    A3      A2      A1      A0      A4      10     11     12      13   
                         
*Arduino Mega2560    A3      A2      A1      A0      A4      10     11     12      13                           

*                  tft_D0  tft_D1  tft_D2  tft_D3  tft_D4  tft_D5  tft_D6  tft_D7  
*     Arduino Uno    8       9       2       3       4       5       6       7
*Arduino Mega2560    8       9       2       3       4       5       6       7 

*Remember to set the pins to suit your display module!
*/

#include <Adafruit_GFX.h> // Core graphics library
#include <Adafruit_TFTLCD.h> // tft Library
#include <TouchScreen.h> // Touchscreen Library
#include <MCUFRIEND_kbv.h> // Touchscreen Hardware-specific library
#include <MobaTools.h> // Motor Control Library

// Colors
#define BLACK       0x0000
#define WHITE       0xFFFF
#define RED         0xF800
#define GREEN       0x07E0
#define BLUE        0x001F
#define ORANGE      0xFD20      
#define DARKCYAN    0x03EF      
#define DARKGREY    0x7BEF   
#define LIGHTGREY   0xC618     

//debug/msg
int x, y;
String msg="";
char text_buffer[80];

//////////////////////////////////
// Serial Communication Setup
//////////////////////////////////
const unsigned int MAX_MESSAGE_LENGTH = 100;
char *token;
const char *delimiter_comma =",";
const char *delimiter_dots =":";

String serialControlMessage[6];
String serialControlValues[6];

//////////////////////////////////
// Optional Sonar Module Setup - Module works as emergency break in Normal & Manual Mode and stops the motor before the slider crashes. Requires attached Sensor Module and Obstacle at End of Slider.
//////////////////////////////////
#include <NewPing.h>

#define TRIGGER_PIN   47 // Arduino pin tied to trigger pin on ping sensor. BROWN / Also used for Camera Trigger
#define ECHO_PIN      49 // Arduino pin tied to echo pin on ping sensor. BLACK
#define MAX_DISTANCE 200 // Maximum distance we want to ping for (in centimeters). Maximum sensor distance is rated at 400-500cm.

/*
White -> gnd
49 Black -> Echo
47 Brown -> Trig
Red -> vcc

OR for Camera Module:
47 Brown/Trigger -> Camera Trigger
GND -> Camera GND
*/

NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE); // NewPing setup of pins and maximum distance.

unsigned int pingSpeed = 50; // How frequently are we going to send out a ping (in milliseconds). 50ms would be 20 times a second.
unsigned long pingTimer;     // Holds the next ping time.
boolean sonar_attached = false;

//////////////////////////////////
// Camera Module Setup
//////////////////////////////////
boolean camera_attached = false;
unsigned long camera_trigger_duration = 100; // Camera trigger pulse duration in ms (adjustable based on camera requirements)
int photo_counter = 0; // Counter for triggered photos

//////////////////////////////////
// Screen Setup
//////////////////////////////////

#define tft_CS A3 // Chip Select goes to Analog 3
#define tft_CD A2 // Command/Data goes to Analog 2
#define tft_WR A1 // tft Write goes to Analog 1
#define tft_RD A0 // tft Read gies to Analog 0

#define tft_RESET A4 // Can alternately just connect to Arduino's reset pin

// define pins for resistive touchscreen
#define YP A1 // must be an analog pin, use "an" notation!
#define XM A2 // must be an analog pin, use "an" notation!
#define YM 7 // can be a digital pin
#define XP 6 // can be a digital pin

// define touchscreen pressure points
#define MINPRESSURE 10
#define MAXPRESSURE 1000

// Define touchscreen parameters
// Use test sketch to refine if necessary
#define TS_MINX 930
#define TS_MAXX 130
 
#define TS_MINY 200
#define TS_MAXY 970
 
#define STATUS_X 10
#define STATUS_Y 65

MCUFRIEND_kbv tft; // Define object for TFT display
TouchScreen ts = TouchScreen(XP, YP, XM, YM, 300); // Define object for touchscreen / Last parameter is X-Y resistance, measure or use 300 if unsure

//////////////////////////////////
// Motor Setup
//////////////////////////////////

//motor pins
int ENABLE_PIN = 23;
int STEP_PIN = 25;
int DIR_PIN = 27;
int stepsPerRev = 3200; // 360°/1.8° = 200 Steps x 16 Microsteppint = 3200 Microsteps/Rev

//microstepping Pins M1 =A8, M2=A9, M3=A10
//TABELLE, Abschnitt Software: https://www.mega-testberichte.de/testbericht/einen-kameraslider-motorisieren-arduino-a4988-steppermotor-touchdisplay-do-it-yourself
//pin mappings 
int M1 = A8;
int M2 = A9;
int M3 = A10;

MoToStepper stepper (stepsPerRev, STEPDIR);
MoToTimer stepperPause;   // Pause between stepper moves for timelapse
short motorDirection = 1; // clockwise

//--basic values for movement
int speed_set = 600;
int raise_speed_by = 60;
int speed_max = 1200; // -> 10.000 with Microstepping. -> 1.200 without Microstepping
long distance_set = 17000;
int raise_distance_by = 1000;
int ramp_set = 0;
short ramp_steps_by = 100;

//--"more special" variables 
bool return_to_home = false;
bool manual_start_or_stop = true; // true == start, false = stop
short distance_special_select = 1; // 1 = all normal Distances, 2 = Short Slider Length, 3 = Long Slider Length
bool stepperRunning;
long currentPos = 0;

//--needed for timelapse, buttons
long time_set = 0; 
short raise_time_by = 1;
int time_max = 900; // 15min
long ms_time = 0;

//--subdivisions for timelapse
int steps_set = 2; // Divider for Stops. So minimum drive half of the distance, stop, wait for delay, drive to end. Distance between stops is distance_set/steps_set
short steps_max = 1000; // Maximum subdivisions for timelapse system. Arbitrary number, choose to your liking
short raise_steps_by = 1;
int steps_count = 0;

//--slider length in steps
long slider_length_long = 36000; 
long slider_length_short = 18000;

//////////////////////////////////
//  Draw UI  
//////////////////////////////////

char buttonRadius = 10;
char buttonHeight = 60;
char buttonSpacing = 10;
uint16_t smallButtonWidth = 147;
uint16_t bigButtonWidth = 303;

// Define button array object
Adafruit_GFX_Button buttons[11];

  void drawButtons() {

// Create Buttons - initButton would create a Button from x and y coordinates in it's center. initButtonUL uses the top left corner
     buttons[0].initButtonUL(&tft, buttonSpacing, buttonSpacing, bigButtonWidth, buttonHeight, WHITE, DARKCYAN, WHITE, "NORMAL", 3); // NORMAL Button
        int speed_percentage = speed_set/12;
        int_to_string(speed_percentage, text_buffer); 
        sprintf(text_buffer,"%s%s",text_buffer,"%");
     buttons[1].initButtonUL(&tft, bigButtonWidth+2*buttonSpacing, buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, text_buffer, 3); // SPEED Button (set number)
     buttons[2].initButtonUL(&tft, buttonSpacing, buttonHeight+2*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, RED, WHITE, "MANUAL", 3); // MANUAL Button
     buttons[3].initButtonUL(&tft, 2*buttonSpacing+smallButtonWidth, buttonHeight+2*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, "RTH", 3); // RTH Button
          int_to_string(distance_set, text_buffer); 
     buttons[4].initButtonUL(&tft, 2*smallButtonWidth+3*buttonSpacing, 1*buttonHeight+2*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, text_buffer, 3); // DIST Button (set number)
     buttons[5].initButtonUL(&tft, buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, "-->|", 3); // RETURN Button          
     buttons[6].initButtonUL(&tft, smallButtonWidth+2*buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE,"<<" , 3); // DIRECTION Button 
     int_to_string(ramp_set, text_buffer);  
     buttons[7].initButtonUL(&tft, 2*smallButtonWidth+3*buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, text_buffer, 3);// RAMP Button (set number)
     buttons[8].initButtonUL(&tft, buttonSpacing, 3*buttonHeight+4*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, ORANGE, WHITE, "TIMELAP", 3);// TIMELAPSE START Button
          int_to_string(time_set*1000, text_buffer);  
     buttons[9].initButtonUL(&tft, smallButtonWidth+2*buttonSpacing, 3*buttonHeight+4*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, ORANGE, WHITE, text_buffer, 3);// DELAY Button (set number)
          int_to_string(steps_set, text_buffer);  
     buttons[10].initButtonUL(&tft, 2*smallButtonWidth+3*buttonSpacing, 3*buttonHeight+4*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, ORANGE, WHITE, text_buffer, 3); // STEPS Button (set number)

// Draw Buttons
        for(uint8_t buttonCounter = 0; buttonCounter <= 10; buttonCounter++) 
        {
        buttons[buttonCounter].drawButton();
        }

// Draw Info Texts for set number Buttons

    tft.setTextSize(1);
    tft.setTextColor(WHITE); 

    tft.setCursor(bigButtonWidth+2*buttonSpacing+60,buttonSpacing+5);  tft.print("SPEED");
    tft.setCursor(bigButtonWidth+2*buttonSpacing+50,2*buttonSpacing+buttonHeight+5);  tft.print("DISTANCE");  
    tft.setCursor(bigButtonWidth+2*buttonSpacing+60,3*buttonSpacing+2*buttonHeight+5);  tft.print("RAMP");  
    tft.setCursor(bigButtonWidth+2*buttonSpacing+40,4*buttonSpacing+3*buttonHeight+5);  tft.print("SUBDIVISIONS");  
    tft.setCursor(smallButtonWidth+2*buttonSpacing+60,4*buttonSpacing+3*buttonHeight+5);  tft.print("DELAY");  

    tft.fillRect(0, tft.height()-30, tft.width(), 30, LIGHTGREY); // Infobar
}

/*************************
**  Required functions  **
*************************/
void setup() {  

tft.reset();

  // basic motor setup
/*
  // Microstepping - disabled due to the use of Planetary Gear. Enable it, if you are using a "normal" stepper motor.
  pinMode(M1, OUTPUT);
  pinMode(M2, OUTPUT);
  pinMode(M3, OUTPUT);

  //see table for step values: https://lastminuteengineers.com/a4988-stepper-motor-driver-arduino-tutorial/
  digitalWrite(M1, HIGH);
  digitalWrite(M2, HIGH);
  digitalWrite(M3, HIGH);
  */
  stepper.attach( STEP_PIN, DIR_PIN );
  stepper.attachEnable (ENABLE_PIN,1,LOW); // Set Enable Pin and Turn of Motor per Default

  // Setup the Display
  tft.begin(tft.readID());
  tft.setRotation(1);
  tft.fillScreen(BLACK);

  //call function to draw our gui  
  drawButtons();
  
  Serial.begin(115200); 
  Serial.println("Starting Slider Control V2.1 by Gregor Urabl \r\n");  
  Serial.print("TFT size is "); Serial.print(tft.width()); Serial.print("x"); Serial.println(tft.height());
  
    stepperRunning = true;
    stepper.setZero(0); //set current Position as 0 
    pingTimer = millis(); // Start Timer
    photo_counter = 0; // Reset photo counter

   // Detection of attached module - Sonar or Camera
   if(sonar.ping(MAX_DISTANCE)!=0){ // Make one Ping on max Distance to test if ultrasonic module is attached
      tft.fillRect(tft.width()-10, 0, 10, 10, GREEN); // Green Bar shows that Ultrasonic Sensor has been connected
      Serial.println("Sonar Module attached.");
      sonar_attached = true;
      camera_attached = false;
    } else {
      // If sonar test fails, assume camera module is attached
      pinMode(TRIGGER_PIN, OUTPUT); // Set trigger pin as output for camera
      digitalWrite(TRIGGER_PIN, HIGH); // Set default state to HIGH (open circuit)
      tft.fillRect(tft.width()-10, 0, 10, 10, BLUE); // Blue Bar shows that Camera Module has been connected
      Serial.println("Camera Module attached - Sonar test failed.");
      camera_attached = true;
      sonar_attached = false;
      }
}

void loop() {

// start optional sonar module
if (millis() >= pingTimer && sonar_attached == true) {   // pingSpeed milliseconds since last ping, do another ping.
    pingTimer += pingSpeed;      // Set the next ping time.
    sonar.ping_timer(echoCheck); // Send out the ping, calls "echoCheck" function every 24uS where you can check the ping status.
  }

    //touchscreen
  uint16_t i;
  digitalWrite(13, HIGH);
  TSPoint p = ts.getPoint();
  digitalWrite(13, LOW);

  pinMode(XM, OUTPUT);
  pinMode(YP, OUTPUT);
  if (p.z > MINPRESSURE && p.z < MAXPRESSURE)
  {

    p.x = map(p.x, TS_MINX, TS_MAXX, tft.width(),0);
    p.y = map(p.y, TS_MINY, TS_MAXY, tft.height(),0);

      //debug
      //check the area where we drew the buton for touch
      /*
      Serial.print("Touch X is:");
      Serial.print(p.x);
      Serial.print("\r\n");

      Serial.print("Touch Y is:");
      Serial.print(p.y);
      Serial.print("\r\n");*/

      //--------------------NORMAL button 
      if ((p.y >= 10) && (p.x >= 40) && (p.y <= 220) && (p.x <= 100) ) { 
      doNormalRun(speed_set,ramp_set,distance_set); //go to function, because this can also be triggered by Serial Communication
      }

      //--------------------SPEED button with UPDATE of number
     if ((p.y >= 240) && (p.x >= 40) && (p.y <= 330) && (p.x <= 110) ) {   

        //one touch raises speed by X up to "speed_max"
        if(speed_set < speed_max) {
          speed_set = speed_set + raise_speed_by;  
        }
        else {
          speed_set = 60;
        }       
        int speed_percentage = speed_set/12;
        int_to_string(speed_percentage, text_buffer); 
        sprintf(text_buffer,"%s%s",text_buffer,"%");
        buttons[1].initButtonUL(&tft, bigButtonWidth+2*buttonSpacing, buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, text_buffer, 3); // SPEED Button (set number)
        redrawButtons(1,bigButtonWidth+2*buttonSpacing+60,buttonSpacing+5,"SPEED");

        String speedMsg = "Speed set to ";
        speedMsg.concat(text_buffer);
        updateStr(speedMsg);
     }

      //--------------------MANUAL button
      if ((p.y >= 10) && (p.x >= 140) && (p.y <= 100) && (p.x <= 210) ) { 
      
      //Set Basic Speed and Acceleration/Ramp of each Steppers at startup
      stepper.setMaxSpeed(speed_set);
      stepper.setRampLen(ramp_set); 

      if(manual_start_or_stop == true){ //start run on first click   
      currentPos = stepper.currentPosition();
      updateStr("Manual Run");
      stepper.rotate(motorDirection);
      manual_start_or_stop = !manual_start_or_stop;
      }
      else{ // stop run on second click
         long traveled_distance = stepper.currentPosition()-currentPos;
         String traveledMsg = "Manual Run stopped after ";
            if(traveled_distance<0){traveled_distance*=-1;}
        traveledMsg.concat(traveled_distance);
        traveledMsg.concat(" Steps.");
        updateStr(traveledMsg);
        manual_start_or_stop = !manual_start_or_stop;
          if(return_to_home == true){          
                updateStr("Returning Home"); 
                stepper.moveTo(currentPos);            
          } else{stepper.stop();} //motor off 
          }
      }

         //--------------------RTH button
      if ((p.y >= 120) && (p.x >= 140) && (p.y <= 220) && (p.x <= 210) ) { 
          rth();
      }   

      //--------------------DISTANCE button with UPDATE of number
     if ((p.y >= 235) && (p.x >= 140) && (p.y <= 320) && (p.x <= 220) ) {   
        
        if(distance_special_select == 3) // Check if Slider was set to SHORT Distance on the last press. If so, reset the button back to Zero
          {
          distance_set = 0;
          int_to_string(distance_set, text_buffer); 
          distance_special_select = 1;
        }   
         else if(distance_set < slider_length_long-raise_distance_by) { // If the Button is not set to SHORT or LONG, one touch raises Distance by X up to Slider Length. As LONG is equivalent to  "slider_length_long" we have to break one "raise_distance_by" before that happens.
          distance_set = distance_set + raise_distance_by;  
          int_to_string(distance_set, text_buffer); 
          distance_special_select = 1;
          }
          else if(distance_set == slider_length_long-raise_distance_by && distance_special_select == 1) // If Distance is one step away from LONG, raise it one last time an set the special select var so we know to stop counting the normal way now
          {
            distance_set = slider_length_long;  
          strcpy(text_buffer,"LONG");
          distance_special_select = 2;
          }
          else if(distance_special_select == 2) // We are on LONG, show SHORT next.
          {
          strcpy(text_buffer,"SHORT");
          distance_set = slider_length_short;
          distance_special_select = 3;
          }
         
      buttons[4].initButtonUL(&tft, bigButtonWidth+2*buttonSpacing, 1*buttonHeight+2*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, text_buffer, 3); // DIST Button (set number)
      redrawButtons(4,bigButtonWidth+2*buttonSpacing+50,2*buttonSpacing+buttonHeight+5,"DISTANCE"); 

        String distMsg = "Travel Distance set to ";
        distMsg.concat(text_buffer);
        updateStr(distMsg);
     }

      //--------------------RETURN/ NO RETURN button
      if ((p.y >= 10) && (p.x >= 250) && (p.y <= 100) && (p.x <= 310) ) {   

      return_to_home = !return_to_home;

      if(return_to_home == true){
         buttons[5].initButtonUL(&tft, buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, "<-->", 3);
         buttons[5].drawButton();
         updateStr("Return Mode set to RETURN"); 
        } else{
         buttons[5].initButtonUL(&tft, buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, "-->|", 3);
         buttons[5].drawButton();
         updateStr("Return Mode set to SINGLE RUN");
        }

        }

      //--------------------DIRECTION button
      if ((p.y >= 125) && (p.x >= 245) && (p.y <=220) && (p.x <= 315) ) {   
        
        motorDirection *= -1; // invert it

        if(motorDirection == -1){
         buttons[6].initButtonUL(&tft, smallButtonWidth+2*buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE,">>" , 3); // DIRECTION Button 
         buttons[6].drawButton();
         updateStr("Direction set set to "); tft.write(0x10);tft.write(0x10);tft.write(" CW");
        } else{
         buttons[6].initButtonUL(&tft, smallButtonWidth+2*buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE,"<<" , 3); // DIRECTION Button 
         buttons[6].drawButton();
         updateStr("Direction set set to "); tft.write(0x11);tft.write(0x11);tft.write(" CCW");
        }
      
      }

      //--------------------RAMP button with UPDATE of number
      if ((p.y >= 235) && (p.x >= 250) && (p.y <=325) && (p.x <= 320) ) {
        //one touch raises Ramp by X up to (slider_length_long/2)
        if(ramp_set < distance_set/2) { 
          ramp_set = ramp_set + ramp_steps_by;  
        }
        else {
          ramp_set = 0;
        }        

        int_to_string(ramp_set, text_buffer); 
        buttons[7].initButtonUL(&tft, 2*smallButtonWidth+3*buttonSpacing, 2*buttonHeight+3*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, DARKGREY, WHITE, text_buffer, 3);// RAMP Button (set number)
        redrawButtons(7,bigButtonWidth+2*buttonSpacing+60,3*buttonSpacing+2*buttonHeight+5,"RAMP");

        String rampMsg = "Ramp set to ";
        rampMsg.concat(text_buffer);
        updateStr(rampMsg);
      }      

      //------------------------TIMELAPSE START button 
      if ((p.y >= 10) && (p.x >= 350) && (p.y <= 100) && (p.x <= 420) ) {          
      doTimelapse(speed_set, time_set, steps_set, distance_set);
      }     

      //------------------------DELAY button with UPDATE of number
      if ((p.y >= 125) && (p.x >= 360) && (p.y <= 220) && (p.x <= 420) ) {    // if ((p.y >= 125) && (p.x >= 360) && (p.y <= 220) && (p.x <= 420) ) { 

        //one touch raises time by X up to time_max
        if(time_set < time_max) {
          time_set = time_set + raise_time_by;  
          
        }
        else {
          time_set = 0;
        }             

        int_to_string(time_set, text_buffer); 
        buttons[9].initButtonUL(&tft, smallButtonWidth+2*buttonSpacing, 3*buttonHeight+4*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, ORANGE, WHITE, text_buffer, 3);// DELAY Button (set number)    
        redrawButtons(9,smallButtonWidth+2*buttonSpacing+60,4*buttonSpacing+3*buttonHeight+5,"DELAY"); 

        String timeMsg = "Delay for Timelapse set to ";
        timeMsg.concat(text_buffer);
        updateStr(timeMsg);
      }      

       //------------------------STEPS button with UPDATE of number 
      if ((p.y >= 230) && (p.x >= 360) && (p.y <= 310) && (p.x <= 410) ) {    
        //one touch raises steps by 1 up to steps_max
        if(steps_set < steps_max) {
          steps_set = steps_set + raise_steps_by;  
        }
        else {
          steps_set = 2;
        }       

        int_to_string(steps_set, text_buffer); 
        buttons[10].initButtonUL(&tft, 2*smallButtonWidth+3*buttonSpacing, 3*buttonHeight+4*buttonSpacing, smallButtonWidth, buttonHeight, WHITE, ORANGE, WHITE, text_buffer, 3); // STEPS Button (set number)
        redrawButtons(10,bigButtonWidth+2*buttonSpacing+40,4*buttonSpacing+3*buttonHeight+5,"SUBDIVISIONS"); 

        String stepsMsg = "Subdivisions set to ";
        stepsMsg.concat(text_buffer);
        updateStr(stepsMsg);
      }    
}

       //------------------------SERIAL REMOTE CONTROL
          while (Serial.available() > 0)  //Check to see if anything is available in the serial receive buffer
          {
            static char message[MAX_MESSAGE_LENGTH];    //Create a place to hold the incoming message
            static unsigned int message_pos = 0;
            char inByte = Serial.read();    //Read the next available byte in the serial receive buffer

            if ( inByte != '\n' && (message_pos < MAX_MESSAGE_LENGTH - 1) )    //Message coming in (check not terminating character) and guard for over message size
            {
              message[message_pos] = inByte;      //Add the incoming byte to our message
              message_pos++;
            }
            else    //Full message received...
            {
              message[message_pos] = '\0';      //Add null character to string
              //Serial.println(message); // The whole Message for DEBUG
            token = strtok(message, delimiter_comma);     // Get Tokens from whole String
            short countDummy = 0;

            while (token != NULL) {
                serialControlMessage[countDummy] = token;
                countDummy++;
                token=strtok(NULL, delimiter_comma);
            }
              message_pos = 0;      //Reset for the next message
            
              for(int i=0;i<=5;i++)
                  { //Save pure Values without Labels to new array
                    serialControlValues[i]= serialControlMessage[i].substring(serialControlMessage[i].lastIndexOf(":")+1,serialControlMessage[i].length());
                  }

              if(serialControlValues[5].toInt() < 2){serialControlValues[5] = "2";} //Safety Check to prevent timelapse step division by 0
              serialControlValues[0].toLowerCase(); //set mode to lower case for keyword check

              //Check for Mode Keyword
              if(serialControlValues[0] == "timelapse")
              {
                Serial.println("Timelapse started over Serial Communication");
                doTimelapse(serialControlValues[1].toInt(), serialControlValues[4].toInt(), serialControlValues[5].toInt(), serialControlValues[2].toInt());
              } 
              else if (serialControlValues[0] == "normal")
              {
                Serial.println("Normal Run started over Serial Communication");
                doNormalRun(serialControlValues[1].toInt(),serialControlValues[3].toInt(),serialControlValues[2].toInt());
              }               
              else if (serialControlValues[0] == "rth")
              {
                rth();
                Serial.println("Return to Home started over Serial Communication");
              }  
                  else
              {
                Serial.println("Invalid Command");
              }
         }        // ← schließt: else // Full message received
          }       // ← schließt: while (Serial.available() > 0)
}
// END OF LOOP

/***************************************************************************
 * Return to Home
 ****************************************************************************/
 void rth(){
      stepper.setMaxSpeed(speed_max);
      stepper.setRampLen(0); 
      updateStr("Return to Home");
      stepper.moveTo(0);
}

/***************************************************************************
 * normal run function
 ****************************************************************************/
void doNormalRun(int speed_set, int ramp_set, long distance_set){
      stepper.setMaxSpeed(speed_set); 
      stepper.setRampLen(ramp_set);   

      updateStr("Normal Run");   
      tft.fillRect(0, tft.height()-35, tft.width(), 5, RED); // Create Red Progress Bar Basis

      currentPos = stepper.currentPosition();
      stepper.move(distance_set*motorDirection);

      while(stepper.stepsToDo() > 0){
        tft.fillRect(0, tft.height()-35, tft.width()-(tft.width()/100*stepper.moving()), 5, GREEN); // Progress Bar   
      } 
          if(stepper.moving() == 0)
          { updateStr("Target Reached");
            tft.fillRect(0, tft.height()-35, tft.width(), 5, BLACK); // "Remove" Progress Bar
             
          if(return_to_home == true){
           delay(2000); // wait 2sec bevor returning
            updateStr("Returning Home");
            stepper.moveTo(currentPos);
                while(stepper.stepsToDo() > 0){ // Progress Bar for Home Run
                tft.fillRect(tft.width(), tft.height()-35, -(tft.width()-(tft.width()/100*stepper.moving())), 5, BLUE); 
                }
              if(stepper.currentPosition() == currentPos){
            tft.fillRect(0, tft.height()-35, tft.width(), 5, BLACK); // "Remove" Progress Bar
            updateStr("Run Completed");
              }       
          }}
}

/***************************************************************************
 * Camera Trigger Function
 ****************************************************************************/
void triggerCamera(){
  if(camera_attached == true){
    photo_counter++; // Increment photo counter
    digitalWrite(TRIGGER_PIN, LOW); // Close circuit (trigger camera)
    delay(camera_trigger_duration); // Hold trigger for specified duration
    digitalWrite(TRIGGER_PIN, HIGH); // Open circuit (release trigger)
    
    // Serial feedback for triggered photo
    Serial.print("Photo #");
    Serial.print(photo_counter);
    Serial.println(" triggered.");
  }
}

/***************************************************************************
 * timelapse function
 ****************************************************************************/
void doTimelapse(int speed_set, long time_set, int steps_set, long distance_set){
  updateStr("Timelapse Running");

      //Setup
      stepper.setMaxSpeed(speed_set);
      stepper.setRampLen(0); // We don't want a Ramp while doing timelapses, so we disable it here
      steps_count = 1; // Reset stepcount on every new timelapse
      photo_counter = 0; // Reset photo counter for new timelapse

        Serial.print("\r\nStarting Timelapse to Distance ");    
        Serial.println(distance_set);  
        
        // If camera is attached, inform about photo mode
        if(camera_attached == true){
          Serial.println("Camera Module detected - Photos will be triggered at each position.");
        }
            
        if(time_set != 0){   
         ms_time = time_set*1000L;  
                }else {ms_time = 0;}

        Serial.print("Delay time set in ms: "); 
        Serial.print(ms_time);
        Serial.print("\r\n");

        long timelapse_substep = distance_set/steps_set;
        char timelapse_stepsinfo[] ="Substeps length is: ";

        sprintf(timelapse_stepsinfo,"%s%ld%s%i%s",timelapse_stepsinfo,timelapse_substep," (",steps_set," Steps)");
        Serial.println(timelapse_stepsinfo); 

        // Trigger first photo at start position if camera is attached
        if(camera_attached == true){
          delay(50); // Small delay to avoid vibrations before first photo
          triggerCamera();
        }

        while (steps_count <= steps_set) { // while steps are still to do...
          if(stepperRunning){
            if ( !stepper.moving() ) {
                if( steps_count != 1) 
                {
                  Serial.print(stepper.currentPosition());Serial.print("/");Serial.print(distance_set); Serial.print("\r\n");
                  
                  // Trigger camera after motor stops and before delay (if camera attached)
                  if(camera_attached == true){
                    delay(50); // Small delay to avoid vibrations from motor stop
                    triggerCamera();
                  }
                  
                  Serial.print("Waiting...\r\n");
                  // Calculate reduced delay time if camera trigger was used
                  long effective_delay = ms_time;
                  if(camera_attached == true && ms_time > camera_trigger_duration + 100){
                    effective_delay = ms_time - camera_trigger_duration - 100; // Subtract trigger time and safety margins
                  }
                  stepperPause.setTime(effective_delay);
                  } else {stepperPause.setTime(ms_time);} // To prevent the motor from waiting the full Delay before even starting we start with a delay of 1ms. We have to wait at least that time because otherwise it would brick the stepperPause.expired() function later on.               
                  stepperRunning = false;
                }
            } else {
            if ( stepperPause.expired() ) {
          Serial.print(steps_count);Serial.print("/");Serial.print(steps_set); Serial.print("\r\n");
           stepper.move(timelapse_substep*motorDirection);
          stepperRunning = true;
          steps_count++;
          }
           }
        }
        Serial.print(distance_set);Serial.print("/");Serial.print(distance_set); Serial.print("\r\n");

        // Wait for the last move to fully complete before triggering the final photo
        while(stepper.stepsToDo() > 0) {}

        // Final photo at end position if camera is attached
        if(camera_attached == true){
          delay(50); // Small delay to avoid vibrations before final photo
          triggerCamera();
          Serial.print("Timelapse Complete - Total Photos: ");
          Serial.println(photo_counter);
        } else {
          updateStr("Timelapse Complete."); 
        }
            
            delay(5000); //wait at end before RTH
            rth();
            drawButtons(); // I don't know why, but after a timelapse the screen went blank every time...so we redraw the UI after finishing the timelapse here.
}

/***************************************************************************
 * update string so we see what has been touched - debug help
 ****************************************************************************/
void updateStr(String msg){ 
    tft.fillRect(0, tft.height()-30, tft.width(), 30, LIGHTGREY);
    tft.setCursor(20,tft.height()-22);
    tft.setTextSize(2);
    tft.setTextColor(BLACK); 
    tft.print(msg);    
    Serial.println(msg); //Output also in Serial Monitor
}

/***************************************************************************
 * redraw Buttons after Input
 ****************************************************************************/
void redrawButtons(char buttonNr,short xCursor,short yCursor, String buttonLabel){ 
    buttons[buttonNr].drawButton();
    tft.setTextSize(1);
    tft.setTextColor(WHITE); 
    tft.setCursor(xCursor, yCursor);
    tft.print(buttonLabel); 
}

/*****************************************************************************
 * convert X to String
 ****************************************************************************/
void int_to_string(long val, char* string) {
  if(string) 
     sprintf(string, "%ld", val);  
  return;  
}

/*****************************************************************************
 * Optional Sonar Module
 ****************************************************************************/
void echoCheck() { 
  if (sonar.check_timer()) { // This is how you check to see if the ping was received.
    int myPing = sonar.ping_result / US_ROUNDTRIP_CM;
    if(myPing<=7){
      stepper.stop();
      Serial.println("Motor has been stopped by Sonar Module.");
      }
  }
}