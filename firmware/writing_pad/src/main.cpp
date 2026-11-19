/*
 * =====================================================================
 * NEUROGRIP WRITING PAD - DIRECT MOBILE BLE PERIPHERAL FIRMWARE
 * Board: ESP32 DevKit V1
 * Display: Waveshare 3.5inch RPi LCD (F) - CAPACITIVE TOUCH
 * Drivers:
 *   - Display: ST7796S (4-Wire SPI @ 40MHz, IPS 480x320)
 *   - Touch:   Goodix GT911 (I2C Capacitive Multi-touch)
 * Connector: Uses standard 40-pin header OR 13-Pin GH1.25 connector
 *
 * Dedicated Peripheral Architecture:
 *   1. Captures capacitive touch (X, Y) from GT911 at ~200 Hz
 *   2. Displays ultra-fast digital inking and clinical handwriting guides
 *   3. Connects DIRECTLY to Android Companion App via BLE (Peripheral role)
 *   4. Streams touch coordinates (X, Y) & receives mode/clear commands
 *   5. Receives Smart Pen telemetry forwarded from Mobile App for UI sync
 * =====================================================================
 */

#include <SPI.h>
#include <Wire.h>
#include <TFT_eSPI.h>              // Fast ST7796S display driver
#include <TAMC_GT911.h>            // Goodix GT911 capacitive touch driver
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// -------------------------------------------------------------
// Waveshare 3.5" (F) GH1.25 / GPIO Pin Configuration
// -------------------------------------------------------------
#define TOUCH_SDA   21    // GH1.25 Pin 4
#define TOUCH_SCL   22    // GH1.25 Pin 3
#define TOUCH_INT   27    // GH1.25 Pin 2 (Interrupt)
#define TOUCH_RST   14    // GH1.25 Pin 1 (Reset)

#define SCREEN_WIDTH  480
#define SCREEN_HEIGHT 320

TFT_eSPI tft = TFT_eSPI();
TAMC_GT911 touch = TAMC_GT911(TOUCH_SDA, TOUCH_SCL, TOUCH_INT, TOUCH_RST, SCREEN_WIDTH, SCREEN_HEIGHT);

// -------------------------------------------------------------
// BLE Service & Characteristic UUIDs
// -------------------------------------------------------------
#define SERVICE_UUID        "19B10000-E8F2-537E-4F6C-D104768A1214"
#define DATA_CHAR_UUID      "19B10001-E8F2-537E-4F6C-D104768A1214"
#define CMD_CHAR_UUID       "19B10002-E8F2-537E-4F6C-D104768A1214"

BLEServer* pServer = NULL;
BLECharacteristic* pDataCharacteristic = NULL;
BLECharacteristic* pCmdCharacteristic = NULL;
volatile bool phoneConnected = false;
volatile bool penConnected = false;
volatile bool updateUIFlag = false;

// -------------------------------------------------------------
// Shared Telemetry & Display Mode State
// -------------------------------------------------------------
volatile int penPressure = 0;
volatile int penTremor = 0;

int prevX = -1, prevY = -1;

enum DisplayMode {
  MODE_FREE = 0,
  MODE_ALPHA_UPPER = 1,
  MODE_ALPHA_LOWER = 2,
  MODE_ALPHA_NEURO = 3
};

DisplayMode currentMode = MODE_ALPHA_UPPER;
volatile bool pendingClear = false;
volatile DisplayMode pendingMode = MODE_ALPHA_UPPER;
volatile bool isDarkTheme = true;

inline uint16_t getBgColor() { return isDarkTheme ? TFT_BLACK : TFT_WHITE; }
inline uint16_t getHeaderBgColor() { return isDarkTheme ? 0x10A2 : 0xF7BE; }
inline uint16_t getHeaderTextColor() { return isDarkTheme ? TFT_WHITE : 0x10A2; }
inline uint16_t getBorderColor() { return isDarkTheme ? 0x2945 : 0xCE79; }
inline uint16_t getInkColor() { return isDarkTheme ? TFT_CYAN : 0x0017; }

void drawUI();
void clearCanvas();
void drawAlphabetGuide(DisplayMode mode);

// Helper to draw dashed lines for clinical handwriting guides
void drawDashedLine(int x0, int y0, int x1, int y1, uint16_t color, int dash = 5, int gap = 3) {
  float dx = x1 - x0;
  float dy = y1 - y0;
  float dist = sqrt(dx * dx + dy * dy);
  if (dist < 1.0f) return;
  float ux = dx / dist;
  float uy = dy / dist;

  float traveled = 0.0f;
  while (traveled < dist) {
    float seg = min((float)dash, dist - traveled);
    int sx0 = x0 + (int)(ux * traveled);
    int sy0 = y0 + (int)(uy * traveled);
    int sx1 = x0 + (int)(ux * (traveled + seg));
    int sy1 = y0 + (int)(uy * (traveled + seg));
    tft.drawLine(sx0, sy0, sx1, sy1, color);
    traveled += (dash + gap);
  }
}

// -------------------------------------------------------------
// BLE Server Callbacks (for Mobile Companion App)
// -------------------------------------------------------------
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer, esp_ble_gatts_cb_param_t *param) {
    phoneConnected = true;
    updateUIFlag = true;
    Serial.println("[PAD BLE] Mobile App Connected directly!");
    // Request fastest BLE connection interval (7.5ms to 11.25ms)
    pServer->updateConnParams(param->connect.remote_bda, 6, 9, 0, 400);
  }
  void onDisconnect(BLEServer* pServer) {
    phoneConnected = false;
    penConnected = false;
    updateUIFlag = true;
    Serial.println("[PAD BLE] Mobile App Disconnected. Restarting advertising...");
    pServer->startAdvertising();
  }
};

// -------------------------------------------------------------
// BLE Command Receiver (Two-Way App-to-Pad Sync)
// -------------------------------------------------------------
class CmdCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pCharacteristic) {
    std::string rxVal = pCharacteristic->getValue();
    if (rxVal.length() > 0) {
      if (rxVal.find("CMD:CLEAR") != std::string::npos) {
        pendingClear = true;
      } else if (rxVal.find("CMD:MODE:FREE") != std::string::npos) {
        pendingMode = MODE_FREE;
        pendingClear = true;
      } else if (rxVal.find("CMD:MODE:ALPHA:UPPER") != std::string::npos) {
        pendingMode = MODE_ALPHA_UPPER;
        pendingClear = true;
      } else if (rxVal.find("CMD:MODE:ALPHA:LOWER") != std::string::npos) {
        pendingMode = MODE_ALPHA_LOWER;
        pendingClear = true;
      } else if (rxVal.find("CMD:MODE:ALPHA:NEURO") != std::string::npos) {
        pendingMode = MODE_ALPHA_NEURO;
        pendingClear = true;
      } else if (rxVal.find("CMD:THEME:DARK") != std::string::npos) {
        isDarkTheme = true;
        pendingClear = true;
      } else if (rxVal.find("CMD:THEME:LIGHT") != std::string::npos) {
        isDarkTheme = false;
        pendingClear = true;
      } else if (rxVal.find("PEN:") != std::string::npos) {
        int state = 0;
        sscanf(rxVal.c_str(), "PEN:%d", &state);
        bool newPenState = (state == 1);
        if (newPenState != penConnected) {
          penConnected = newPenState;
          updateUIFlag = true;
        }
      }
    }
  }
};

// -------------------------------------------------------------
// Minimalist UI Rendering Functions (Dark & Light Theme)
// -------------------------------------------------------------
void drawUI() {
  uint16_t hBg = getHeaderBgColor();
  uint16_t hText = getHeaderTextColor();
  uint16_t hBorder = getBorderColor();

  tft.fillRect(0, 0, 480, 44, hBg);
  tft.drawFastHLine(0, 44, 480, hBorder);

  // Minimalist Title
  tft.setTextColor(hText, hBg);
  tft.setTextSize(2);
  tft.drawString("NEUROGRIP", 10, 14);

  // Mobile & Pen status indicator
  tft.setTextSize(1);
  uint16_t statColor = (phoneConnected && penConnected) ? (isDarkTheme ? TFT_GREEN : 0x04A0) :
                       phoneConnected ? (isDarkTheme ? TFT_CYAN : 0x0017) :
                       (isDarkTheme ? TFT_YELLOW : 0xB4A0);
  tft.setTextColor(statColor, hBg);
  const char* statusStr = (phoneConnected && penConnected) ? "* PEN+APP SYNCED" :
                          phoneConnected ? "* APP CONNECTED" : "* STANDBY";
  tft.drawString(statusStr, 130, 18);

  // Header Button 1: CLEAR [235 - 305] (w=70, h=28)
  uint16_t clearBtnBg = isDarkTheme ? 0x9000 : 0xF9C7;
  uint16_t clearText = isDarkTheme ? TFT_WHITE : 0x8800;
  tft.fillRoundRect(235, 8, 70, 28, 4, clearBtnBg);
  tft.setTextColor(clearText, clearBtnBg);
  tft.setTextSize(2);
  tft.drawString("CLEAR", 243, 14);

  // Header Button 2: MODE [315 - 385] (w=70, h=28)
  const char* modeLabel = (currentMode == MODE_FREE) ? "FREE" :
                          (currentMode == MODE_ALPHA_UPPER) ? "A-Z" :
                          (currentMode == MODE_ALPHA_LOWER) ? "a-z" : "WORD";
  uint16_t modeBtnBg = (currentMode == MODE_FREE) ? (isDarkTheme ? 0x18E3 : 0xE71C) : (isDarkTheme ? 0x03EF : 0x0277);
  uint16_t modeText = isDarkTheme ? TFT_WHITE : 0xFFFF;
  tft.fillRoundRect(315, 8, 70, 28, 4, modeBtnBg);
  tft.setTextColor(modeText, modeBtnBg);
  tft.drawString(modeLabel, 325, 14);

  // Header Button 3: THEME [395 - 468] (w=73, h=28)
  const char* themeLabel = isDarkTheme ? "DARK" : "LIGHT";
  uint16_t themeBtnBg = isDarkTheme ? 0x2965 : 0xDEFB;
  uint16_t themeText = isDarkTheme ? 0x7BEF : 0x18E3;
  tft.fillRoundRect(395, 8, 73, 28, 4, themeBtnBg);
  tft.setTextColor(themeText, themeBtnBg);
  tft.drawString(themeLabel, 407, 14);
}

void drawAlphabetGuide(DisplayMode mode) {
  if (mode == MODE_FREE) return;

  const int yAsc = 75;
  const int yMid = 140;
  const int yBase = 205;
  const int yDesc = 270;

  uint16_t ascDescColor = isDarkTheme ? 0x4A69 : 0xAD55;
  uint16_t midLineColor = isDarkTheme ? 0x03EF : 0x02DF;
  uint16_t baseLineColor = isDarkTheme ? TFT_CYAN : 0x0017;
  uint16_t guideColor = isDarkTheme ? 0x047F : 0x632C;
  uint16_t dotColor = isDarkTheme ? TFT_YELLOW : 0xD5A0;

  // 1. Draw 4 Clinical Handwriting Guidelines across 480px width
  for (int x = 10; x < 470; x += 8) {
    tft.drawFastHLine(x, yAsc, 4, ascDescColor);   // Dotted Ascender
    tft.drawFastHLine(x, yMid, 4, midLineColor);   // Dotted Midline (Cyan)
    tft.drawFastHLine(x, yDesc, 4, ascDescColor);  // Dotted Descender
  }
  // Solid Baseline
  tft.drawFastHLine(10, yBase, 460, baseLineColor);
  tft.drawFastHLine(10, yBase + 1, 460, baseLineColor);

  // Guideline Labels
  tft.setTextSize(1);
  uint16_t labelColor = isDarkTheme ? 0x7BEF : 0x6B4D;
  tft.setTextColor(labelColor, getBgColor());
  tft.drawString("ASC", 12, yAsc - 10);
  tft.drawString("MID", 12, yMid - 10);
  tft.drawString("BASE", 12, yBase + 3);
  tft.drawString("DESC", 12, yDesc + 3);

  // 2. Render Letter Tracing Guidelines
  if (mode == MODE_ALPHA_UPPER) {
    // Letter 'A'
    drawDashedLine(35, yBase, 65, yAsc, guideColor);
    drawDashedLine(65, yAsc, 95, yBase, guideColor);
    drawDashedLine(50, 150, 80, 150, guideColor);
    tft.fillCircle(65, yAsc, 2, dotColor);

    // Letter 'B'
    drawDashedLine(125, yBase, 125, yAsc, guideColor);
    drawDashedLine(125, yAsc, 165, yAsc, guideColor);
    drawDashedLine(165, yAsc, 175, 107, guideColor);
    drawDashedLine(175, 107, 165, yMid, guideColor);
    drawDashedLine(165, yMid, 125, yMid, guideColor);
    drawDashedLine(125, yMid, 170, yMid, guideColor);
    drawDashedLine(170, yMid, 180, 172, guideColor);
    drawDashedLine(180, 172, 170, yBase, guideColor);
    drawDashedLine(170, yBase, 125, yBase, guideColor);
    tft.fillCircle(125, yAsc, 2, dotColor);

    // Letter 'C'
    drawDashedLine(265, 100, 235, yAsc, guideColor);
    drawDashedLine(235, yAsc, 210, 105, guideColor);
    drawDashedLine(210, 105, 210, 175, guideColor);
    drawDashedLine(210, 175, 235, yBase, guideColor);
    drawDashedLine(235, yBase, 265, 180, guideColor);
    tft.fillCircle(265, 100, 2, dotColor);

    // Letter 'D'
    drawDashedLine(295, yBase, 295, yAsc, guideColor);
    drawDashedLine(295, yAsc, 340, yAsc, guideColor);
    drawDashedLine(340, yAsc, 355, 140, guideColor);
    drawDashedLine(355, 140, 340, yBase, guideColor);
    drawDashedLine(340, yBase, 295, yBase, guideColor);
    tft.fillCircle(295, yAsc, 2, dotColor);

    // Letter 'E'
    drawDashedLine(385, yBase, 385, yAsc, guideColor);
    drawDashedLine(385, yAsc, 430, yAsc, guideColor);
    drawDashedLine(385, yMid, 420, yMid, guideColor);
    drawDashedLine(385, yBase, 430, yBase, guideColor);
    tft.fillCircle(385, yAsc, 2, dotColor);
  }
  else if (mode == MODE_ALPHA_LOWER) {
    // Letter 'a'
    drawDashedLine(85, 150, 55, yMid, guideColor);
    drawDashedLine(55, yMid, 45, 170, guideColor);
    drawDashedLine(45, 170, 55, yBase, guideColor);
    drawDashedLine(55, yBase, 85, yBase, guideColor);
    drawDashedLine(85, yMid, 85, yBase, guideColor);
    tft.fillCircle(85, 150, 2, dotColor);

    // Letter 'b'
    drawDashedLine(130, yBase, 130, yAsc, guideColor);
    drawDashedLine(130, yMid, 170, yMid, guideColor);
    drawDashedLine(170, yMid, 175, 172, guideColor);
    drawDashedLine(175, 172, 170, yBase, guideColor);
    drawDashedLine(170, yBase, 130, yBase, guideColor);
    tft.fillCircle(130, yAsc, 2, dotColor);

    // Letter 'c'
    drawDashedLine(260, 155, 240, yMid, guideColor);
    drawDashedLine(240, yMid, 220, 172, guideColor);
    drawDashedLine(220, 172, 240, yBase, guideColor);
    drawDashedLine(240, yBase, 260, 185, guideColor);
    tft.fillCircle(260, 155, 2, dotColor);

    // Letter 'd'
    drawDashedLine(350, yBase, 350, yAsc, guideColor);
    drawDashedLine(350, yBase, 310, yBase, guideColor);
    drawDashedLine(310, yBase, 305, 172, guideColor);
    drawDashedLine(305, 172, 310, yMid, guideColor);
    drawDashedLine(310, yMid, 350, yMid, guideColor);
    tft.fillCircle(350, yAsc, 2, dotColor);

    // Letter 'e'
    drawDashedLine(395, 170, 440, 170, guideColor);
    drawDashedLine(440, 170, 440, yMid, guideColor);
    drawDashedLine(440, yMid, 395, yMid, guideColor);
    drawDashedLine(395, yMid, 395, yBase, guideColor);
    drawDashedLine(395, yBase, 435, yBase, guideColor);
    tft.fillCircle(395, 170, 2, dotColor);
  }
  else if (mode == MODE_ALPHA_NEURO) {
    // Word: "N E U R O"
    // 'N'
    drawDashedLine(45, yBase, 45, yAsc, guideColor);
    drawDashedLine(45, yAsc, 95, yBase, guideColor);
    drawDashedLine(95, yBase, 95, yAsc, guideColor);

    // 'E'
    drawDashedLine(130, yBase, 130, yAsc, guideColor);
    drawDashedLine(130, yAsc, 175, yAsc, guideColor);
    drawDashedLine(130, yMid, 165, yMid, guideColor);
    drawDashedLine(130, yBase, 175, yBase, guideColor);

    // 'U'
    drawDashedLine(210, yAsc, 210, 185, guideColor);
    drawDashedLine(210, 185, 235, yBase, guideColor);
    drawDashedLine(235, yBase, 260, 185, guideColor);
    drawDashedLine(260, 185, 260, yAsc, guideColor);

    // 'R'
    drawDashedLine(300, yBase, 300, yAsc, guideColor);
    drawDashedLine(300, yAsc, 345, yAsc, guideColor);
    drawDashedLine(345, yAsc, 345, yMid, guideColor);
    drawDashedLine(345, yMid, 300, yMid, guideColor);
    drawDashedLine(320, yMid, 345, yBase, guideColor);

    // 'O'
    drawDashedLine(380, 105, 410, yAsc, guideColor);
    drawDashedLine(410, yAsc, 440, 105, guideColor);
    drawDashedLine(440, 105, 440, 175, guideColor);
    drawDashedLine(440, 175, 410, yBase, guideColor);
    drawDashedLine(410, yBase, 380, 175, guideColor);
    drawDashedLine(380, 175, 380, 105, guideColor);
  }
}

void clearCanvas() {
  tft.fillRect(0, 45, 480, 275, getBgColor());
  drawAlphabetGuide(currentMode);
  prevX = -1;
  prevY = -1;
}

void recoverI2C() {
  Wire.end();
  pinMode(TOUCH_SCL, OUTPUT);
  pinMode(TOUCH_SDA, INPUT_PULLUP);
  for (int i = 0; i < 9; i++) {
    digitalWrite(TOUCH_SCL, LOW);
    delayMicroseconds(5);
    digitalWrite(TOUCH_SCL, HIGH);
    delayMicroseconds(5);
  }
  pinMode(TOUCH_SDA, OUTPUT);
  digitalWrite(TOUCH_SDA, HIGH);
  delay(10);
  touch.begin();
  touch.setRotation(ROTATION_RIGHT);
  Wire.setTimeOut(25);
  Serial.println("[PAD] I2C Bus recovered and GT911 reset.");
}

// -------------------------------------------------------------
// Setup & Initialization
// -------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n[NeuroGrip] =========================================");
  Serial.println("[NeuroGrip] Waveshare 3.5\" (F) Capacitive Touch Pad");
  Serial.println("[NeuroGrip] Display: ST7796S (4-Wire SPI @ 40MHz)");
  Serial.println("[NeuroGrip] Touch:   Goodix GT911 (I2C SDA=21, SCL=22)");
  Serial.println("[NeuroGrip] =========================================");

  // Backlight enable (GPIO 32)
  pinMode(32, OUTPUT);
  digitalWrite(32, HIGH);

  // 1. Initialize ST7796S IPS Display
  tft.init();
  tft.setRotation(1); // Landscape (480x320)
  tft.fillScreen(TFT_BLACK);

  // 2. Clear I2C Bus & Initialize GT911 Capacitive Touch
  recoverI2C();

  drawUI();
  clearCanvas();

  // 3. Initialize BLE Server for Direct Mobile App Connection
  BLEDevice::init("NeuroGrip_Pad");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  BLEService* pService = pServer->createService(SERVICE_UUID);

  // Telemetry Stream Characteristic (Notify to App)
  pDataCharacteristic = pService->createCharacteristic(
    DATA_CHAR_UUID,
    BLECharacteristic::PROPERTY_READ |
    BLECharacteristic::PROPERTY_NOTIFY
  );
  pDataCharacteristic->addDescriptor(new BLE2902());

  // Command Characteristic (Write from App to Pad)
  pCmdCharacteristic = pService->createCharacteristic(
    CMD_CHAR_UUID,
    BLECharacteristic::PROPERTY_WRITE |
    BLECharacteristic::PROPERTY_WRITE_NR
  );
  pCmdCharacteristic->setCallbacks(new CmdCallbacks());

  pService->start();
  BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();

  Serial.println("[OK] Waveshare 3.5\" (F) ST7796S + GT911 Direct BLE Peripheral Ready.");
}

// -------------------------------------------------------------
// Main Loop: Touch Detection + Inking + Telemetry Streaming
// -------------------------------------------------------------
void loop() {
  int touchX = 0, touchY = 0;
  bool isDown = false;
  static int missedFrames = 0;

  // Handle commands received via BLE from Mobile Companion App
  if (pendingClear) {
    pendingClear = false;
    currentMode = pendingMode;
    Serial.printf("[PAD SYNC] Mode switched to %d. Screen cleared & redrawn.\n", currentMode);
    drawUI();
    clearCanvas();
  }

  // Safely update display header on main thread when connection status changes
  if (updateUIFlag) {
    updateUIFlag = false;
    drawUI();
  }

  // Periodic heartbeat diagnostic
  static unsigned long lastHeartbeat = 0;
  unsigned long curMillis = millis();
  if (curMillis - lastHeartbeat > 2000) {
    lastHeartbeat = curMillis;
    Serial.printf("[PAD HB m=%lu] App:%d PenSynced:%d Mode:%d\n",
                  curMillis,
                  phoneConnected ? 1 : 0,
                  penConnected ? 1 : 0,
                  (int)currentMode);
  }

  // Poll GT911 capacitive touch controller at rock-solid 100 Hz (10ms cadence)
  static unsigned long lastTouchPoll = 0;
  static unsigned long lastStreamTime = 0;
  static int lastSentX = -1;
  static int lastSentY = -1;
  static bool wasDownLastFrame = false;
  unsigned long now = millis();

  if (now - lastTouchPoll >= 10) {
    lastTouchPoll = now;
    touch.read();

    if (touch.isTouched && touch.touches > 0) {
      missedFrames = 0;
      touchX = touch.points[0].x;
      touchY = touch.points[0].y;
      touchX = constrain(touchX, 0, 479);
      touchY = constrain(touchY, 0, 319);
      isDown = true;

      // Header buttons detection (touchY < 44)
      if (touchY < 44) {
        // 1. Clear Button [230, 8] to [308, 38]
        if (touchX >= 230 && touchX <= 308) {
          Serial.printf("[PAD] CLEAR Button Pressed\n");
          clearCanvas();
          if (phoneConnected && pDataCharacteristic) {
            pDataCharacteristic->setValue((uint8_t*)"EVT:CLEAR", 9);
            pDataCharacteristic->notify();
          }
          delay(140);
        } 
        // 2. Mode Button [312, 8] to [388, 38]
        else if (touchX >= 312 && touchX <= 388) {
          if (currentMode == MODE_ALPHA_UPPER) currentMode = MODE_ALPHA_LOWER;
          else if (currentMode == MODE_ALPHA_LOWER) currentMode = MODE_ALPHA_NEURO;
          else if (currentMode == MODE_ALPHA_NEURO) currentMode = MODE_FREE;
          else currentMode = MODE_ALPHA_UPPER;

          Serial.printf("[PAD] Mode Switched: %d\n", currentMode);
          drawUI();
          clearCanvas();

          if (phoneConnected && pDataCharacteristic) {
            char evt[24];
            snprintf(evt, sizeof(evt), "EVT:MODE:%d", currentMode);
            pDataCharacteristic->setValue((uint8_t*)evt, strlen(evt));
            pDataCharacteristic->notify();
          }
          delay(140);
        }
        // 3. Theme Button [392, 8] to [475, 38]
        else if (touchX >= 392 && touchX <= 475) {
          isDarkTheme = !isDarkTheme;
          Serial.printf("[PAD] Theme Toggled: %s\n", isDarkTheme ? "DARK" : "LIGHT");
          drawUI();
          clearCanvas();

          if (phoneConnected && pDataCharacteristic) {
            const char* evt = isDarkTheme ? "EVT:THEME:DARK" : "EVT:THEME:LIGHT";
            pDataCharacteristic->setValue((uint8_t*)evt, strlen(evt));
            pDataCharacteristic->notify();
          }
          delay(140);
        }
        prevX = -1; prevY = -1;
        return;
      }

      // Active digital ink drawing on the IPS display glass
      uint16_t ink = getInkColor();
      if (prevX > 0 && prevY > 0) {
        tft.drawLine(prevX, prevY, touchX, touchY, ink);
        tft.drawLine(prevX + 1, prevY, touchX + 1, touchY, ink);
        tft.drawLine(prevX - 1, prevY, touchX - 1, touchY, ink);
        tft.drawLine(prevX, prevY + 1, touchX, touchY + 1, ink);
        tft.drawLine(prevX, prevY - 1, touchX, touchY - 1, ink);
      } else {
        tft.fillCircle(touchX, touchY, 2, ink);
        Serial.printf("[PAD TOUCH START] X:%d, Y:%d\n", touchX, touchY);
      }
      prevX = touchX;
      prevY = touchY;

      // Stream to Mobile App in Real-Time (<10ms)
      if (phoneConnected && pDataCharacteristic) {
        if (touchX != lastSentX || touchY != lastSentY || (now - lastStreamTime >= 10)) {
          lastStreamTime = now;
          lastSentX = touchX;
          lastSentY = touchY;
          wasDownLastFrame = true;

          char packet[24];
          snprintf(packet, sizeof(packet), "X:%d,Y:%d", touchX, touchY);
          pDataCharacteristic->setValue((uint8_t*)packet, strlen(packet));
          pDataCharacteristic->notify();
        }
      }
    } else {
      missedFrames++;
      if (phoneConnected && pDataCharacteristic && wasDownLastFrame) {
        wasDownLastFrame = false;
        lastSentX = -1;
        lastSentY = -1;
        Serial.printf("[PAD TOUCH LIFT]\n");

        char packet[12] = "X:0,Y:0";
        pDataCharacteristic->setValue((uint8_t*)packet, 7);
        pDataCharacteristic->notify();
      }
      if (missedFrames >= 2) {
        prevX = -1;
        prevY = -1;
      }
    }
  }

  delay(2); // 2ms yield for radio stack & FreeRTOS stability
}
