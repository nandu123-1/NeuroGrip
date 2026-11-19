# NeuroGrip: System Usage & Clinical Operation Manual

Welcome to the **NeuroGrip Neuromuscular Smart Pen & Digital Assessment Ecosystem**. This guide covers step-by-step instructions for patients, occupational therapists, neurologists, and engineering teams.

---

## 🎯 System Overview

NeuroGrip is an intelligent assistive medical device engineered for patients with Parkinson’s disease, essential tremor, arthritis, and pediatric motor dysgraphia. The ecosystem operates across three seamlessly synchronized components:

1. **NeuroGrip Smart Pen (Seeed Studio XIAO nRF52840 Sense):**
   - Ergonomic two-part 3D-printed enclosure with weighted low-center-of-gravity stabilization.
   - Interlink FSR 402 high-sensitivity pinch force sensor (12-bit ADC: 0–4095, calibrated 0–850g).
   - InvenSense MPU-6050 6-DOF IMU tracking 3-axis acceleration and involuntary tremor spectrum (3–12 Hz).
   - 0.96" SSD1306 OLED display showing live force readouts, personalized safe envelope, and biofeedback status.
   - 8-LED WS2812B NeoPixel ring and non-blocking haptic vibrator for real-time sensory coaching.

2. **NeuroGrip Capacitive Writing Pad (ESP32 DevKit V1):**
   - 3.5-inch Waveshare IPS display (ST7796S, 480×320 resolution, 4-wire SPI @ 40 MHz).
   - Goodix GT911 capacitive multi-touch digitizer sampled at deterministic 100 Hz (10ms).
   - Sub-10ms digital inking latency with clinical handwriting guides (Upper, Lower, Neuro-Shapes, Freehand).

3. **NeuroGrip Companion App (Android / React Native / Expo):**
   - Autonomous dual-peripheral BLE coordinator running real-time telemetry streaming at <15ms.
   - Clinical analytics dashboard computing tremor spectrum, peak pinch force, and motor fatigue.
   - On-device and cloud-synchronized AI diagnostic classifier for early motor impairment detection.

---

## 🚀 Step-by-Step Operating Instructions

### Step 1: Powering On the Hardware
1. **Smart Pen:**
   - Slide the power switch on the pen body to **ON**.
   - The SSD1306 OLED display will initialize and show `NEUROGRIP PEN - SYSTEM READY`.
   - The WS2812B NeoPixel ring will pulse with a gentle Cyan/Blue breathing animation indicating it is advertising via BLE.
2. **Writing Pad:**
   - Connect the ESP32 Writing Pad to USB-C power (or internal battery pack).
   - The 3.5" IPS display will show the clinical interface header with connection status badges:
     - `PAD: READY`
     - `APP: SEARCHING`
     - `PEN: WAITING`

### Step 2: Launching the Companion App
1. Open the **NeuroGrip Companion App** on your Android smartphone or tablet.
2. Ensure Bluetooth and Location services are enabled.
3. The app automatically scans and establishes direct, concurrent BLE links to both devices:
   - Green badge: `● Pen + Pad Connected`
   - Real-time telemetry cards will immediately begin populating with live pinch load, tremor frequency, and stylus position.

### Step 3: Calibrating Personalized Pinch Thresholds
Every patient's muscular grip capability is unique. NeuroGrip automatically personalizes the biofeedback envelope:
1. Navigate to the **Device Hub** tab in the mobile app.
2. Select your clinical patient profile (e.g., *Adult Baseline*, *Pediatric Motor Training*, or *Parkinson's Tremor Protocol*).
3. The app transmits the configured safe limits directly to the Smart Pen over BLE:
   - `CMD:GRAMS:120,260` (Example: Safe range = 120g to 260g).
4. The pen confirms with an audible chirp and immediately updates its OLED screen:
   - `ENVELOPE: 120-260g`
   - Dynamic tick marks on the graphical force bar automatically adjust to the patient's exact physical targets.

### Step 4: Conducting Handwriting & Motor Exercises
1. On the **Live Pad Mirror** tab:
   - Choose your exercise mode:
     - **Freehand Inking:** Open creative canvas for handwriting or drawing.
     - **Alphabet Tracing:** Guided uppercase (A–E), lowercase (a–e), or neuro-motor assessment patterns (Archimedean spirals and sinusoidal meanders).
2. The patient writes directly on the glass surface of the Writing Pad using the Smart Pen.
3. Strokes are inked instantaneously on the Pad's IPS display and mirrored in real-time (<15ms) on the mobile device.

### Step 5: Real-Time Multi-Sensory Biofeedback
During writing, the Smart Pen monitors force and tremor at 100 Hz, coaching the patient in real time:

| Pinch Force Level | OLED Status Display | NeoPixel LED Ring | Haptic Buzzer | Action Needed |
| :--- | :--- | :--- | :--- | :--- |
| **0 - 20g** | `STATUS: RESTING` | Dim Soft Teal | Silent | Stylus lifted / hover state |
| **20g - Min Safe (e.g. 120g)** | `STATUS: LIGHT TOUCH` | Soft Cyan | Silent | Grip is light; apply slight firm hold |
| **Min - Max Safe (120 - 260g)** | `STATUS: OPTIMAL ZONE` | **Solid Emerald Green** | Silent | **Perfect grip pressure. Keep writing!** |
| **Exceeds Max (> 260g)** | `STATUS: ! OVERGRIP !` | **Flashing Crimson Red** | 55ms Pulse | Excessive tension; consciously relax fingers |
| **Involuntary Tremor (> 6.0 Hz)** | `STATUS: TREMOR DETECTED` | Pulsing Amber | Micro-Chirp | Rest hand on pad surface to stabilize |

### Step 6: Reviewing Clinical Analytics & AI Diagnostics
1. Open the **Therapist Analytics** tab to view:
   - Real-time pinch force distribution chart.
   - Tremor frequency power spectrum (Hz).
   - Motor fatigue decay slope over time.
2. Select **Run AI Neuromuscular Assessment**:
   - The built-in ensemble classifier evaluates 30 kinematic features extracted from the handwriting session.
   - Outputs a validated risk score and provides clinical recommendations for physical therapy.

---

## 🔧 Maintenance & Troubleshooting

- **Touch not registering on Writing Pad:**
  - Ensure the 13-pin GH1.25 cable or GPIO pins are seated firmly.
  - Press the physical ESP32 reset button; the firmware runs an autonomous I2C bus recovery routine on boot.
- **Pen shows constant red overgrip:**
  - Verify personalized profile in Companion App -> Device Hub. Tap **Sync Thresholds** to calibrate baseline grams.
- **Re-pairing BLE:**
  - If a device disconnects, pull down to refresh on Device Hub or restart the app. The auto-reconnect engine will resume the link in <1.5s.
