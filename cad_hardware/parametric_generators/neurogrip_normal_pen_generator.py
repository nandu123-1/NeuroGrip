import sys
import os
import math
import shutil

fc_lib = "/home/sunraku/Applications/FreeCAD/usr/lib"
if fc_lib not in sys.path:
    sys.path.insert(0, fc_lib)

try:
    import FreeCAD as App
    import Part
    from FreeCAD import Vector, Rotation, Placement
except ImportError as e:
    print(f"Error importing FreeCAD: {e}")
    sys.exit(1)

def set_color(obj, color):
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color

def build_normal_proportions_pen():
    doc = App.newDocument("NeuroGrip_Normal_Pen")
    App.setActiveDocument("NeuroGrip_Normal_Pen")
    print("Created FreeCAD Document: NeuroGrip_Normal_Pen")

    # =========================================================================
    # PARAMETRIC ARCHITECTURE: EXECUTIVE NORMAL PROPORTIONS TWO-PART PEN
    # Total Length: 140.0 mm (Standard normal pen length - Lamy / Parker / Pilot)
    # Grip Diameter: 12.6 mm (Slim, ergonomic, comfortable)
    # Mid-Barrel Diameter: 13.4 mm (Minimal wall enclosing 10.0mm 10440 battery)
    # Rear Section Diameter: 18.6 mm (Smooth gradual contour over 17.5mm XIAO board)
    # FSR 402 Light Gap Slot: Z = 5.8 to 6.6 mm (Immediate proximity to stylus tip)
    # Part 1: Front Grip Section (Z = 0 to 45.0 mm, tenon Z = 37 to 45 mm)
    # Part 2: Rear Barrel Enclosure (Z = 37 to 140.0 mm)
    # =========================================================================

    # -------------------------------------------------------------------------
    # PART 1: FRONT GRIP SECTION (Pen_Front_Grip)
    # -------------------------------------------------------------------------
    print("--- 1. Generating Part 1: Front Grip Section with FSR 402 Light Gap ---")
    
    pts_grip = [
        Vector(0.0, 0, 0.0),       # Stylus tip apex
        Vector(0.8, 0, 0.5),       # Stylus ball
        Vector(1.4, 0, 2.0),       # Stylus collar
        Vector(2.8, 0, 4.5),       # Slender nib cone
        Vector(4.8, 0, 6.5),       # Transition flare
        Vector(6.3, 0, 8.5),       # Grip diameter starts (OD = 12.6 mm)
        Vector(6.3, 0, 26.0),      # Ergonomic finger grip waist (OD = 12.6 mm, FSR 402 zone)
        Vector(6.6, 0, 32.0),      # Subtle flare
        Vector(6.7, 0, 37.0),      # Shoulder seam (OD = 13.4 mm)
        Vector(5.5, 0, 37.0),      # Step to tenon (OD = 11.0 mm, 0.2mm slip fit into 11.4mm socket)
        Vector(5.5, 0, 45.0),      # Tenon top
        Vector(0.0, 0, 45.0),      # Centerline top
        Vector(0.0, 0, 0.0)        # Close
    ]

    wire_grip = Part.makePolygon(pts_grip)
    face_grip = Part.Face(wire_grip)
    solid_grip_outer = face_grip.revolve(Vector(0,0,0), Vector(0,0,1), 360.0)

    # Front internal bore: starts at Z=9.0 mm to Z=46.0 mm
    # Radius 5.35 mm (ID = 10.7 mm, wall = 6.3 - 5.35 = 0.95 mm)
    # Holds MPU-6050 (10.5 x 2.2 x 20.0 mm at Z=9.0..29.0 mm)
    front_bore = Part.makeCylinder(5.35, 37.0, Vector(0, 0, 9.0), Vector(0, 0, 1))
    front_body = solid_grip_outer.cut(front_bore)

    # Flush FSR 402 bed on grip waist: Z = 6.5 to 24.5 mm (18 mm long, 8.0 mm wide)
    # Recess depth 0.45 mm into outer radius 6.3 mm (cut from Y = 5.85 to 6.4 mm)
    fsr_bed = Part.makeBox(8.0, 0.55, 18.0, Vector(-4.0, 5.85, 6.5))
    front_body = front_body.cut(fsr_bed)

    # "LIGHT GAP" NEAR THE TIP OF PEN FOR FSR 402:
    # Precision 0.8 mm x 6.0 mm transverse slot right near the tip (Z = 5.8 to 6.6 mm)
    # Functions:
    # 1. Flex relief gap so the FSR sensor head deflects freely without binding
    # 2. Pass-through slot for sensor tail wiring directly into internal bore
    light_gap_slot = Part.makeBox(6.0, 2.5, 0.8, Vector(-3.0, 4.5, 5.8))
    front_body = front_body.cut(light_gap_slot)

    # Snap ridge on tenon: torus minor radius 0.20 mm at Z=41.0 mm
    snap_ridge = Part.makeTorus(5.5, 0.20, Vector(0, 0, 41.0), Vector(0, 0, 1))
    front_body = front_body.fuse(snap_ridge)

    # -------------------------------------------------------------------------
    # PART 2: REAR BARREL SECTION (Pen_Rear_Barrel)
    # -------------------------------------------------------------------------
    print("--- 2. Generating Part 2: Rear Barrel Enclosure (Normal Pen Body) ---")
    
    pts_barrel = [
        Vector(0.0, 0, 37.0),
        Vector(6.7, 0, 37.0),      # Mating shoulder (OD = 13.4 mm)
        Vector(6.7, 0, 80.0),      # Mid barrel (OD = 13.4 mm, wall 1.2 mm over 11.0 mm battery bore)
        Vector(7.2, 0, 92.0),      # Very gradual ergonomic taper starts
        Vector(8.2, 0, 100.0),     # Smooth contour
        Vector(9.3, 0, 105.0),     # Reaches MCU section (OD = 18.6 mm)
        Vector(9.3, 0, 128.0),     # Upper barrel (OD = 18.6 mm)
        Vector(8.4, 0, 135.0),     # Crown taper
        Vector(6.2, 0, 140.0),     # Rear dome cap top
        Vector(0.0, 0, 140.0),     # Centerline
        Vector(0.0, 0, 37.0)       # Close
    ]

    wire_barrel = Part.makePolygon(pts_barrel)
    face_barrel = Part.Face(wire_barrel)
    solid_barrel_outer = face_barrel.revolve(Vector(0,0,0), Vector(0,0,1), 360.0)

    # Internal Bores in Rear Barrel:
    # A. Tenon receiver socket: Z=37.0 to 45.0 mm, radius 5.7 mm (ID = 11.4 mm, 0.2mm slip fit)
    tenon_socket = Part.makeCylinder(5.7, 8.0, Vector(0, 0, 37.0), Vector(0, 0, 1))
    rear_body = solid_barrel_outer.cut(tenon_socket)

    # Snap groove inside tenon socket: minor radius 0.22 mm at Z=41.0 mm
    snap_groove = Part.makeTorus(5.7, 0.22, Vector(0, 0, 41.0), Vector(0, 0, 1))
    rear_body = rear_body.cut(snap_groove)

    # B. Battery Bore: Z=45.0 to 92.0 mm, radius 5.5 mm (clears 10.0mm 10440 battery)
    batt_bore = Part.makeCylinder(5.5, 47.0, Vector(0, 0, 45.0), Vector(0, 0, 1))
    rear_body = rear_body.cut(batt_bore)

    # C. Buzzer Chamber: Z=92.0 to 97.0 mm, radius 5.0 mm (clears 9.0mm buzzer)
    buzzer_bore = Part.makeCylinder(5.0, 5.0, Vector(0, 0, 92.0), Vector(0, 0, 1))
    rear_body = rear_body.cut(buzzer_bore)

    # D. XIAO Board Cavity: Z=104.0 to 127.0 mm, radius 8.8 mm (clears 17.5mm board)
    xiao_bore = Part.makeCylinder(8.8, 23.0, Vector(0, 0, 104.0), Vector(0, 0, 1))
    rear_body = rear_body.cut(xiao_bore)

    # Wire tunnel between buzzer and XIAO
    wire_tunnel = Part.makeCylinder(3.5, 7.0, Vector(0, 0, 97.0), Vector(0, 0, 1))
    rear_body = rear_body.cut(wire_tunnel)

    # E. USB-C Port Cutout: Z=126.0 to 141.0 mm (9.2 x 3.4 mm)
    usbc_port = Part.makeBox(9.2, 3.4, 15.0, Vector(-4.6, -1.7, 126.0))
    rear_body = rear_body.cut(usbc_port)

    # F. Acoustic micro-slits for buzzer at Z=94.5 mm
    for ang in [0, 90, 180, 270]:
        slit = Part.makeBox(0.8, 2.5, 1.4, Vector(-0.4, 5.5, 93.8))
        slit.rotate(Vector(0,0,94.5), Vector(0,0,1), ang)
        rear_body = rear_body.cut(slit)

    # G. Optical LED pinhole at Z=134.0 mm
    led_hole = Part.makeCylinder(0.55, 4.0, Vector(0, 7.0, 134.0), Vector(0, 1, 0))
    rear_body = rear_body.cut(led_hole)

    # H. Classic Architectural Spring Pocket Clip (proportional 38mm length)
    clip_body = Part.makeBox(2.6, 2.6, 38.0, Vector(-1.2, -11.2, 92.0))
    clip_attach = Part.makeBox(2.6, 3.2, 5.0, Vector(-1.2, -11.2, 125.0))
    clip_ball = Part.makeSphere(1.4, Vector(0, -10.3, 93.5))
    clip_complete = clip_body.fuse(clip_attach).fuse(clip_ball)
    rear_body = rear_body.fuse(clip_complete)

    # -------------------------------------------------------------------------
    # 3. ADD OBJECTS TO DOCUMENT
    # -------------------------------------------------------------------------
    obj_front = doc.addObject("Part::Feature", "NormalPen_Front_Grip_Section")
    obj_front.Shape = front_body
    set_color(obj_front, (0.78, 0.80, 0.84)) # Brushed Aerospace Titanium

    obj_rear = doc.addObject("Part::Feature", "NormalPen_Rear_Barrel_Section")
    obj_rear.Shape = rear_body
    set_color(obj_rear, (0.02, 0.05, 0.12)) # Executive Midnight Navy

    # -------------------------------------------------------------------------
    # 4. PRECISE INTERNAL COMPONENT MOCKUPS (REAL SIZES)
    # -------------------------------------------------------------------------
    print("--- 3. Modeling Snug Internal Components in Normal Proportions ---")
    
    # 1. Interlink FSR 402 Sensor (Flush bed Z=6.5..24.5 mm, light gap at Z=5.8..6.6 mm)
    mock_fsr = Part.makeBox(7.5, 0.45, 17.5, Vector(-3.75, 5.85, 6.7))
    obj_fsr = doc.addObject("Part::Feature", "Mockup_FSR402_Sensor")
    obj_fsr.Shape = mock_fsr
    set_color(obj_fsr, (0.95, 0.80, 0.15))

    # 2. MPU-6050 IMU Breakout (10.5 x 2.2 x 20.0 mm, seated at Z=9.0..29.0 mm)
    mock_imu = Part.makeBox(10.5, 2.2, 20.0, Vector(-5.25, -1.1, 9.0))
    obj_imu = doc.addObject("Part::Feature", "Mockup_MPU6050_IMU")
    obj_imu.Shape = mock_imu
    set_color(obj_imu, (0.10, 0.35, 0.85))

    # 3. 10440 Li-ion Battery Cell (Dia 10.0 x 44.0 mm, seated at Z=46.0..90.0 mm)
    mock_batt = Part.makeCylinder(5.0, 44.0, Vector(0, 0, 46.0), Vector(0, 0, 1))
    obj_batt = doc.addObject("Part::Feature", "Mockup_Battery_10440")
    obj_batt.Shape = mock_batt
    set_color(obj_batt, (0.15, 0.75, 0.35))

    # 4. Piezo Buzzer Transducer (Dia 9.0 x 3.5 mm, seated at Z=93.0..96.5 mm)
    mock_buzzer = Part.makeCylinder(4.5, 3.5, Vector(0, 0, 93.0), Vector(0, 0, 1))
    obj_buzzer = doc.addObject("Part::Feature", "Mockup_Buzzer")
    obj_buzzer.Shape = mock_buzzer
    set_color(obj_buzzer, (0.25, 0.25, 0.25))

    # 5. Seeed Studio XIAO nRF52840 MCU (17.5 x 3.5 x 21.0 mm, seated at Z=105.0..126.0 mm)
    mock_xiao = Part.makeBox(17.5, 3.5, 21.0, Vector(-8.75, -1.75, 105.0))
    obj_xiao = doc.addObject("Part::Feature", "Mockup_XIAO_nRF52840")
    obj_xiao.Shape = mock_xiao
    set_color(obj_xiao, (0.85, 0.15, 0.15))

    # 6. Status RGB LED Indicator (Dia 1.1 mm, seated at Z=134.0 mm)
    mock_led = Part.makeCylinder(0.50, 3.5, Vector(0, 5.5, 134.0), Vector(0, 1, 0))
    obj_led = doc.addObject("Part::Feature", "Mockup_RGB_LED")
    obj_led.Shape = mock_led
    set_color(obj_led, (0.0, 0.90, 1.0))

    doc.recompute()
    print("Recomputation successful!")

    # =========================================================================
    # EXPORTING ARTIFACTS: FCSTD, STEP, AND 3D-PRINTABLE STLS
    # =========================================================================
    OUTPUT_DIR = "/home/sunraku"
    fcstd_path = os.path.join(OUTPUT_DIR, "NeuroGrip_NormalPen_TwoPart.FCStd")
    step_path = os.path.join(OUTPUT_DIR, "NeuroGrip_NormalPen_TwoPart.step")
    stl_front_path = os.path.join(OUTPUT_DIR, "NeuroGrip_NormalPen_Front_Grip.stl")
    stl_rear_path = os.path.join(OUTPUT_DIR, "NeuroGrip_NormalPen_Rear_Barrel.stl")

    doc.saveAs(fcstd_path)
    print(f"Saved FreeCAD Document: {fcstd_path}")

    all_objs = [obj_front, obj_rear, obj_imu, obj_fsr, obj_batt, obj_buzzer, obj_xiao, obj_led]
    Part.export(all_objs, step_path)
    print(f"Exported STEP Assembly: {step_path}")

    Part.export([obj_front], stl_front_path)
    Part.export([obj_rear], stl_rear_path)
    print(f"Exported 3D Print STLs:\n  - {stl_front_path}\n  - {stl_rear_path}")

    # Copy to artifacts directory
    ARTIFACT_DIR = "/home/sunraku/.gemini/antigravity-cli/brain/91c353f2-6f2e-4d17-a6cf-9355eb5a6989"
    for src in [fcstd_path, step_path, stl_front_path, stl_rear_path]:
        shutil.copy2(src, os.path.join(ARTIFACT_DIR, os.path.basename(src)))

    print("Normal Proportions Pen Two-Part models and STLs generated successfully!")

if __name__ == "__main__":
    build_normal_proportions_pen()
    sys.exit(0)
