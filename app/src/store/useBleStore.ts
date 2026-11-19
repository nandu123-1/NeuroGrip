import { create } from 'zustand';
import { BleManager, Device, BleError, Subscription } from 'react-native-ble-plx';
import { PermissionsAndroid, Platform } from 'react-native';
import base64 from 'react-native-base64';

// Service & Characteristic UUIDs for Direct Dual-Device Architecture
export const HUB_DEVICE_NAME = 'NeuroGrip_Hub';
export const PAD_DEVICE_NAME = 'NeuroGrip_Pad';
export const PEN_DEVICE_NAME = 'NeuroGrip_Pen';
export const SERVICE_UUID = '19B10000-E8F2-537E-4F6C-D104768A1214';
export const CHARACTERISTIC_DATA_UUID = '19B10001-E8F2-537E-4F6C-D104768A1214';
export const CHARACTERISTIC_CMD_UUID = '19B10002-E8F2-537E-4F6C-D104768A1214';

export const bleManager = new BleManager();

export interface Point {
  x: number;
  y: number;
  pressure: number;
}

export type Stroke = Point[];

export type ConnectionStatus = 'Disconnected' | 'Scanning' | 'Connecting' | 'Connected';

export interface FsrCalibration {
  adcZero: number;          // Tare baseline (ADC with no pressure)
  adcReference: number;     // Reference grip ADC
  referenceGrams: number;   // Target grams at reference grip (e.g. 250g)
  exponent: number;         // Power-law exponent
  isCalibrated: boolean;
}

export function convertFsrAdcToGrams(rawAdc: number, calib?: FsrCalibration): number {
  if (rawAdc <= 200) return 0;
  // Exact 1:1 mathematical match with Smart Pen firmware OLED display: map(rawAdc, 200, 4000, 20, 600)
  const g = 20 + ((rawAdc - 200) * (600 - 20)) / (4000 - 200);
  return Math.max(0, Math.min(850, Math.round(g)));
}

export function convertGramsToFsrAdc(grams: number, calib?: FsrCalibration): number {
  if (grams <= 20) return 200;
  // Inverse of exact Smart Pen OLED mapping: map(rawAdc, 200, 4000, 20, 600)
  const adc = 200 + ((grams - 20) * (4000 - 200)) / (600 - 20);
  return Math.max(0, Math.min(4095, Math.round(adc)));
}

interface BleState {
  status: ConnectionStatus;       // Overall status: 'Connected' if pen or pad connected
  penStatus: ConnectionStatus;    // Smart Pen link status
  padStatus: ConnectionStatus;    // Writing Pad link status
  
  penDevice: Device | null;
  padDevice: Device | null;
  device: Device | null;          // Compatibility alias (padDevice || penDevice)
  
  // Real-time Telemetry
  touchX: number;
  touchY: number;
  isTouched: boolean;
  pressure: number;            // 0 - 4095
  pressureGrams: number;       // Calibrated 0 - 850g
  tremor: number;              // Tremor Magnitude
  tremorHz: number;            // Tremor Frequency
  penBattery: number;          // 0 - 100%
  interventions: number;

  // FSR 402 Calibration
  fsrCalibration: FsrCalibration;
  setFsrTareZero: (zeroAdc?: number) => void;
  setFsrReferenceGrip: (refAdc?: number, targetGrams?: number) => void;
  resetFsrCalibration: () => void;
  
  // Interactive Canvas Strokes
  strokes: Stroke[];
  currentStroke: Stroke | null;
  testMode: 'free' | 'alphabet';
  alphabetSet: 'upper' | 'lower' | 'neuro';
  
  // Simulation Mode
  isSimulated: boolean;

  // Actions
  connectAndStartListening: () => Promise<void>;
  disconnect: () => Promise<void>;
  resetInterventions: () => void;
  clearStrokes: () => void;
  setTestMode: (mode: 'free' | 'alphabet') => void;
  setAlphabetSet: (setKey: 'upper' | 'lower' | 'neuro') => Promise<void>;
  sendCommand: (cmd: string) => Promise<void>;
  sendToPad: (cmd: string) => Promise<void>;
  sendToPen: (cmd: string) => Promise<void>;
  toggleSimulation: () => void;
  triggerBuzzerHaptic: () => Promise<void>;
  syncPersonalizedLimitsToPen: (minGrams?: number, maxGrams?: number) => Promise<boolean>;
}

let penMonitorSubscription: Subscription | null = null;
let penDisconnectSubscription: Subscription | null = null;
let padMonitorSubscription: Subscription | null = null;
let padDisconnectSubscription: Subscription | null = null;
let simInterval: ReturnType<typeof setInterval> | null = null;
let wasTriggered = false;
let isScanningActive = false;
let lastTelemetrySetTime = 0;
let lastAiCheckTime = 0;

export const useBleStore = create<BleState>((set, get) => ({
  status: 'Disconnected',
  penStatus: 'Disconnected',
  padStatus: 'Disconnected',
  penDevice: null,
  padDevice: null,
  device: null,
  
  touchX: 0,
  touchY: 0,
  isTouched: false,
  pressure: 0,
  pressureGrams: 0,
  tremor: 0,
  tremorHz: 0,
  penBattery: 95,
  interventions: 0,
  
  strokes: [],
  currentStroke: null,
  testMode: 'alphabet',
  alphabetSet: 'upper',
  isSimulated: false,

  fsrCalibration: {
    adcZero: 90,
    adcReference: 2600,
    referenceGrams: 250,
    exponent: 0.88,
    isCalibrated: true,
  },

  setFsrTareZero: (zeroAdc?: number) => {
    const live = zeroAdc !== undefined ? zeroAdc : get().pressure;
    set((state) => ({
      fsrCalibration: {
        ...state.fsrCalibration,
        adcZero: Math.max(0, Math.min(200, live)),
        isCalibrated: true,
      },
      pressureGrams: 0,
    }));
    get().sendToPen('CMD:TARE');
  },

  setFsrReferenceGrip: (refAdc?: number, targetGrams = 250) => {
    const live = refAdc !== undefined ? refAdc : get().pressure;
    const base = get().fsrCalibration.adcZero;
    const cleanRef = Math.max(base + 80, live);
    set((state) => ({
      fsrCalibration: {
        ...state.fsrCalibration,
        adcReference: cleanRef,
        referenceGrams: targetGrams,
        isCalibrated: true,
      },
      pressureGrams: targetGrams,
    }));
  },

  resetFsrCalibration: () => {
    set({
      fsrCalibration: {
        adcZero: 90,
        adcReference: 2600,
        referenceGrams: 250,
        exponent: 0.88,
        isCalibrated: false,
      },
    });
  },

  resetInterventions: () => set({ interventions: 0 }),
  
  clearStrokes: () => {
    set({ strokes: [], currentStroke: null });
    get().sendToPad('CMD:CLEAR');
  },

  setTestMode: (mode) => {
    set({ testMode: mode, strokes: [], currentStroke: null });
    if (mode === 'free') {
      get().sendToPad('CMD:MODE:FREE');
    } else {
      const { alphabetSet } = get();
      const cmd = alphabetSet === 'lower' ? 'CMD:MODE:ALPHA:LOWER' :
                  alphabetSet === 'neuro' ? 'CMD:MODE:ALPHA:NEURO' : 'CMD:MODE:ALPHA:UPPER';
      get().sendToPad(cmd);
    }
  },

  setAlphabetSet: async (setKey) => {
    set({ alphabetSet: setKey, strokes: [], currentStroke: null });
    const cmd = setKey === 'lower' ? 'CMD:MODE:ALPHA:LOWER' :
                setKey === 'neuro' ? 'CMD:MODE:ALPHA:NEURO' : 'CMD:MODE:ALPHA:UPPER';
    await get().sendToPad(cmd);
  },

  sendToPad: async (cmd: string) => {
    const { padDevice, padStatus } = get();
    if (padDevice && padStatus === 'Connected') {
      try {
        const cmdBase64 = base64.encode(cmd);
        await padDevice.writeCharacteristicWithoutResponseForService(
          SERVICE_UUID,
          CHARACTERISTIC_CMD_UUID,
          cmdBase64
        );
      } catch (err) {
        try {
          const cmdBase64 = base64.encode(cmd);
          await padDevice.writeCharacteristicWithResponseForService(
            SERVICE_UUID,
            CHARACTERISTIC_CMD_UUID,
            cmdBase64
          );
        } catch (e2) {
          console.warn('[BLE] Could not send to Pad:', cmd, e2);
        }
      }
    }
  },

  sendToPen: async (cmd: string) => {
    const { penDevice, penStatus } = get();
    if (penDevice && penStatus === 'Connected') {
      try {
        const cmdBase64 = base64.encode(cmd);
        await penDevice.writeCharacteristicWithoutResponseForService(
          SERVICE_UUID,
          CHARACTERISTIC_CMD_UUID,
          cmdBase64
        );
      } catch (err) {
        try {
          const cmdBase64 = base64.encode(cmd);
          await penDevice.writeCharacteristicWithResponseForService(
            SERVICE_UUID,
            CHARACTERISTIC_CMD_UUID,
            cmdBase64
          );
        } catch (e2) {
          console.warn('[BLE] Could not send to Pen:', cmd, e2);
        }
      }
    }
  },

  sendCommand: async (cmd: string) => {
    // Intelligent routing to appropriate peripheral
    if (
      cmd.startsWith('CMD:MODE') ||
      cmd.startsWith('CMD:CLEAR') ||
      cmd.startsWith('CMD:THEME') ||
      cmd.startsWith('PEN:')
    ) {
      await get().sendToPad(cmd);
    } else if (
      cmd.startsWith('CMD:GRAMS') ||
      cmd.startsWith('CMD:THRESH') ||
      cmd.startsWith('CMD:TARE') ||
      cmd.startsWith('BUZZ') ||
      cmd.startsWith('SET:LIMIT')
    ) {
      await get().sendToPen(cmd);
    } else {
      await Promise.all([get().sendToPad(cmd), get().sendToPen(cmd)]);
    }
  },

  toggleSimulation: () => {
    const { isSimulated } = get();
    if (isSimulated) {
      if (simInterval) clearInterval(simInterval);
      set({ isSimulated: false, status: 'Disconnected', penStatus: 'Disconnected', padStatus: 'Disconnected' });
    } else {
      set({
        isSimulated: true,
        status: 'Connected',
        penStatus: 'Connected',
        padStatus: 'Connected'
      });
      
      let letterProgress = 0;
      let letterIndex = 0;
      
      const letterWaypoints = [
        [
          { x: 100, y: 240 }, { x: 120, y: 160 }, { x: 140, y: 80 },
          { x: 160, y: 160 }, { x: 180, y: 240 },
          { x: 120, y: 170 }, { x: 160, y: 170 },
        ],
        [
          { x: 220, y: 240 }, { x: 220, y: 160 }, { x: 220, y: 80 },
          { x: 260, y: 80 }, { x: 275, y: 120 }, { x: 235, y: 160 },
          { x: 280, y: 200 }, { x: 250, y: 240 }, { x: 220, y: 240 },
        ]
      ];

      simInterval = setInterval(() => {
        letterProgress += 1;
        const currentPath = letterWaypoints[letterIndex % letterWaypoints.length];
        const step = letterProgress % currentPath.length;
        if (letterProgress % currentPath.length === 0) {
          letterIndex += 1;
        }

        const targetPt = currentPath[step];
        const simX = targetPt.x + Math.round((Math.random() - 0.5) * 2);
        const simY = targetPt.y + Math.round((Math.random() - 0.5) * 2);
        const simPressure = Math.round(340 + 120 * Math.sin(letterProgress * 0.4));
        const simGrams = convertFsrAdcToGrams(simPressure, get().fsrCalibration);
        const simTremor = Math.round(2100 + 1500 * Math.abs(Math.sin(letterProgress * 0.2)));
        const simTremorHz = +(3.6 + Math.sin(letterProgress * 0.1) * 0.8).toFixed(1);

        const newPoint: Point = { x: simX, y: simY, pressure: simPressure };
        const isTriggered = simPressure > 700 || simTremor > 6000;

        set((state) => {
          let newInterventions = state.interventions;
          if (isTriggered && !wasTriggered) {
            newInterventions++;
          }
          wasTriggered = isTriggered;

          const updatedStroke = state.currentStroke ? [...state.currentStroke, newPoint] : [newPoint];

          return {
            touchX: simX,
            touchY: simY,
            isTouched: true,
            pressure: simPressure,
            pressureGrams: simGrams,
            tremor: simTremor,
            tremorHz: simTremorHz,
            interventions: newInterventions,
            currentStroke: updatedStroke.length > 50 ? [] : updatedStroke,
            strokes: updatedStroke.length > 50 ? [...state.strokes, updatedStroke] : state.strokes
          };
        });
      }, 60);
    }
  },

  disconnect: async () => {
    isScanningActive = false;
    try {
      bleManager.stopDeviceScan();
    } catch (e) {}

    if (simInterval) clearInterval(simInterval);

    const { penDevice, padDevice } = get();
    if (penDevice) {
      try {
        await bleManager.cancelDeviceConnection(penDevice.id);
      } catch (e) {}
    }
    if (padDevice) {
      try {
        await bleManager.cancelDeviceConnection(padDevice.id);
      } catch (e) {}
    }

    if (penMonitorSubscription) penMonitorSubscription.remove();
    if (penDisconnectSubscription) penDisconnectSubscription.remove();
    if (padMonitorSubscription) padMonitorSubscription.remove();
    if (padDisconnectSubscription) padDisconnectSubscription.remove();

    set({
      status: 'Disconnected',
      penStatus: 'Disconnected',
      padStatus: 'Disconnected',
      penDevice: null,
      padDevice: null,
      device: null,
      pressure: 0,
      pressureGrams: 0,
      tremor: 0,
      isTouched: false,
      isSimulated: false
    });
  },

  triggerBuzzerHaptic: async () => {
    await get().sendToPen('BUZZ:200');
  },

  syncPersonalizedLimitsToPen: async (minGrams?: number, maxGrams?: number) => {
    const { penDevice, penStatus, sendToPen } = get();
    if (!penDevice || penStatus !== 'Connected') {
      console.log('[BLE] Pen not connected. Threshold will sync upon reconnection.');
      return false;
    }
    try {
      const { useAiStore } = require('./useAiStore');
      const activeProfile = useAiStore.getState().activeProfile;
      const targetMinG = minGrams ?? activeProfile.minSafePinchGrams;
      const targetMaxG = maxGrams ?? activeProfile.maxSafePinchGrams;

      const cmdGrams = `CMD:GRAMS:${targetMinG},${targetMaxG}`;
      await sendToPen(cmdGrams);

      const cmdThresh = `CMD:THRESH:${targetMinG},${targetMaxG}`;
      await sendToPen(cmdThresh);
      console.log(`[BLE] Synced personalized thresholds directly to Pen: ${cmdGrams}`);
      return true;
    } catch (err) {
      console.warn('[BLE] Could not sync thresholds to pen:', err);
      return false;
    }
  },

  connectAndStartListening: async () => {
    // Request Android 12+ BLE Permissions
    if (Platform.OS === 'android' && Platform.Version >= 31) {
      const result = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      ]);
      if (result['android.permission.BLUETOOTH_SCAN'] !== 'granted') {
        console.warn('Bluetooth permissions denied');
        set({ status: 'Disconnected' });
        return;
      }
    }

    const { penStatus, padStatus } = get();
    if (penStatus !== 'Connected' || padStatus !== 'Connected') {
      set({ status: 'Scanning' });
      if (penStatus !== 'Connected') set({ penStatus: 'Scanning' });
      if (padStatus !== 'Connected') set({ padStatus: 'Scanning' });
    }

    if (isScanningActive) {
      return;
    }
    isScanningActive = true;

    console.log('[BLE] Starting dual device discovery for Smart Pen and Writing Pad...');

    bleManager.startDeviceScan(null, null, async (error, scannedDevice) => {
      if (error) {
        console.warn('Scan error:', error);
        isScanningActive = false;
        if (get().penStatus !== 'Connected' && get().padStatus !== 'Connected') {
          set({ status: 'Disconnected', penStatus: 'Disconnected', padStatus: 'Disconnected' });
        }
        return;
      }

      if (!scannedDevice) return;
      const devName = scannedDevice.name || '';

      // 1. Identify Smart Pen
      const isPen = devName === PEN_DEVICE_NAME ||
                    devName === 'NeuroGrip_Pen' ||
                    (devName.includes('NeuroGrip') && devName.includes('Pen'));

      // 2. Identify Writing Pad
      const isPad = devName === PAD_DEVICE_NAME ||
                    devName === HUB_DEVICE_NAME ||
                    devName === 'NeuroGrip_Pad' ||
                    devName === 'NeuroGrip_Hub' ||
                    (devName.includes('NeuroGrip') && (devName.includes('Pad') || devName.includes('Hub')));

      // --- Connect to Smart Pen Directly ---
      if (isPen && !get().penDevice && get().penStatus !== 'Connecting' && get().penStatus !== 'Connected') {
        console.log(`[BLE] Found Smart Pen: '${devName}' (${scannedDevice.id}). Connecting directly...`);
        set({ penStatus: 'Connecting' });

        try {
          const connectedPen = await scannedDevice.connect();
          const penWithServices = await connectedPen.discoverAllServicesAndCharacteristics();
          
          try {
            await connectedPen.requestConnectionPriority(1); // High priority
          } catch (e) {
            console.warn('[BLE] Pen priority request:', e);
          }

          set({
            penDevice: penWithServices,
            penStatus: 'Connected',
            status: 'Connected',
            device: get().padDevice || penWithServices
          });
          console.log('[BLE] Smart Pen connected directly to mobile!');

          // Inform Pad that Pen is active
          if (get().padDevice && get().padStatus === 'Connected') {
            get().sendToPad('PEN:1');
          }

          // Auto-sync personalized limits
          setTimeout(() => {
            get().syncPersonalizedLimitsToPen();
          }, 350);

          if (penDisconnectSubscription) penDisconnectSubscription.remove();
          penDisconnectSubscription = bleManager.onDeviceDisconnected(connectedPen.id, () => {
            console.log('[BLE] Smart Pen disconnected.');
            if (penMonitorSubscription) penMonitorSubscription.remove();
            set({
              penDevice: null,
              penStatus: 'Disconnected',
              status: get().padStatus === 'Connected' ? 'Connected' : 'Disconnected',
              device: get().padDevice
            });
            if (get().padStatus === 'Connected') {
              get().sendToPad('PEN:0');
            }
            setTimeout(() => {
              if (get().penStatus === 'Disconnected') {
                get().connectAndStartListening();
              }
            }, 1200);
          });

          // Monitor Pen Telemetry Stream (P:<fsr>,T:<tremor>)
          if (penMonitorSubscription) penMonitorSubscription.remove();
          penMonitorSubscription = penWithServices.monitorCharacteristicForService(
            SERVICE_UUID,
            CHARACTERISTIC_DATA_UUID,
            (monitorError: BleError | null, characteristic) => {
              if (monitorError || !characteristic?.value) return;
              const raw = base64.decode(characteristic.value);

              const match = raw.match(/P:(\d+)(?:,G:(\d+))?,T:(\d+)/);
              const gripMatch = raw.match(/Grip=(\d+).*?Tremor=([\d.]+)/i);

              if (match || gripMatch) {
                let currentPressure = 0;
                let grams = 0;
                let currentTremor = 0;

                if (match) {
                  currentPressure = parseInt(match[1], 10) || 0;
                  if (match[2] && match[3]) {
                    grams = parseInt(match[2], 10) || 0;
                    currentTremor = parseInt(match[3], 10) || 0;
                  } else if (match[2] && !match[3]) {
                    currentTremor = parseInt(match[2], 10) || 0;
                    grams = convertFsrAdcToGrams(currentPressure);
                  } else {
                    currentTremor = parseInt(match[3] || '0', 10) || 0;
                    grams = convertFsrAdcToGrams(currentPressure);
                  }
                } else if (gripMatch) {
                  currentPressure = parseInt(gripMatch[1], 10) || 0;
                  currentTremor = Math.round(parseFloat(gripMatch[2]) * 1000);
                  grams = convertFsrAdcToGrams(currentPressure);
                }

                // Check dynamically against the personalized safe envelope
                let maxSafeLimit = 260;
                try {
                  const { useAiStore } = require('./useAiStore');
                  const activeProf = useAiStore.getState().activeProfile;
                  if (activeProf && activeProf.maxSafePinchGrams) {
                    maxSafeLimit = activeProf.maxSafePinchGrams;
                  }
                } catch (e) {}

                const isTriggered = grams > maxSafeLimit || currentTremor > 6000;
                const now = Date.now();

                // Throttle React state updates to 30 Hz (33ms) or on threshold trigger to protect UI thread
                if (now - lastTelemetrySetTime >= 33 || isTriggered !== wasTriggered) {
                  lastTelemetrySetTime = now;
                  set((state) => {
                    let newInterventions = state.interventions;
                    if (isTriggered && !wasTriggered) {
                      newInterventions++;
                    }
                    wasTriggered = isTriggered;

                    return {
                      pressure: currentPressure,
                      pressureGrams: grams,
                      tremor: currentTremor,
                      tremorHz: +(3.0 + (currentTremor / 3000)).toFixed(1),
                      interventions: newInterventions
                    };
                  });
                }

                // Autonomous AI threshold monitor sampled at 4 Hz without component re-render loops
                if (now - lastAiCheckTime >= 250) {
                  lastAiCheckTime = now;
                  try {
                    const { useAiStore } = require('./useAiStore');
                    useAiStore.getState().checkLiveTelemetry(
                      grams,
                      +(3.0 + (currentTremor / 3000)).toFixed(1),
                      get().isTouched,
                      () => {
                        get().triggerBuzzerHaptic().catch(() => {});
                      }
                    );
                  } catch (e) {}
                }
              }
            }
          );

          // Stop scanning if both devices connected
          if (get().padStatus === 'Connected') {
            try {
              bleManager.stopDeviceScan();
              isScanningActive = false;
            } catch (e) {}
          }
        } catch (penErr) {
          console.warn('[BLE] Could not connect to Smart Pen:', penErr);
          set({ penStatus: 'Disconnected', penDevice: null });
        }
      }

      // --- Connect to Writing Pad Directly ---
      if (isPad && !get().padDevice && get().padStatus !== 'Connecting' && get().padStatus !== 'Connected') {
        console.log(`[BLE] Found Writing Pad: '${devName}' (${scannedDevice.id}). Connecting directly...`);
        set({ padStatus: 'Connecting' });

        try {
          const connectedPad = await scannedDevice.connect();
          const padWithServices = await connectedPad.discoverAllServicesAndCharacteristics();

          try {
            await connectedPad.requestConnectionPriority(1); // High priority
          } catch (e) {
            console.warn('[BLE] Pad priority request:', e);
          }

          set({
            padDevice: padWithServices,
            padStatus: 'Connected',
            status: 'Connected',
            device: padWithServices
          });
          console.log('[BLE] Writing Pad connected directly to mobile!');

          // Sync initial handwriting mode to Pad
          setTimeout(() => {
            const { testMode, alphabetSet, penStatus, pressure, tremor } = get();
            if (testMode === 'free') {
              get().sendToPad('CMD:MODE:FREE');
            } else {
              const cmd = alphabetSet === 'lower' ? 'CMD:MODE:ALPHA:LOWER' :
                          alphabetSet === 'neuro' ? 'CMD:MODE:ALPHA:NEURO' : 'CMD:MODE:ALPHA:UPPER';
              get().sendToPad(cmd);
            }
            if (penStatus === 'Connected') {
              get().sendToPad('PEN:1');
            }
          }, 350);

          if (padDisconnectSubscription) padDisconnectSubscription.remove();
          padDisconnectSubscription = bleManager.onDeviceDisconnected(connectedPad.id, () => {
            console.log('[BLE] Writing Pad disconnected.');
            if (padMonitorSubscription) padMonitorSubscription.remove();
            set({
              padDevice: null,
              padStatus: 'Disconnected',
              isTouched: false,
              status: get().penStatus === 'Connected' ? 'Connected' : 'Disconnected',
              device: get().penDevice
            });
            setTimeout(() => {
              if (get().padStatus === 'Disconnected') {
                get().connectAndStartListening();
              }
            }, 1200);
          });

          // Monitor Pad Data Characteristic (Touch & Events)
          if (padMonitorSubscription) padMonitorSubscription.remove();
          padMonitorSubscription = padWithServices.monitorCharacteristicForService(
            SERVICE_UUID,
            CHARACTERISTIC_DATA_UUID,
            (monitorError: BleError | null, characteristic) => {
              if (monitorError || !characteristic?.value) return;
              const raw = base64.decode(characteristic.value);

              // 0. Pad Hardware Events
              if (raw.startsWith('EVT:CLEAR')) {
                set({ strokes: [], currentStroke: null });
                return;
              }
              if (raw.startsWith('EVT:MODE:')) {
                const code = parseInt(raw.slice(9), 10);
                if (code === 0) set({ testMode: 'free', strokes: [], currentStroke: null });
                else if (code === 1) set({ testMode: 'alphabet', alphabetSet: 'upper', strokes: [], currentStroke: null });
                else if (code === 2) set({ testMode: 'alphabet', alphabetSet: 'lower', strokes: [], currentStroke: null });
                else if (code === 3) set({ testMode: 'alphabet', alphabetSet: 'neuro', strokes: [], currentStroke: null });
                return;
              }
              if (raw.startsWith('EVT:THEME:')) {
                const isLight = raw.includes('LIGHT');
                const themeMode = isLight ? 'light' : 'dark';
                try {
                  const { useThemeStore } = require('./useThemeStore');
                  const { DarkColors, LightColors } = require('../theme/colors');
                  useThemeStore.setState({
                    theme: themeMode,
                    colors: isLight ? LightColors : DarkColors,
                  });
                } catch (e) {
                  console.warn('Could not sync theme from hardware event', e);
                }
                return;
              }

              // 1. Pad Touch Packet: X:(\d+),Y:(\d+)...
              if (raw.charCodeAt(0) === 88 /* 'X' */) {
                const parts = raw.split(',');
                if (parts.length >= 2) {
                  const x = parseInt(parts[0].slice(2), 10) || 0;
                  const y = parseInt(parts[1].slice(2), 10) || 0;
                  const isDown = x > 0 && y > 0;
                  const curP = get().pressure;

                  set((state) => {
                    let updatedCurrent = state.currentStroke;
                    let updatedStrokes = state.strokes;

                    if (isDown) {
                      // Filter micro-jitter (<2px distance from last point)
                      if (updatedCurrent && updatedCurrent.length > 0) {
                        const lastPt = updatedCurrent[updatedCurrent.length - 1];
                        if (Math.abs(lastPt.x - x) < 2 && Math.abs(lastPt.y - y) < 2) {
                          return state;
                        }
                      }
                      const pt: Point = { x, y, pressure: curP };
                      updatedCurrent = updatedCurrent ? [...updatedCurrent, pt] : [pt];
                    } else if (updatedCurrent && updatedCurrent.length > 0) {
                      updatedStrokes = [...updatedStrokes, updatedCurrent];
                      updatedCurrent = null;
                    } else if (!state.isTouched) {
                      return state;
                    }

                    return {
                      touchX: x,
                      touchY: y,
                      isTouched: isDown,
                      currentStroke: updatedCurrent,
                      strokes: updatedStrokes
                    };
                  });
                }
              }
            }
          );

          // Stop scanning if both devices connected
          if (get().penStatus === 'Connected') {
            try {
              bleManager.stopDeviceScan();
              isScanningActive = false;
            } catch (e) {}
          }
        } catch (padErr) {
          console.warn('[BLE] Could not connect to Writing Pad:', padErr);
          set({ padStatus: 'Disconnected', padDevice: null });
        }
      }
    });
  }
}));
