# NeuroGrip: BLE Telemetry & High-Speed Protocol Specification

This document details the Bluetooth Low Energy (BLE) communication architecture, service definitions, characteristic specifications, packet payloads, and latency optimizations implemented across the **NeuroGrip Ecosystem**.

---

## 📡 Topology Architecture

```
                  +--------------------------------+
                  |    Mobile Companion App        |
                  |  (BLE Central / Coordinator)   |
                  +---------------+----------------+
                                  |
            +---------------------+---------------------+
            | (Sub-15ms Link)                           | (Sub-10ms Link)
            v                                           v
+-----------------------+                   +-----------------------+
|  NeuroGrip Smart Pen  |                   | NeuroGrip Writing Pad |
|   (BLE Peripheral)    |                   |   (BLE Peripheral)    |
| XIAO nRF52840 Sense   |                   | ESP32 + GT911 Digitizer|
+-----------------------+                   +-----------------------+
```

Both physical hardware units operate as independent BLE Peripherals that connect concurrently to the Android Companion App acting as the master Central Hub.

---

## 🔑 Service & Characteristic UUIDs

Both devices utilize the standard NeuroGrip 128-bit Nordic/Custom BLE UUID profile:

| Entity | UUID | Properties | Purpose |
| :--- | :--- | :--- | :--- |
| **Primary Service** | `19B10000-E8F2-537E-4F6C-D104768A1214` | Primary | NeuroGrip Ecosystem Service |
| **Data Characteristic** | `19B10001-E8F2-537E-4F6C-D104768A1214` | `READ`, `NOTIFY` | High-frequency telemetry stream from device to app |
| **Command Characteristic** | `19B10002-E8F2-537E-4F6C-D104768A1214` | `WRITE`, `WRITE_NR` | Low-latency control commands from app to device |

---

## 📦 Packet Payload Formats

### 1. Smart Pen to Mobile App (Data Characteristic Notify @ 25 Hz)
The Smart Pen streams compact ASCII-delimited telemetry packets designed to fit within a single unfragmented 23-byte BLE MTU:

#### Active Sensor Packet:
```
P:<raw_adc>,G:<grams>,T:<tremor_magnitude>
```
- `P` (integer): 12-bit raw FSR ADC reading ($0 - 4095$).
- `G` (integer): Calibrated pinch force in grams ($0 - 850\text{g}$).
- `T` (integer): 3-axis differential vector acceleration magnitude from MPU-6050 ($0 - 15000$).

*Example Payload:* `P:1840,G:215,T:1420` (Payload size: 18 bytes).

---

### 2. Writing Pad to Mobile App (Data Characteristic Notify @ 100 Hz)
The capacitive digitizer streams coordinate positions immediately when contact moves or at least every 10ms:

#### Touch Down / Coordinate Stream:
```
X:<x_coordinate>,Y:<y_coordinate>
```
- `X` (integer): Clamped horizontal screen coordinate ($0 - 479$).
- `Y` (integer): Clamped vertical screen coordinate ($0 - 319$).

*Example Payload:* `X:245,Y:180` (Payload size: 9 bytes).

#### Touch Lift / Pen Release:
```
X:0,Y:0
```
Sent exactly once upon stylus or finger lift to signal the end of the current drawing stroke.

#### Writing Pad UI Events:
- `EVT:CLEAR`: Sent when the physical CLEAR button on the LCD header is pressed.
- `EVT:MODE:<0-3>`: Sent when the MODE button cycles through display patterns ($0=\text{Free}, 1=\text{Upper}, 2=\text{Lower}, 3=\text{Neuro}$).
- `EVT:THEME:DARK` / `EVT:THEME:LIGHT`: Sent when the theme toggle button is tapped.

---

### 3. Mobile App to Smart Pen (Command Characteristic Write)

#### Synchronize Personalized Pinch Envelope:
```
CMD:GRAMS:<min_grams>,<max_grams>
```
- Transmits calibrated clinical boundaries (e.g., `CMD:GRAMS:120,260`).
- The Smart Pen converts grams into hardware ADC counts (`gramsToAdc()`), updates its SSD1306 OLED screen (`ENVELOPE: 120-260g`), and chirps the haptic buzzer in confirmation.

#### Manual Haptic Feedback Trigger:
```
BUZZ:<duration_ms>
```
- Triggers non-blocking tactile feedback pulse for patient guidance (e.g., `BUZZ:100`).

---

### 4. Mobile App to Writing Pad (Command Characteristic Write)

#### Canvas Clear & Mode Selection:
- `CMD:CLEAR`: Immediately clears the ST7796S display and resets digital inking buffers.
- `CMD:MODE:FREE`: Switches digitizer to unrestricted freehand drawing mode.
- `CMD:MODE:ALPHA:UPPER`: Draws clinical uppercase guideline grid (A–E).
- `CMD:MODE:ALPHA:LOWER`: Draws clinical lowercase guideline grid (a–e).
- `CMD:MODE:ALPHA:NEURO`: Draws clinical diagnostic patterns (Archimedean spirals and sinusoidal meanders).
- `CMD:THEME:DARK` / `CMD:THEME:LIGHT`: Syncs background and inking palette.
- `PEN:1` / `PEN:0`: Notifies the Writing Pad header whether the Smart Pen is active.

---

## ⚡ Latency & Timing Parameters

To achieve sub-15ms end-to-end responsiveness without UI thread stutter:

| Parameter | Writing Pad (ESP32) | Smart Pen (nRF52840) |
| :--- | :--- | :--- |
| **Connection Interval** | $7.5\text{ms} - 11.25\text{ms}$ (`min: 6, max: 9`) | $7.5\text{ms} - 12.5\text{ms}$ (`min: 6, max: 10`) |
| **Slave Latency** | $0$ (zero skipped intervals) | $0$ (zero skipped intervals) |
| **Supervision Timeout** | $400\text{ms}$ | $500\text{ms}$ |
| **Sampling Frequency** | $100\text{ Hz}$ ($10\text{ms}$) | $100\text{ Hz}$ sensor, $25\text{ Hz}$ BLE |
| **PHY Mode** | 1M LE / 2M LE Auto-negotiated | 2M LE High-Speed PHY |
| **Throughput** | ~800 bytes/sec | ~450 bytes/sec |
