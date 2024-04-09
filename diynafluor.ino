#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>

#define LED_PIN 11 // Pin connected to LED

Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591); // Initialize TSL2591 sensor
bool executeLoop = false; // Flag to indicate whether to execute the loop or not
int ledPower = 255;

void setup() {
  Serial.begin(9600); // Initialize serial communication
  pinMode(LED_PIN, OUTPUT); // Set LED pin as output

  Serial.println("Ready!"); // Print message to serial monitor
}

void loop() {
  if (executeLoop) {
    float totalVisible = 0.0;
    const int numReadings = 3; // Number of readings to take
    for (int i = 0; i < numReadings; i++) {
      analogWrite(LED_PIN, ledPower); // Turn on LED
      delay(100); // Wait for LED to stabilize
      tsl.setTiming(TSL2591_INTEGRATIONTIME_600MS); 
      tsl.setGain(TSL2591_GAIN_MAX);
      uint16_t visible = tsl.getLuminosity(TSL2591_VISIBLE); // Read visible light only
      
      totalVisible += visible;
      
      delay(100);
      analogWrite(LED_PIN, 0); // Turn off LED
      
      delay(100); // Wait before taking the next reading
    }
  
    // Calculate the average of the readings
    float averageVisible = totalVisible / numReadings;
    
    // Print average sensor reading
    Serial.println(averageVisible);
    
    executeLoop = false; // Reset flag
  }
  
  if (Serial.available() > 0) { // Check if data is available in serial buffer
    String command = Serial.readStringUntil('\r'); // Read the incoming command
    
    if (command[0] == 'r') { // If the command is 'r' for reading
      ledPower = atoi(command.substring(1).c_str());
      executeLoop = true; // Set flag to true to execute the loop
    }
  }
}