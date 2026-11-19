/*
 * =====================================================================
 * NEUROGRIP SMART PEN - HIGH-PERFORMANCE FIRMWARE
 * Board: Seeed Studio XIAO nRF52840 Sense
 * Peripherals:
 *   - Interlink FSR 402 on Analog Pin A0 (12-bit ADC: 0 - 4095)
 *   - InvenSense MPU-6050 (GY-521) on I2C (SDA=D4, SCL=D5) @ 0x68
 *   - SSD1306 0.96" OLED Display on I2C (SDA=D4, SCL=D5) @ 0x3C
 *   - WS2812B 8-LED NeoPixel Ring on Digital Pin D1
 *   - Onboard Multi-Color RGB LED (Pins 12, 13, 14)
 *   - Tactile Haptic / Piezo Buzzer on D2 (mirrored to D0)
 * BLE Protocol:
 *   - Device Name: "NeuroGrip_Pen"
 *   - Service UUID: 19B10000-E8F2-537E-4F6C-D104768A1214
 *   - Data Char (Notify): 19B10001-E8F2-537E-4F6C-D104768A1214 (P:<fsr>,T:<tremor>)
 *   - Cmd Char (Write):   19B10002-E8F2-537E-4F6C-D104768A1214 (CMD:THRESH:<min>,<max>)
 *
 * Performance Architecture:
 *   - Non-blocking multi-rate scheduler (Sensor: 50Hz, BLE: 25Hz, OLED: 10Hz, RGB: 20Hz)
 *   - Zero blocking delay() calls; non-blocking millis() haptic timing
 *   - Continuous BLE.poll() for zero-latency bidirectional transmission
 *   - Fast 400 kHz I2C clock
 * =====================================================================
 */

#include <ArduinoBLE.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_NeoPixel.h>

// Hardware Pin Definitions
#define PIN_FSR           A0
#define PIN_BUZZER        D2
#define RING_PIN          D1
#define NUM_PIXELS        8

#ifndef LED_RED
#define LED_RED           11
#endif
#ifndef LED_GREEN
#define LED_GREEN         13
#endif
#ifndef LED_BLUE
#define LED_BLUE          12
#endif

// I2C Addresses
#define MPU6050_ADDR      0x68
#define OLED_ADDR         0x3C
#define SCREEN_WIDTH      128
#define SCREEN_HEIGHT     64
#define OLED_RESET        -1

// Peripheral Objects
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
Adafruit_NeoPixel ring(NUM_PIXELS, RING_PIN, NEO_GRB + NEO_KHZ800);

bool oledAvailable = false;
bool mpuAvailable = false;

// BLE Service & Characteristics
#define BLE_SERVICE_UUID    "19B10000-E8F2-537E-4F6C-D104768A1214"
#define BLE_DATA_CHAR_UUID  "19B10001-E8F2-537E-4F6C-D104768A1214"
#define BLE_CMD_CHAR_UUID   "19B10002-E8F2-537E-4F6C-D104768A1214"

BLEService neuroGripService(BLE_SERVICE_UUID);
BLEStringCharacteristic dataChar(BLE_DATA_CHAR_UUID, BLERead | BLENotify, 64);
BLEStringCharacteristic cmdChar(BLE_CMD_CHAR_UUID, BLEWrite, 32);

// Filter & Sensor Variables
int rawFSR = 0;
int filteredFSR = 0;
int16_t ax = 0, ay = 0, az = 0;
int16_t gx = 0, gy = 0, gz = 0;
int prevAx = 0, prevAy = 0, prevAz = 0;
int tremorMagnitude = 0;
const int TREMOR_ALERT_THRESHOLD = 5000;

// Dynamic Personalized Threshold Limits (Configurable via BLE from companion app)
int minPinchGrams = 120;          // Default lower safe pinch limit in grams
int maxPinchGrams = 260;          // Default upper safe pinch limit in grams
int minPinchAdcThreshold = 800;   // Corresponding 12-bit ADC threshold
int maxPinchAdcThreshold = 3400;  // Corresponding 12-bit ADC threshold

inline int gramsToAdc(int g) {
  if (g <= 20) return 200;
  long adc = 200 + ((long)(g - 20) * (4000 - 200)) / (600 - 20);
  return (int)constrain(adc, 200, 4000);
}

inline int adcToGrams(int adc) {
  if (adc <= 200) return 0;
  long g = 20 + ((long)(adc - 200) * (600 - 20)) / (4000 - 200);
  return (int)constrain(g, 0, 850);
}

// Non-blocking Timing Variables
unsigned long now = 0;
unsigned long lastSensorSampleTime = 0;
const unsigned long SENSOR_INTERVAL_MS = 10; // 100 Hz high-speed sensor sampling

unsigned long lastBleSendTime = 0;
const unsigned long BLE_SEND_INTERVAL_MS = 12; // ~83 Hz ultra-fast millisecond BLE streaming

unsigned long lastOledUpdateTime = 0;
const unsigned long OLED_INTERVAL_MS = 100; // 10 Hz smooth visual refresh

unsigned long lastRgbUpdateTime = 0;
const unsigned long RGB_INTERVAL_MS = 50; // 20 Hz lighting animation

// Non-blocking Buzzer / Haptics State Machine
unsigned long buzzerOffTime = 0;
unsigned long lastHapticAlertTime = 0;
const unsigned long HAPTIC_COOLDOWN_MS = 750;

// Pulse / Breathing Animation Phase
uint8_t animPhase = 0;

void triggerBuzzerNonBlocking(int durationMs) {
  digitalWrite(PIN_BUZZER, HIGH);
  buzzerOffTime = millis() + durationMs;
}

void updateBuzzerState() {
  if (buzzerOffTime > 0 && millis() >= buzzerOffTime) {
    digitalWrite(PIN_BUZZER, LOW);
    buzzerOffTime = 0;
  }
}

// Onboard RGB LED helper (active low on XIAO nRF52840)
void setOnboardRGB(bool r, bool g, bool b) {
  digitalWrite(LED_RED, r ? LOW : HIGH);
  digitalWrite(LED_GREEN, g ? LOW : HIGH);
  digitalWrite(LED_BLUE, b ? LOW : HIGH);
}

void setupMPU6050() {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0x00); // Wake up MPU-6050
  byte err = Wire.endTransmission(true);
  mpuAvailable = (err == 0);
  if (mpuAvailable) {
    Serial.println("[OK] MPU-6050 IMU initialized.");
  } else {
    Serial.println("[WARN] MPU-6050 not responding; continuing without IMU.");
  }
}

void readMPU6050() {
  if (!mpuAvailable) {
    tremorMagnitude = 0;
    return;
  }

  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B); // Accelerometer register start
  if (Wire.endTransmission(false) != 0) return;

  if (Wire.requestFrom((uint8_t)MPU6050_ADDR, (size_t)6, true) == 6) {
    ax = (Wire.read() << 8) | Wire.read();
    ay = (Wire.read() << 8) | Wire.read();
    az = (Wire.read() << 8) | Wire.read();

    // High-pass differential vector magnitude for involuntary tremor
    int dX = abs(ax - prevAx);
    int dY = abs(ay - prevAy);
    int dZ = abs(az - prevAz);
    int instantTremor = (int)(sqrt((long)dX * dX + (long)dY * dY + (long)dZ * dZ));

    // Smooth tremor with EWMA filter
    tremorMagnitude = (tremorMagnitude * 3 + instantTremor) / 4;

    prevAx = ax;
    prevAy = ay;
    prevAz = az;
  }
}

void updateOLED(bool bleConnected) {
  if (!oledAvailable) return;

  display.clearDisplay();

  // 1. Header Line: Device Title & Connection Indicator
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 2);
  display.print("NEUROGRIP PEN");

  display.setCursor(82, 2);
  if (bleConnected) {
    display.print("[BLE OK]");
  } else {
    display.print("[SEARCH]");
  }

  // 2. Real-Time Force Readout
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(2, 16);
  display.print("GRIP: ");

  // Simple approx grams for on-screen read (assuming calibrated curve)
  int displayGrams = 0;
  if (filteredFSR > 200) {
    displayGrams = (int)map(filteredFSR, 200, 4000, 20, 600);
  }
  display.setTextSize(2);
  display.setCursor(38, 14);
  display.print(displayGrams);
  display.setTextSize(1);
  display.print(" g");

  display.setCursor(96, 16);
  display.print("(");
  display.print(filteredFSR);
  display.print(")");

  // 3. Dynamic Progress / Envelope Bar
  display.drawRect(2, 32, 124, 9, SSD1306_WHITE);

  // Fill current force
  int fillWidth = map(constrain(filteredFSR, 0, 4095), 0, 4095, 0, 120);
  if (fillWidth > 0) {
    display.fillRect(4, 34, fillWidth, 5, SSD1306_WHITE);
  }

  // Draw personalized safe window tick marks
  int minTick = map(constrain(minPinchAdcThreshold, 0, 4095), 0, 4095, 2, 124);
  int maxTick = map(constrain(maxPinchAdcThreshold, 0, 4095), 0, 4095, 2, 124);
  display.drawLine(minTick, 30, minTick, 42, SSD1306_WHITE);
  display.drawLine(maxTick, 30, maxTick, 42, SSD1306_WHITE);

  // 4. Personalized Limits Display in Grams
  display.setCursor(2, 44);
  display.print("ENVELOPE: ");
  display.print(minPinchGrams);
  display.print("-");
  display.print(maxPinchGrams);
  display.print("g");

  // 5. Biofeedback Status Line
  display.setCursor(2, 55);
  if (filteredFSR > maxPinchAdcThreshold) {
    display.print("STATUS: ! OVERGRIP !");
  } else if (filteredFSR >= minPinchAdcThreshold) {
    display.print("STATUS: OPTIMAL ZONE");
  } else if (filteredFSR > 200) {
    display.print("STATUS: LIGHT TOUCH");
  } else {
    display.print("STATUS: RESTING (0g)");
  }

  display.display();
}

void updateRGB(bool bleConnected) {
  animPhase = (animPhase + 8) & 255;

  if (!bleConnected) {
    // BLE Advertising / Searching: Gentle pulsing Cyan/Blue breathing
    uint8_t brightness = (animPhase > 128) ? (255 - animPhase) * 2 : animPhase * 2;
    uint8_t scaledB = map(brightness, 0, 255, 15, 120);
    for (int i = 0; i < NUM_PIXELS; i++) {
      ring.setPixelColor(i, ring.Color(0, scaledB / 2, scaledB));
    }
    ring.show();
    setOnboardRGB(false, false, true); // Blue on
    return;
  }

  // BLE Connected Biofeedback States:
  if (filteredFSR > maxPinchAdcThreshold) {
    // Excessive Pinch Force (> maxThreshold): Rapid pulsing Crimson Red Alert!
    uint8_t rVal = (animPhase % 64 < 32) ? 255 : 40;
    for (int i = 0; i < NUM_PIXELS; i++) {
      ring.setPixelColor(i, ring.Color(rVal, 0, 0));
    }
    ring.show();
    setOnboardRGB(true, false, false); // Bright Red
  } else if (filteredFSR >= minPinchAdcThreshold) {
    // Safe / Optimal Grip Zone: Soothing Solid Emerald Green
    for (int i = 0; i < NUM_PIXELS; i++) {
      ring.setPixelColor(i, ring.Color(0, 220, 60));
    }
    ring.show();
    setOnboardRGB(false, true, false); // Green
  } else if (filteredFSR > (minPinchAdcThreshold / 2)) {
    // Light contact / approaching safe zone: Soft Cyan / Amber
    for (int i = 0; i < NUM_PIXELS; i++) {
      ring.setPixelColor(i, ring.Color(10, 80, 120));
    }
    ring.show();
    setOnboardRGB(false, true, true); // Cyan
  } else {
    // Resting (Pen idle or lifted): Soft dim teal
    for (int i = 0; i < NUM_PIXELS; i++) {
      ring.setPixelColor(i, ring.Color(0, 15, 20));
    }
    ring.show();
    setOnboardRGB(false, false, false); // Off
  }
}

void handleIncomingBleCommands() {
  if (cmdChar.written()) {
    String cmd = cmdChar.value();
    Serial.print("[BLE CMD RX] ");
    Serial.println(cmd);

    if (cmd.startsWith("BUZZ:")) {
      int dur = cmd.substring(5).toInt();
      triggerBuzzerNonBlocking(dur > 0 ? dur : 100);
    } else if (cmd.startsWith("CMD:THRESH:") || cmd.startsWith("SET:LIMIT:") || cmd.startsWith("CMD:GRAMS:")) {
      int colonIdx = cmd.lastIndexOf(':');
      String valStr = cmd.substring(colonIdx + 1);
      int commaIdx = valStr.indexOf(',');
      int newMin = 0, newMax = 0;
      if (commaIdx > 0) {
        newMin = valStr.substring(0, commaIdx).toInt();
        newMax = valStr.substring(commaIdx + 1).toInt();
      } else {
        newMax = valStr.toInt();
      }

      // If incoming values are in grams (<= 850g)
      if (newMax > 0 && newMax <= 850) {
        if (newMin > 0 && newMin < newMax) {
          minPinchGrams = newMin;
        }
        maxPinchGrams = newMax;
        minPinchAdcThreshold = gramsToAdc(minPinchGrams);
        maxPinchAdcThreshold = gramsToAdc(maxPinchGrams);
      } else if (newMax > 850) {
        // Incoming values are in raw ADC counts
        if (newMin > 0) minPinchAdcThreshold = newMin;
        maxPinchAdcThreshold = newMax;
        minPinchGrams = adcToGrams(minPinchAdcThreshold);
        maxPinchGrams = adcToGrams(maxPinchAdcThreshold);
      }

      // Haptic confirmation chirp
      triggerBuzzerNonBlocking(60);
      char logBuf[96];
      snprintf(logBuf, sizeof(logBuf), "[OK] Personalized Limits Synced: %d-%dg (ADC: %d-%d)\r\n",
               minPinchGrams, maxPinchGrams, minPinchAdcThreshold, maxPinchAdcThreshold);
      Serial.print(logBuf);
    }
  }
}

void setup() {
  Serial.begin(115200);

  // Buzzer output
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  // Onboard RGB outputs
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  setOnboardRGB(false, false, false);

  // Initialize Fast 400kHz I2C Bus
  Wire.begin();
  Wire.setClock(400000);

  // Initialize WS2812B RGB Ring
  ring.begin();
  ring.setBrightness(75);
  for (int i = 0; i < NUM_PIXELS; i++) {
    ring.setPixelColor(i, ring.Color(0, 150, 255)); // Initial Cyan test
  }
  ring.show();

  // Initialize SSD1306 OLED Display
  if (display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    oledAvailable = true;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(16, 12);
    display.println("NEUROGRIP PEN");
    display.setCursor(20, 28);
    display.println("SYSTEM READY");
    display.setCursor(14, 44);
    display.println("FAST 25Hz BLE");
    display.display();
    Serial.println("[OK] SSD1306 OLED initialized @ 0x3C");
  }

  // Initialize MPU-6050 IMU
  setupMPU6050();

  // Initialize BLE Stack
  if (!BLE.begin()) {
    Serial.println("[ERR] Failed to start BLE radio!");
    while (1);
  }

  BLE.setLocalName("NeuroGrip_Pen");
  BLE.setAdvertisedService(neuroGripService);
  neuroGripService.addCharacteristic(dataChar);
  neuroGripService.addCharacteristic(cmdChar);
  BLE.addService(neuroGripService);

  // Initialize baseline personalized threshold limits
  minPinchAdcThreshold = gramsToAdc(minPinchGrams);
  maxPinchAdcThreshold = gramsToAdc(maxPinchGrams);

  // Fast connection interval negotiation (7.5ms to 12.5ms ultra-low latency)
  BLE.setConnectionInterval(6, 10);

  BLE.advertise();
  char advBuf[96];
  snprintf(advBuf, sizeof(advBuf), "[OK] NeuroGrip Pen Active & Fast Advertising. Envelope: %d-%dg (ADC: %d-%d)\r\n",
           minPinchGrams, maxPinchGrams, minPinchAdcThreshold, maxPinchAdcThreshold);
  Serial.print(advBuf);

  // Startup confirmation chirp
  triggerBuzzerNonBlocking(70);
}

void loop() {
  now = millis();

  // Service BLE stack continuously on EVERY iteration
  BLE.poll();

  // Update non-blocking buzzer/haptic timer
  updateBuzzerState();

  BLEDevice central = BLE.central();
  bool isConnected = central && central.connected();

  // 1. HIGH-SPEED SENSOR ACQUISITION (50 Hz / 20 ms)
  if (now - lastSensorSampleTime >= SENSOR_INTERVAL_MS) {
    lastSensorSampleTime = now;

    // Read FSR and smooth with EWMA filter (alpha = 0.25)
    rawFSR = analogRead(PIN_FSR);
    filteredFSR = (filteredFSR * 3 + rawFSR) / 4;

    // Read MPU-6050 IMU
    readMPU6050();

    // Local Real-Time Haptic Biofeedback on Overgrip (> maxPinchAdcThreshold)
    if (filteredFSR > maxPinchAdcThreshold) {
      if (now - lastHapticAlertTime >= HAPTIC_COOLDOWN_MS) {
        lastHapticAlertTime = now;
        triggerBuzzerNonBlocking(55); // Crisp 55ms haptic pulse
      }
    }
  }

  // 2. ULTRA-FAST BLE TRANSMISSION (25 Hz / 40 ms)
  // Perfectly matches BLE connection intervals to eliminate packet backlog & delay
  if (isConnected) {
    handleIncomingBleCommands();

    if (now - lastBleSendTime >= BLE_SEND_INTERVAL_MS) {
      lastBleSendTime = now;

      char buffer[36];
      int gVal = adcToGrams(filteredFSR);
      snprintf(buffer, sizeof(buffer), "P:%d,G:%d,T:%d", filteredFSR, gVal, tremorMagnitude);
      dataChar.writeValue(buffer);
    }
  }

  // 3. NON-BLOCKING RGB RING BIOFEEDBACK (20 Hz / 50 ms)
  if (now - lastRgbUpdateTime >= RGB_INTERVAL_MS) {
    lastRgbUpdateTime = now;
    updateRGB(isConnected);
  }

  // 4. NON-BLOCKING OLED DISPLAY REFRESH (10 Hz / 100 ms)
  if (now - lastOledUpdateTime >= OLED_INTERVAL_MS) {
    lastOledUpdateTime = now;
    updateOLED(isConnected);
  }
}
