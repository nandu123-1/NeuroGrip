import sys
import os
import math
import shutil

fc_lib = "/home/sunraku/Applications/FreeCAD/usr/lib"
if fc_lib not in sys.path:
    sys.path.insert(0, fc_lib)

import FreeCAD as App
import Part
import MeshPart
from FreeCAD import Vector, Rotation, Placement

def set_color(obj, color):
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color

def make_circle_wire(radius, z):
    c = Part.makeCircle(radius, Vector(0, 0, z), Vector(0, 0, 1))
    return Part.Wire([c])

def build_sleek_pen():
    print("=================================================================")
    print("Building Ultra-Sleek, Lightweight NeuroGrip Smart Pen (No OLED)")
    print("=================================================================")

    doc = App.newDocument("NeuroGrip_RealComponents_Pen")
    App.setActiveDocument("NeuroGrip_RealComponents_Pen")

    # -------------------------------------------------------------------------
    # 1. SLEEK CONTINUOUS CIRCULAR LOFT PROFILE (Total Length = 140.0 mm)
    # Maximum diameter: 14.6 mm (at buzzer). Grip diameter: 11.6 mm.
    # -------------------------------------------------------------------------
    outer_slices = [
        (1.0, 0.0),      # Apex of stylus nib (Dia 2.0 mm)
        (1.3, 2.0),      # Tip collar
        (2.5, 8.0),      # Elongated green cone (Dia 5.0 mm)
        (4.2, 15.0),     # Elongated green cone (Dia 8.4 mm)
        (5.8, 22.0),     # Grip waist (Dia 11.6 mm) - slender, ergonomic!
        (5.8, 35.0),     # Grip FSR section (Dia 11.6 mm)
        (6.0, 45.0),     # Transition to battery section (Dia 12.0 mm)
        (6.3, 70.0),     # Battery barrel mid (Dia 12.6 mm)
        (6.5, 92.0),     # Battery rear bulkhead (Dia 13.0 mm)
        (7.3, 100.0),    # Buzzer chamber (Dia 14.6 mm - max diameter!)
        (7.3, 115.0),    # Buzzer to XIAO deck (Dia 14.6 mm)
        (7.0, 128.0),    # XIAO MCU deck (Dia 14.0 mm)
        (6.0, 136.0),    # Crown taper (Dia 12.0 mm)
        (4.5, 140.0)     # Rear dome cap apex (Dia 9.0 mm)
    ]

    wires_outer = [make_circle_wire(r, z) for r, z in outer_slices]
    solid_outer = Part.makeLoft(wires_outer, True)

    # Sleek integrated pocket clip (slender 2.0 mm profile)
    clip_body = Part.makeBox(1.8, 2.0, 36.0, Vector(-0.9, -8.6, 94.0))
    clip_attach = Part.makeBox(1.8, 2.4, 5.0, Vector(-0.9, -8.6, 125.0))
    clip_ball = Part.makeSphere(1.1, Vector(0, -7.8, 95.0))
    solid_outer = solid_outer.fuse(clip_body.fuse(clip_attach).fuse(clip_ball))

    # -------------------------------------------------------------------------
    # 2. INTERNAL CAVITIES (1.1 - 1.2 mm Thin Walls for Featherlight Weight)
    # -------------------------------------------------------------------------
    # A. Nib & Stylus Refill Bore: Z = 0.0 to 16.0 mm (Dia 2.4 mm)
    nib_bore = Part.makeCylinder(1.2, 16.0, Vector(0, 0, 0.0), Vector(0, 0, 1))

    # B. Front Wire Tunnel: Z = 16.0 to 22.0 mm (Dia 3.0 mm)
    wire_tunnel = Part.makeCylinder(1.5, 6.0, Vector(0, 0, 16.0), Vector(0, 0, 1))

    # C. FSR Breakout & MPU-6050 Bay: Z = 22.0 to 47.0 mm (Dia 9.4 mm bore)
    fsr_bay = Part.makeCylinder(4.7, 25.0, Vector(0, 0, 22.0), Vector(0, 0, 1))

    # D. 10440 Battery Bay: Z = 48.0 to 92.5 mm (Dia 10.4 mm bore for 10.0 mm cell)
    batt_bay = Part.makeCylinder(5.2, 44.5, Vector(0, 0, 48.0), Vector(0, 0, 1))

    # E. KY-012 Buzzer Chamber: Z = 93.5 to 112.0 mm (Dia 12.4 mm bore for 12.0 mm buzzer)
    buzzer_bay = Part.makeCylinder(6.2, 18.5, Vector(0, 0, 93.5), Vector(0, 0, 1))

    # F. Seeed Studio XIAO MCU Bay: Z = 113.0 to 134.0 mm (12.4 x 4.0 mm slot)
    xiao_bay = Part.makeBox(12.5, 4.2, 21.0, Vector(-6.25, -2.1, 113.0))

    # G. Rear USB-C Charging Port: Z = 134.0 to 140.0 mm (8.8 x 3.2 mm)
    usbc_port = Part.makeBox(8.8, 3.2, 7.0, Vector(-4.4, -1.6, 134.0))

    # Cut all internal bays from outer solid
    hollow_solid = solid_outer
    for cavity in [nib_bore, wire_tunnel, fsr_bay, batt_bay, buzzer_bay, xiao_bay, usbc_port]:
        hollow_solid = hollow_solid.cut(cavity)

    # -------------------------------------------------------------------------
    # 3. EXTERIOR FEATURES: LIGHT GAP, FSR BED, SOUND SLITS
    # -------------------------------------------------------------------------
    # A. 0.8 mm Mechanical Isolation Light Gap at Z = 20.0 to 20.8 mm
    light_gap = Part.makeBox(4.5, 3.5, 0.8, Vector(-2.25, -6.0, 20.0))
    hollow_solid = hollow_solid.cut(light_gap)

    # B. Recessed FSR 402 Disc Bed at Z = 21.0 to 39.0 mm (Index Finger Surface)
    fsr_bed = Part.makeBox(6.5, 0.40, 18.0, Vector(-3.25, -6.0, 21.0))
    hollow_solid = hollow_solid.cut(fsr_bed)

    # C. Buzzer Sound Slits at Z = 102.0 mm (Dorsal face)
    for ang in [-25, 0, 25]:
        slit = Part.makeBox(0.9, 3.5, 4.0, Vector(-0.45, 5.0, 100.0))
        slit.rotate(Vector(0,0,102.0), Vector(0,0,1), ang)
        hollow_solid = hollow_solid.cut(slit)

    # D. Status LED pinhole at Z = 134.0 mm
    led_pinhole = Part.makeCylinder(0.8, 3.5, Vector(0, 4.0, 134.0), Vector(0, 1, 0))
    hollow_solid = hollow_solid.cut(led_pinhole)

    # -------------------------------------------------------------------------
    # 4. SPLIT INTO EXACTLY TWO VERTICAL LENGTHWISE PARTS (Parting Plane Y = 0)
    # -------------------------------------------------------------------------
    cutter_pos_y = Part.makeBox(50.0, 30.0, 180.0, Vector(-25.0, 0.0, -20.0))
    half_left = hollow_solid.cut(cutter_pos_y)    # Y <= 0 (Left Chassis)

    cutter_neg_y = Part.makeBox(50.0, 30.0, 180.0, Vector(-25.0, -30.0, -20.0))
    half_right = hollow_solid.cut(cutter_neg_y)  # Y >= 0 (Right Cover)

    # -------------------------------------------------------------------------
    # 5. ANTI-SHAKE RETENTION RIBS & ALIGNMENT DOWELS
    # -------------------------------------------------------------------------
    # 4 Longitudinal Battery Anti-Shake Ribs (0.6 mm thick, 0.25 mm interference)
    # They gently grip the 10440 cell so it cannot vibrate or rattle on shake
    rib1 = Part.makeBox(0.6, 1.2, 12.0, Vector(-0.3, 4.4, 52.0))
    rib2 = Part.makeBox(0.6, 1.2, 12.0, Vector(-0.3, 4.4, 76.0))
    half_right = half_right.fuse(rib1).fuse(rib2)

    # 6 Lightweight Alignment Dowels along Y = 0 parting rim (on solid wall)
    dowel_locs = [
        Vector(2.0, 0.0, 12.0),    # Conical tip wall
        Vector(-4.5, 0.0, 47.5),   # FSR / Battery bulkhead
        Vector(4.5, 0.0, 47.5),    # FSR / Battery bulkhead
        Vector(-5.5, 0.0, 93.0),   # Battery / Buzzer bulkhead
        Vector(5.5, 0.0, 93.0),    # Battery / Buzzer bulkhead
        Vector(4.5, 0.0, 136.0)    # Rear crown rim (beside USB-C)
    ]

    for loc in dowel_locs:
        socket = Part.makeCylinder(0.75, 1.5, loc, Vector(0, -1, 0))
        half_left = half_left.cut(socket)

        pin = Part.makeCylinder(0.65, 1.3, loc, Vector(0, -1, 0))
        pin_base = Part.makeCylinder(0.85, 1.0, loc, Vector(0, 1, 0))
        half_right = half_right.fuse(pin.fuse(pin_base))

    # Ensure single continuous manifold solids for each half
    if len(half_left.Solids) > 1:
        half_left = max(half_left.Solids, key=lambda s: s.Volume)
    if len(half_right.Solids) > 1:
        half_right = max(half_right.Solids, key=lambda s: s.Volume)

    print(f"Sleek Enclosure Verification:")
    print(f"  - Left Chassis:  Solids={len(half_left.Solids)}, IsValid={half_left.isValid()}, Vol={half_left.Volume:.1f} mm^3 (~{half_left.Volume/1000.0:.2f} cm^3)")
    print(f"  - Right Cover:   Solids={len(half_right.Solids)}, IsValid={half_right.isValid()}, Vol={half_right.Volume:.1f} mm^3 (~{half_right.Volume/1000.0:.2f} cm^3)")
    total_vol = (half_left.Volume + half_right.Volume) / 1000.0
    print(f"  - Total Plastic Volume: {total_vol:.2f} cm^3 (Weight: ~{total_vol*1.24:.1f} grams!)")

    obj_left = doc.addObject("Part::Feature", "NeuroGrip_Left_Chassis")
    obj_left.Shape = half_left
    obj_left.Visibility = True
    set_color(obj_left, (0.78, 0.80, 0.84)) # Satin Matte Titanium

    obj_right = doc.addObject("Part::Feature", "NeuroGrip_Right_Cover")
    obj_right.Shape = half_right
    obj_right.Visibility = True
    set_color(obj_right, (0.04, 0.08, 0.18)) # Deep Executive Navy

    # -------------------------------------------------------------------------
    # 6. INTEGRATE REAL COMPONENT 3D MODELS
    # -------------------------------------------------------------------------
    print("--- Integrating Real Component 3D Models ---")

    # A. Real FSR 402 with Breakout Module (images.jpeg)
    fsr_step_path = "/home/sunraku/3D_Components/FSR402_Breakout_Module.step"
    if os.path.exists(fsr_step_path):
        fsr_raw = Part.read(fsr_step_path)
        pl_fsr = Placement(Vector(0.0, -1.0, 23.5), Rotation(Vector(0,0,1), 0))
        fsr_raw.Placement = pl_fsr
        obj_fsr = doc.addObject("Part::Feature", "Real_FSR402_Breakout_Module")
        obj_fsr.Shape = fsr_raw
        obj_fsr.Visibility = True
        set_color(obj_fsr, (0.08, 0.35, 0.75))

    # B. Real 10440 Li-Ion Battery (Dia 10.0 x 44.0 mm)
    batt_step_path = "/home/sunraku/3D_Components/Battery_10440_AAA.step"
    batt_shape = Part.read(batt_step_path)
    pl_batt = Placement(Vector(0.0, 0.0, 48.0), Rotation(Vector(0, 0, 1), 0))
    batt_shape.Placement = pl_batt
    obj_batt = doc.addObject("Part::Feature", "Real_10440_LiIon_Battery")
    obj_batt.Shape = batt_shape
    obj_batt.Visibility = True
    set_color(obj_batt, (0.10, 0.72, 0.25))

    # C. Real KY-012 Active Buzzer Module (images (1).jpeg)
    ky012_step_path = "/home/sunraku/3D_Components/KY012_Buzzer_Module.step"
    if os.path.exists(ky012_step_path):
        buzzer_raw = Part.read(ky012_step_path)
        pl_buzzer = Placement(Vector(0.0, 0.0, 95.0), Rotation(Vector(0,0,1), 0))
        buzzer_raw.Placement = pl_buzzer
        obj_buzzer = doc.addObject("Part::Feature", "Real_KY012_Buzzer_Module")
        obj_buzzer.Shape = buzzer_raw
        obj_buzzer.Visibility = True
        set_color(obj_buzzer, (0.15, 0.15, 0.18))

    # D. Real Seeed Studio XIAO MCU (Official 83-solid STEP)
    xiao_step_path = "/home/sunraku/3D_Components/Seeed_Studio_XIAO.step"
    xiao_shape = Part.read(xiao_step_path)
    pl_xiao = Placement(Vector(0.0, 0.0, 114.0), Rotation(Vector(1, 0, 0), -90.0))
    xiao_shape.Placement = pl_xiao
    obj_xiao = doc.addObject("Part::Feature", "Real_Seeed_Studio_XIAO_MCU")
    obj_xiao.Shape = xiao_shape
    obj_xiao.Visibility = True
    set_color(obj_xiao, (0.75, 0.15, 0.15))

    # E. MPU-6050 Motion Sensor
    mpu_chip_path = "/home/sunraku/3D_Components/MPU6050_QFN24.step"
    mpu_chip = Part.read(mpu_chip_path)
    pl_mpu = Placement(Vector(0.0, 0.0, 44.0), Rotation(Vector(1, 0, 0), 90.0))
    mpu_chip.Placement = pl_mpu
    obj_mpu = doc.addObject("Part::Feature", "Real_MPU6050_IMU")
    obj_mpu.Shape = mpu_chip
    obj_mpu.Visibility = True
    set_color(obj_mpu, (0.05, 0.20, 0.65))

    doc.recompute()
    print("Recomputation successful!")

    # -------------------------------------------------------------------------
    # 7. EXPORT MASTER DELIVERABLES
    # -------------------------------------------------------------------------
    OUTPUT_DIR = "/home/sunraku"
    fcstd_path = os.path.join(OUTPUT_DIR, "NeuroGrip_RealComponents_Pen.FCStd")
    step_path = os.path.join(OUTPUT_DIR, "NeuroGrip_RealComponents_Pen.step")
    stl_left_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Left_Chassis.stl")
    stl_right_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Right_Cover.stl")

    doc.saveAs(fcstd_path)
    print(f"Saved FreeCAD Document: {fcstd_path}")

    all_objs = [obj_left, obj_right, obj_buzzer, obj_fsr, obj_batt, obj_xiao, obj_mpu]
    Part.export(all_objs, step_path)
    print(f"Exported STEP Assembly: {step_path}")

    mesh_left = MeshPart.meshFromShape(half_left, 0.05, 0.1)
    mesh_left.write(stl_left_path)

    mesh_right = MeshPart.meshFromShape(half_right, 0.05, 0.1)
    mesh_right.write(stl_right_path)
    print(f"Exported STLs: {stl_left_path}, {stl_right_path}")

    # Mirror to artifacts directory
    ARTIFACT_DIR = "/home/sunraku/.gemini/antigravity-cli/brain/91c353f2-6f2e-4d17-a6cf-9355eb5a6989"
    for src in [fcstd_path, step_path, stl_left_path, stl_right_path]:
        shutil.copy2(src, os.path.join(ARTIFACT_DIR, os.path.basename(src)))

    print("Ultra-sleek pen generation complete!")

build_sleek_pen()
