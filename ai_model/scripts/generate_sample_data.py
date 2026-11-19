"""
Benchmark Data Generator for PaHaW & NewHandPD Kinematic Formats.
Creates representative online handwriting & drawing trials for Parkinson's Disease (PD)
and Healthy Controls (HC), including tremors, micrographia decay, and in-air hesitations.
"""

import os
import numpy as np
import pandas as pd

def generate_spiral(is_pd=False, duration=15.0, fs=100.0):
    t = np.linspace(0, duration, int(duration * fs))
    dt = 1.0 / fs
    
    # Base spiral trajectory: Archimedean spiral
    theta = 2 * np.pi * 3.5 * (t / duration)
    
    if is_pd:
        # Micrographia: radius decays over time
        decay = np.maximum(0.3, 1.0 - 0.4 * (t / duration))
        r = 50.0 * (theta / (2 * np.pi * 3.5)) * decay
        
        # Action tremor (4-7 Hz)
        tremor_freq = np.random.uniform(4.5, 6.5)
        tremor_x = np.sin(2 * np.pi * tremor_freq * t) * np.random.uniform(1.5, 3.5)
        tremor_y = np.cos(2 * np.pi * tremor_freq * t) * np.random.uniform(1.5, 3.5)
        
        # Pressure dynamics: lower and more irregular
        base_p = 500.0 + np.random.normal(0, 80, len(t))
        # Pen-up / hesitations
        hesitation_mask = (np.sin(t * 1.5) > 0.75)
        pressure = np.where(hesitation_mask, 0.0, np.clip(base_p, 0, 1024))
    else:
        # Smooth consistent trajectory
        r = 50.0 * (theta / (2 * np.pi * 3.5))
        tremor_x = np.random.normal(0, 0.15, len(t))
        tremor_y = np.random.normal(0, 0.15, len(t))
        pressure = np.clip(750.0 + np.random.normal(0, 30, len(t)), 200, 1024)
        # Healthy controls have almost no random pen-lifts during continuous spiral
        pressure[0] = 0.0

    x = 100.0 + r * np.cos(theta) + tremor_x
    y = 100.0 + r * np.sin(theta) + tremor_y
    timestamp = (t * 1000).astype(int)  # ms
    
    return pd.DataFrame({
        "timestamp": timestamp,
        "x": x,
        "y": y,
        "pressure": pressure,
        "azimuth": np.random.uniform(0, 360, len(t)),
        "altitude": np.random.uniform(30, 80, len(t))
    })

def generate_meander(is_pd=False, duration=12.0, fs=100.0):
    t = np.linspace(0, duration, int(duration * fs))
    
    # Meander is sinusoidal wave along X axis
    x_base = np.linspace(20, 250, len(t))
    
    if is_pd:
        # Micrographia: amplitude shrinks across peaks
        amp_decay = np.linspace(40.0, 15.0, len(t))
        y_base = 100.0 + amp_decay * np.sin(2 * np.pi * 1.2 * t)
        
        # Tremor
        tremor = np.sin(2 * np.pi * 5.0 * t) * 2.0
        x = x_base + tremor
        y = y_base + tremor
        
        # Pressure & hesitation
        base_p = 450.0 + np.random.normal(0, 70, len(t))
        hesitation = (np.sin(t * 2.0) > 0.8)
        pressure = np.where(hesitation, 0.0, np.clip(base_p, 0, 1024))
    else:
        y_base = 100.0 + 40.0 * np.sin(2 * np.pi * 1.2 * t)
        x = x_base + np.random.normal(0, 0.1, len(t))
        y = y_base + np.random.normal(0, 0.1, len(t))
        pressure = np.clip(780.0 + np.random.normal(0, 25, len(t)), 250, 1024)

    timestamp = (t * 1000).astype(int)
    return pd.DataFrame({
        "timestamp": timestamp,
        "x": x,
        "y": y,
        "pressure": pressure,
        "azimuth": np.random.uniform(0, 360, len(t)),
        "altitude": np.random.uniform(30, 80, len(t))
    })

def populate_benchmark_data(base_dir="/home/sunraku/parkinsons_project/raw_data"):
    pahaw_dir = os.path.join(base_dir, "pahaw")
    nhpd_dir = os.path.join(base_dir, "newhandpd")
    os.makedirs(pahaw_dir, exist_ok=True)
    os.makedirs(nhpd_dir, exist_ok=True)
    
    # Generate PaHaW subjects (30 Patients, 20 Controls)
    print("Populating PaHaW benchmark trials...")
    for i in range(1, 31):
        subj = f"P_{i:03d}"
        df_sp = generate_spiral(is_pd=True)
        df_mn = generate_meander(is_pd=True)
        df_sp.to_csv(os.path.join(pahaw_dir, f"{subj}_spiral.csv"), index=False)
        df_mn.to_csv(os.path.join(pahaw_dir, f"{subj}_meander.csv"), index=False)
        
    for i in range(1, 21):
        subj = f"C_{i:03d}"
        df_sp = generate_spiral(is_pd=False)
        df_mn = generate_meander(is_pd=False)
        df_sp.to_csv(os.path.join(pahaw_dir, f"{subj}_spiral.csv"), index=False)
        df_mn.to_csv(os.path.join(pahaw_dir, f"{subj}_meander.csv"), index=False)
        
    # Generate NewHandPD subjects (20 Patients, 20 Controls)
    print("Populating NewHandPD benchmark trials...")
    for i in range(1, 21):
        subj = f"patient_{i:02d}"
        df_sp = generate_spiral(is_pd=True)
        df_mn = generate_meander(is_pd=True)
        df_sp.to_csv(os.path.join(nhpd_dir, f"{subj}_spiral.csv"), index=False)
        df_mn.to_csv(os.path.join(nhpd_dir, f"{subj}_meander.csv"), index=False)
        
    for i in range(1, 21):
        subj = f"control_{i:02d}"
        df_sp = generate_spiral(is_pd=False)
        df_mn = generate_meander(is_pd=False)
        df_sp.to_csv(os.path.join(nhpd_dir, f"{subj}_spiral.csv"), index=False)
        df_mn.to_csv(os.path.join(nhpd_dir, f"{subj}_meander.csv"), index=False)
        
    print(f"Data ready: {len(os.listdir(pahaw_dir))} PaHaW files, {len(os.listdir(nhpd_dir))} NewHandPD files.")

if __name__ == "__main__":
    populate_benchmark_data()
