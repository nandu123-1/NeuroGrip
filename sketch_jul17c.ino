#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ==========================================
// PIN CONFIGURATIONS
// ==========================================
// FSR 402 
const int fsrPin = 34;      
const int virtualVccFSR = 5;   
const int virtualGndFSR = 2;   

// MPU6050 
const int MPU_ADDR = 0x68;  

// Vibration Motor 
const int motorPin = 25;    

// LED 
const int ledPin = 13;      
const int virtualGndLED = 12;  

// 3-Pin Active Buzzer 
const int buzzerPin = 26;      
const int virtualGndBuzzer = 14; 

// ==========================================
// THRESHOLDS & BLE VARIABLES
// ==========================================
const int TOO_TIGHT_GRIP = 3000;     
const int UNSTABLE_ROTATION = 40000; 

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;

unsigned long previousMillis = 0;
const long interval = 100; // Send data to app 10 times a second

// These UUIDs match your React Native app exactly
#define SERVICE_UUID        "19B10000-E8F2-537E-4F6C-D104768A1214"
#define CHARACTERISTIC_UUID "19B10001-E8F2-537E-4F6C-D104768A1214"

// Callback class to handle connection status
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Mobile App Connected!");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Mobile App Disconnected!");
    }
};

void setup() {
  Serial.begin(115200);
  delay(1000); // Safe boot delay

  // --- SPAWN VIRTUAL POWER & GROUNDS ---
  pinMode(virtualVccFSR, OUTPUT);
  digitalWrite(virtualVccFSR, HIGH); 
  pinMode(virtualGndFSR, OUTPUT);
  digitalWrite(virtualGndFSR, LOW);  
  
  pinMode(virtualGndLED, OUTPUT);
  digitalWrite(virtualGndLED, LOW);     
  
  pinMode(virtualGndBuzzer, OUTPUT);
  digitalWrite(virtualGndBuzzer, LOW);

  // --- INITIALIZE OUTPUT PINS ---
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);      
  pinMode(motorPin, OUTPUT);
  digitalWrite(motorPin, LOW); 
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);

  delay(250); // Give MPU6050 physical power time to stabilize

  // --- INITIALIZE MPU6050 ---
  Wire.begin(21, 22); 
  Wire.setClock(50000); 
  
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);  
  Wire.write(0);     
  byte error = Wire.endTransmission(true);
  
  if(error == 0){
    Serial.println("Smart Pen Online: All Hardware Active.");
  } else {
    Serial.println("CRITICAL ERROR: MPU6050 missing. Check the D21/D22 wires!");
  }
  
  // --- SYSTEM BOOT TEST ---
  Serial.println("Running Hardware Test...");
  digitalWrite(ledPin, HIGH);
  digitalWrite(buzzerPin, HIGH);
  digitalWrite(motorPin, HIGH);
  delay(500); 
  digitalWrite(ledPin, LOW);
  digitalWrite(buzzerPin, LOW);
  digitalWrite(motorPin, LOW);

  // --- INITIALIZE BLUETOOTH ---
  BLEDevice::init("SmartPen_BLE");
  
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY 
                    );

  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  
  Serial.println("ESP32 BLE active. Waiting for the React Native app to scan...");
}

void loop() {
  // ==========================================
  // 1. READ SENSORS
  // ==========================================
  int gripPressure = analogRead(fsrPin);
  
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);  
  Wire.endTransmission(false);
  
  // FIXED BUG: Request 14 bytes instead of 30!
  Wire.requestFrom(MPU_ADDR, 14, true); 
  
  int16_t AcX = Wire.read() << 8 | Wire.read();     
  int16_t AcY = Wire.read() << 8 | Wire.read(); 
  int16_t AcZ = Wire.read() << 8 | Wire.read(); 
  
  Wire.read(); Wire.read(); // Skip Temp
  
  int16_t GyX = Wire.read() << 8 | Wire.read();     
  int16_t GyY = Wire.read() << 8 | Wire.read(); 
  int16_t GyZ = Wire.read() << 8 | Wire.read(); 

  long totalRotationSpeed = abs(GyX) + abs(GyY) + abs(GyZ);

  // ==========================================
  // 2. HARDWARE BIOFEEDBACK ALERTS
  // ==========================================
  if (gripPressure > TOO_TIGHT_GRIP) {
    digitalWrite(buzzerPin, HIGH);  
  } else {
    digitalWrite(buzzerPin, LOW);   
  }

  if (totalRotationSpeed > UNSTABLE_ROTATION) {
    digitalWrite(ledPin, HIGH);    
    digitalWrite(motorPin, HIGH);  
    delay(500);                    
    digitalWrite(motorPin, LOW);   
    delay(400); 
  } else {
    digitalWrite(ledPin, LOW);
    digitalWrite(motorPin, LOW);
  }

  // ==========================================
  // 3. BLUETOOTH TELEMETRY STREAM
  // ==========================================
  if (deviceConnected) {
      unsigned long currentMillis = millis();
      
      // Send data to the app 10 times a second without freezing the loop
      if (currentMillis - previousMillis >= interval) {
          previousMillis = currentMillis;

          // Format the exact string the React Native app charts need
          String payload = "P:" + String(gripPressure) + ",T:" + String(totalRotationSpeed);
          
          pCharacteristic->setValue(payload.c_str());
          pCharacteristic->notify(); 
      }
  }
  
  // Safety check: Restart BLE advertisement if phone disconnects
  if (!deviceConnected && oldDeviceConnected) {
      delay(500); // Give the Bluetooth stack time to clean up
      pServer->startAdvertising(); 
      Serial.println("Restarting BLE broadcast...");
      oldDeviceConnected = deviceConnected;
  }
  
  // Update state when newly connected
  if (deviceConnected && !oldDeviceConnected) {
      oldDeviceConnected = deviceConnected;
  }
  
  delay(50); // Loop speed to keep I2C sensor reads stable 
}