# NeuroGrip: Hardware Architecture & Wiring Specifications

This document outlines the component pinouts, schematics, electrical characteristics, and bill of materials (BOM) for both the **NeuroGrip Smart Pen** and the **NeuroGrip Writing Pad**.

---

## 🖊️ Subsystem 1: NeuroGrip Smart Pen

### Component Bill of Materials (BOM)
- **Main Microcontroller:** Seeed Studio XIAO nRF52840 Sense (64 MHz ARM Cortex-M4F, Bluetooth 5.0, 1MB Flash, 256KB RAM).
- **Force Sensor:** Interlink Electronics FSR 408 (Linear Strip Active Sensing Area, $0.1\text{N} - 10\text{N}$ continuous grip & tip pressure range).
- **Motion Sensor:** InvenSense MPU-6050 (GY-521 breakout, 3-axis accelerometer + 3-axis gyroscope @ 400 kHz I2C).
- **OLED Display:** SSD1306 0.96-inch monochrome I2C OLED ($128 \times 64$ pixels, address `0x3C`).
- **Visual Biofeedback:** Adafruit WS2812B 8-Pixel Addressable NeoPixel Ring (5050 RGB SMD LEDs).
- **Acoustic & Tactile Feedback:** 3V-5V Micro Piezo Buzzer (high-pitch kinetic tremor alert) + 3V DC Miniature Haptic Vibration Motor.
- **Power:** 3.7V 350mAh–500mAh LiPo rechargeable cell with onboard MCP73831 battery charge controller.

### Pinout Table (Seeed XIAO nRF52840 Sense)

| Pin Name | Physical Pin | Connected Component | Function / Interface |
| :--- | :--- | :--- | :--- |
| **A0 / D0** | Pin 1 | Interlink FSR 408 + 10kΩ Pull-down | Analog Grip & Pinch Force Input (12-bit ADC) |
| **D1** | Pin 2 | WS2812B NeoPixel Ring DIN | Single-wire High-speed Timing @ 800 kHz |
| **D2** | Pin 3 | Micro Piezo Buzzer (+) | Discrete Tone / Spasm Audio Alert |
| **D3** | Pin 4 | DC Micro Haptic Motor Driver | Discrete PWM Tactile Vibration Alert |
| **D4 / SDA** | Pin 5 | SSD1306 OLED SDA & MPU-6050 SDA | Shared Hardware I2C Data (`Wire`) |
| **D5 / SCL** | Pin 6 | SSD1306 OLED SCL & MPU-6050 SCL | Shared Hardware I2C Clock (`400 kHz`) |
| **LED_RED** | Internal P11 | Onboard Multi-Color Red LED | Low Active Overgrip Visual Indicator |
| **LED_GREEN**| Internal P13 | Onboard Multi-Color Green LED | Low Active Optimal Zone Visual Indicator |
| **LED_BLUE** | Internal P12 | Onboard Multi-Color Blue LED | Low Active BLE Searching Indicator |
| **3V3** | Pin 11 | Power Rails (OLED, IMU, FSR, Ring) | Regulated 3.3V Logic Supply |
| **GND** | Pin 12 | Common Ground Plane | Common System Ground |

---

## 📱 Subsystem 2: NeuroGrip Writing Pad

### Component Bill of Materials (BOM)
- **Main Microcontroller:** ESP32 DevKit V1 (Tensilica Xtensa Dual-Core 240 MHz, 520KB SRAM, 4MB SPI Flash).
- **Display Module:** 7.0-inch 800x480 TFT LCD Display Module (4-Wire SPI / Parallel Interface).
- **Touch Controller:** 4-Wire Resistive Touch Digitizer (XPT2046 / ADS7846 SPI Controller).
- **Audio Output:** 4Ω 3W–5W Full-Range Multimedia Speaker (40mm–50mm dynamic cone, not mini) + PAM8403 3W Class-D Audio Amplifier.
- **Power & Battery:** 3.7V 3000mAh Rechargeable Li-ion/LiPo Battery with TP4056 Type-C Charging & 5V Step-Up Boost Module.
- **Interconnect:** 16-Pin / 20-Pin Ribbon Cable Harness.

### Pinout Table (ESP32 DevKit V1 to Waveshare 3.5" (F) LCD)

| LCD Pin Name | GH1.25 Pin | ESP32 GPIO | Description / Mode |
| :--- | :--- | :--- | :--- |
| **T_RST** | Pin 1 | **GPIO 14** | GT911 Touch Reset (Active Low) |
| **T_INT** | Pin 2 | **GPIO 27** | GT911 Touch Interrupt Line |
| **T_SCL** | Pin 3 | **GPIO 22** | GT911 I2C Clock (`Wire`) |
| **T_SDA** | Pin 4 | **GPIO 21** | GT911 I2C Data (`Wire`) |
| **GND** | Pin 5 | **GND** | System Ground |
| **VCC** | Pin 6 | **5V / VIN** | Main Power Supply (5V regulated to 3.3V) |
| **LCD_BL** | Pin 7 | **GPIO 32** | Display Backlight Enable (PWM / HIGH) |
| **LCD_SCK** | Pin 8 | **GPIO 18** | SPI Clock (`VSPI_SCLK` @ 40 MHz) |
| **LCD_MISO**| Pin 9 | **GPIO 19** | SPI Master In Slave Out (`VSPI_MISO`) |
| **LCD_MOSI**| Pin 10 | **GPIO 23** | SPI Master Out Slave In (`VSPI_MOSI`) |
| **LCD_CS** | Pin 11 | **GPIO 15** | ST7796S Chip Select (Active Low) |
| **LCD_DC** | Pin 12 | **GPIO 2** | ST7796S Data / Command Selector |
| **LCD_RST**| Pin 13 | **GPIO 4** | ST7796S Hardware Reset (Active Low) |

---

## ⚡ Electrical & Power Safety Guidelines
1. **Isolated Power & Logic Regulators:** The ESP32 5V rail is powered via USB-C with dedicated decoupling capacitors ($10\mu\text{F}$ electrolytic + $100\text{nF}$ ceramic) across power terminals.
2. **I2C Bus Pull-Ups:** Internal ESP32 pull-ups are enabled, complemented by $4.7\text{k}\Omega$ resistors on the Waveshare display PCB for sharp clock edges at 400 kHz.
3. **I2C Autonomous Bus Recovery:** The ESP32 firmware includes a 9-clock pulse recovery loop on `GPIO 22` to release any hung slave on the I2C bus before starting GT911 communications.
