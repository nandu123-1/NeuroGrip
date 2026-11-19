# NeuroGrip: Intelligent Neuromuscular Smart Pen & Capacitive Writing Pad Ecosystem

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PlatformIO](https://img.shields.io/badge/PlatformIO-ESP32-orange.svg)](https://platformio.org/)
[![Arduino](https://img.shields.io/badge/Arduino-nRF52840-teal.svg)](https://www.arduino.cc/)
[![React Native](https://img.shields.io/badge/React%20Native-Expo%2051-61DAFB.svg)](https://reactnative.dev/)
[![Hugging Face Model](https://img.shields.io/badge/Hugging%20Face-neurogrip--model-yellow.svg)](https://huggingface.co/Sunraku02/neurogrip-model)
[![Hugging Face Dataset](https://img.shields.io/badge/Hugging%20Face-neurogrip--dataset-green.svg)](https://huggingface.co/datasets/Sunraku02/neurogrip-dataset)

**NeuroGrip** is an end-to-end medical-assistive hardware and artificial intelligence platform designed to empower patients with neuromuscular motor disorders—including **Parkinson's Disease, Essential Tremor, Motor Dysgraphia, and Arthritis**—through real-time sensory biofeedback and precision kinematic assessment.

---

## 🏗️ System Architecture

```
                  +----------------------------------------------+
                  |           Android Companion App              |
                  |          (BLE Central Coordinator)           |
                  |  - Live Digitizer Mirror (<15ms Latency)     |
                  |  - Dynamic Profile & Threshold Calibration   |
                  |  - Therapist Analytics & Biometric Charts    |
                  +----------------------+-----------------------+
                                         |
                +------------------------+------------------------+
                | (Sub-15ms Direct Link)                          | (Sub-10ms Direct Link)
                v                                                 v
+-------------------------------+               +----------------------------------+
|      NeuroGrip Smart Pen      |               |      NeuroGrip Writing Pad       |
|    Seeed XIAO nRF52840 Sense  |               |       ESP32 DevKit V1 Board      |
|-------------------------------|               |----------------------------------|
| • Interlink FSR 402 (12-bit)  |               | • Waveshare 3.5" IPS LCD (ST7796S|
| • MPU-6050 6-DOF IMU (Tremor) |               | • Goodix GT911 Multi-touch (100Hz|
| • SSD1306 0.96" OLED Display  |               | • Real-time Digital Inking Glass |
| • WS2812B 8-LED NeoPixel Ring |               | • Guided Tracing (Upper/Lower/PD)|
| • Non-blocking Haptic Buzzer  |               | • Sub-10ms Touch Coordinate Stream
+-------------------------------+               +----------------------------------+
                |                                                 |
                +------------------------+------------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |         NeuroGrip AI Diagnostic Engine       |
                  |   Calibrated Ensemble: XGBoost + LightGBM    |
                  |    + Random Forest + Extra Trees Classifier  |
                  |   Sensitivity: 86.9% | ROC-AUC: 0.77         |
                  +----------------------------------------------+
```

---

## 📁 Repository Directory Structure

```
NeuroGrip/
├── README.md                           # Master Project Overview, Setup & Documentation
├── app/                                # Mobile Companion App (React Native, TypeScript, Expo)
│   ├── src/
│   │   ├── screens/                    # LiveCanvasScreen, DeviceHubScreen, TherapistAnalyticsScreen...
│   │   ├── store/                      # Zustand state engines: useBleStore, useAiStore, useThemeStore
│   │   ├── components/                 # Biofeedback gauges, charts, custom icons, interactive games
│   │   └── theme/                      # Dynamic dark/light medical color tokens
│   ├── android/                        # Native Android Gradle configuration & release setup
│   ├── App.tsx                         # Root application entry with auto-reconnect engine
│   └── package.json
├── firmware/                           # Embedded Firmware Subsystems
│   ├── smart_pen/                      # Seeed Studio XIAO nRF52840 Sense Firmware (Arduino)
│   │   └── NeuroGrip_Pen_BLE.ino       # 100Hz FSR/IMU sampling, non-blocking OLED & LED biofeedback
│   ├── writing_pad/                    # Waveshare 3.5" (F) ST7796S + GT911 Firmware (PlatformIO)
│   │   ├── platformio.ini              # 40MHz SPI display flags & library dependencies
│   │   └── src/main.cpp                # 100Hz GT911 touch polling, I2C bus recovery, BLE streaming
│   └── legacy_hub/                     # Legacy ESP32 Dual-BLE Bridge Firmware
│       └── NeuroGrip_Pad_Hub_BLE.ino
├── ai_model/                           # AI & Kinematic Motor Assessment (neurogrip-ai)
│   ├── neurogrip-detector/             # Trained Ensemble Model Artifacts
│   │   ├── model.joblib                # 3.58 MB calibrated ensemble model weights
│   │   ├── pipeline_meta.json          # 30 selected features & calibrated threshold (0.335)
│   │   └── README.md                   # Model card with Python inference snippet
│   ├── scripts/                        # Feature extraction, cross-validation & evaluation scripts
│   └── data/                           # Processed feature-engineered dataset splits
├── cad_hardware/                       # 3D Mechanical Designs & Physical Blueprints
│   ├── 3d_models/                      # 3D printable STL files (shells, chassis, grip housing)
│   ├── cad_assemblies/                 # Master STEP CAD files
│   ├── parametric_generators/          # FreeCAD & Python parametric CAD generation scripts
│   ├── blender/                        # Photorealistic Blender 3D lookdev models (.blend)
│   └── freecad/                        # Parametric FreeCAD project files (.FCStd)
└── docs/                               # Engineering & Clinical Documentation
    ├── USAGE_GUIDE.md                  # Comprehensive operating manual for patients & clinicians
    ├── BLE_COMMUNICATION_PROTOCOL.md   # Packet payloads, MTU sizes, and low-latency parameters
    ├── HARDWARE_SPECIFICATIONS.md      # Pinout tables, schematics, and component BOM
    ├── AI_METHODOLOGY.md               # 30-biomarker feature engineering & validation results
    └── diagrams/                       # High-resolution engineering schematics (PDF / SVG)
```

---

## 🚀 Quickstart: Setup & Installation

### 1. Smart Pen Firmware (Seeed XIAO nRF52840 Sense)
```bash
# Compile using arduino-cli
arduino-cli compile -b Seeeduino:mbed:xiaonRF52840Sense firmware/smart_pen

# Upload to Smart Pen via USB CDC
arduino-cli upload -p /dev/ttyACM0 -b Seeeduino:mbed:xiaonRF52840Sense firmware/smart_pen
```

### 2. Writing Pad Firmware (ESP32 DevKit V1)
```bash
# Navigate to PlatformIO project directory
cd firmware/writing_pad

# Build and flash to ESP32
pio run -t upload -e esp32doit-devkit-v1
```

### 3. Mobile Companion App (Android)
```bash
# Navigate to app directory
cd app

# Install dependencies
npm install

# Start Expo development server or build release APK
npx expo run:android
# Or compile native release APK:
cd android && ./gradlew assembleRelease
```

---

## 🎯 System Usage Guide

### Step 1: Power On Devices
- **Smart Pen:** Slide power switch to **ON**. The 0.96" OLED will display `NEUROGRIP PEN - SYSTEM READY` and the NeoPixel ring will pulse with gentle cyan breathing while advertising via BLE.
- **Writing Pad:** Plug in USB-C power. The 3.5" IPS display boots directly into the clinical interface with live status header badges.

### Step 2: Launch the App & Dual-BLE Connection
- Launch the **NeuroGrip Companion App** on your Android device.
- The app automatically connects concurrently to both the **Writing Pad** and **Smart Pen**:
  - Top status pill confirms: `● Pen + Pad Connected`.
  - Pinch force and tremor spectrum immediately stream live to the dashboard.

### Step 3: Calibrate Personalized Pinch Safe Envelopes
- In **Device Hub**, select the patient profile (*Adult Baseline*, *Pediatric Motor Training*, or *Parkinson's Protocol*).
- The app sends calibrated limits over BLE (`CMD:GRAMS:120,260`).
- The Smart Pen confirms with an audible chirp and updates its OLED: `ENVELOPE: 120-260g`.

### Step 4: Multi-Sensory Biofeedback during Handwriting
While writing or tracing on the Writing Pad, the Smart Pen monitors force and tremor at 100 Hz:

| Pinch Force | OLED Status | NeoPixel LED Ring | Haptics | Clinical Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **0 - 20g** | `STATUS: RESTING` | Dim Soft Teal | Silent | Stylus lifted / hover state |
| **20 - 120g** | `STATUS: LIGHT TOUCH` | Soft Cyan | Silent | Approaching safe envelope |
| **120 - 260g** | `STATUS: OPTIMAL ZONE` | **Solid Emerald Green** | Silent | **Optimal pinch force. Target achieved.** |
| **> 260g** | `STATUS: ! OVERGRIP !` | **Flashing Crimson Red** | 55ms Pulse | Excessive tension / spasm. Relax grip. |
| **Tremor > 6Hz** | `STATUS: TREMOR DETECTED`| Pulsing Amber | Micro-Chirp | Involuntary kinetic tremor detected. |

---

## 🌐 Public Hugging Face Hub Repositories

| Asset | Repository URL | Content Description |
| :--- | :--- | :--- |
| **AI Model Hub** | [https://huggingface.co/Sunraku02/neurogrip-model](https://huggingface.co/Sunraku02/neurogrip-model) | Calibrated 4-model ensemble weights (`model.joblib`), pipeline metadata, and feature encoders |
| **Dataset Hub** | [https://huggingface.co/datasets/Sunraku02/neurogrip-dataset](https://huggingface.co/datasets/Sunraku02/neurogrip-dataset) | PaHaW & NewHandPD raw time-series coordinate streams + 30-feature engineered CSV training splits |

---

## 👥 Team Members & Roles

- **Addagulla Vikas ([@vikasgupta20](https://github.com/vikasgupta20))** — Team Lead, App Development
- **Challa Spurthi ([@spurthireddy280](https://github.com/spurthireddy280))** — Presenter, Embedded Systems
- **Meela Amrutha ([@meela-amrutha](https://github.com/meela-amrutha))** — Hardware, UI/UX Design
- **Anishetty Siddartha ([@siddarthaanishetty19-pixel](https://github.com/siddarthaanishetty19-pixel))** — Research, Hardware
- **Palla Geetesh Nandan ([@nandu123-1](https://github.com/nandu123-1))** — 3D Modelling, ML Training

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](app/LICENSE) file for details.
