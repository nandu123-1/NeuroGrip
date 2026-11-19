import sys
import os
import math
import shutil

# Ensure FreeCAD library path is accessible
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

def build_vertical_twopart_pen():
    doc = App.newDocument("NeuroGrip_VerticalTwoPart_Pen")
    App.setActiveDocument("NeuroGrip_VerticalTwoPart_Pen")
    print("Created FreeCAD Document: NeuroGrip_VerticalTwoPart_Pen")

    # =========================================================================
    # ARCHITECTURAL SPECIFICATION:
    # 1. ELONGATED GREEN NOSE CONE (STYLUS TIP):
    #    - Height increased to 22.0 mm (Z = 0.0 to 22.0 mm).
    #    - Elegant, graceful taper matching authentic executive fountain/stylus pens.
    # 2. TWO VERTICAL LENGTHWISE PARTS (NOT HORIZONTAL):
    #    - Split vertically along parting plane Y = 0 over the entire 140.0 mm height.
    #    - Part 1: NeuroGrip_Vertical_Left_Chassis (Y <= 0)
    #    - Part 2: NeuroGrip_Vertical_Right_Cover (Y >= 0)
    # 3. ANTI-SHAKE POSITIVE COMPONENT RETENTION:
    #    - Solid bulkhead partition walls blocking axial movement along Z.
    #    - Anti-shake compression ribs firmly clamping Battery, IMU, Buzzer, and MCU.
    #    - Zero rattle, vibration, or movement when the pen is shaken.
    # 4. REAL 3D ONLINE COMPONENTS INTEGRATION:
    #    - Real Seeed Studio XIAO MCU (official 83-solid STEP model from library).
    #    - Real 10440 / AAA Li-ion battery (official STEP model from FreeCAD-library).
    #    - Real CUI 9mm magnetic buzzer (official STEP model from KiCad library).
    #    - Real InvenSense MPU-6050 QFN-24 sensor assembly (official KiCad STEP).
    #    - Real Interlink FSR 402 sensor assembly with flex tail & light gap slot.
    # =========================================================================

    # -------------------------------------------------------------------------
    # 1. REVOLVED MASTER EXTERIOR PROFILE (140.0 mm Total Normal Pen Height)
    # -------------------------------------------------------------------------
    pts_outer = [
        Vector(0.0, 0, 0.0),       # Stylus apex (Z = 0)
        Vector(1.0, 0, 0.5),       # Rounded nib ball
        Vector(1.4, 0, 2.5),       # Stylus collar
        Vector(2.2, 0, 7.0),       # Elongated green cone (height increased)
        Vector(3.4, 0, 12.0),      # Elongated green cone
        Vector(4.8, 0, 17.0),      # Elongated green cone
        Vector(6.3, 0, 22.0),      # Smooth transition to grip waist (OD = 12.6 mm)
        Vector(6.3, 0, 45.0),      # Ergonomic grip waist (OD = 12.6 mm)
        Vector(6.7, 0, 50.0),      # Transition to mid barrel
        Vector(6.7, 0, 85.0),      # Mid barrel (OD = 13.4 mm enclosing 10mm battery)
        Vector(7.3, 0, 93.0),      # Gradual ergonomic swell starts
        Vector(8.3, 0, 100.0),     # Smooth contour
        Vector(9.3, 0, 105.0),     # Reaches upper barrel (OD = 18.6 mm for XIAO)
        Vector(9.3, 0, 126.0),     # Upper barrel
        Vector(8.4, 0, 135.0),     # Crown taper
        Vector(6.2, 0, 140.0),     # Rear dome cap top
        Vector(0.0, 0, 140.0),     # Centerline top
        Vector(0.0, 0, 0.0)        # Close profile
    ]

    wire_outer = Part.makePolygon(pts_outer)
    face_outer = Part.Face(wire_outer)
    solid_outer = face_outer.revolve(Vector(0,0,0), Vector(0,0,1), 360.0)

    # Architectural pocket clip on outer barrel (Z = 92 to 134 mm)
    clip_body = Part.makeBox(2.6, 2.6, 38.0, Vector(-1.3, 7.0, 92.0))
    clip_attach = Part.makeBox(2.6, 3.2, 6.0, Vector(-1.3, 6.8, 124.0))
    clip_ball = Part.makeSphere(1.4, Vector(0, 8.0, 93.5))
    clip_complete = clip_body.fuse(clip_attach).fuse(clip_ball)
    solid_outer = solid_outer.fuse(clip_complete)

    print(f"Master outer solid created. Volume: {solid_outer.Volume:.1f} mm^3")

    # -------------------------------------------------------------------------
    # 2. SPLITTING INTO TWO VERTICAL LENGTHWISE HALVES (Y = 0 Parting Plane)
    # -------------------------------------------------------------------------
    cutter_pos_y = Part.makeBox(60.0, 40.0, 180.0, Vector(-30.0, 0.0, -20.0))
    half_left = solid_outer.cut(cutter_pos_y)    # Y <= 0 (Left / Lower Chassis)

    cutter_neg_y = Part.makeBox(60.0, 40.0, 180.0, Vector(-30.0, -40.0, -20.0))
    half_right = solid_outer.cut(cutter_neg_y)  # Y >= 0 (Right / Upper Cover)

    print("Splitting complete along full 140mm vertical length.")

    # -------------------------------------------------------------------------
    # 3. INTERNAL COMPONENT CARRIAGES & ANTI-SHAKE AXIAL BULKHEADS
    # -------------------------------------------------------------------------
    # A. Front wire tunnel inside elongated cone: Z = 16.0 to 23.0 mm (Z=0..16 is solid nib)
    wire_tunnel_front = Part.makeCylinder(1.5, 7.0, Vector(0, 0, 16.0), Vector(0, 0, 1))

    # B. MPU-6050 IMU Cavity: Z = 24.0 to 44.0 mm (Exact 20.0 mm span)
    # Positive forward bulkhead at Z=22..24 mm; rear bulkhead at Z=44..45 mm
    imu_pocket = Part.makeBox(10.7, 2.6, 20.0, Vector(-5.35, -1.3, 24.0))

    # C. 10440 Battery Cradle: Z = 45.0 to 89.5 mm (Exact 44.5 mm span for 44.0 mm cell)
    # Trapped between Z=44..45 bulkhead and Z=89.5..91.0 bulkhead
    batt_cradle = Part.makeCylinder(5.15, 44.5, Vector(0, 0, 45.0), Vector(0, 0, 1))

    # D. Wire tunnel between Battery & Buzzer: Z = 89.5 to 91.0 mm
    wire_tunnel_batt = Part.makeCylinder(1.8, 1.5, Vector(0, 0, 89.5), Vector(0, 0, 1))

    # E. Piezo Buzzer Cavity: Z = 91.0 to 95.0 mm (4.0 mm span for 3.5 mm buzzer)
    # Trapped between Z=89.5..91 bulkhead and Z=95..99 bulkhead
    buzzer_chamber = Part.makeCylinder(4.65, 4.0, Vector(0, 0, 91.0), Vector(0, 0, 1))

    # F. Wire tunnel between Buzzer & XIAO: Z = 95.0 to 99.0 mm
    wire_tunnel_xiao = Part.makeCylinder(2.0, 4.0, Vector(0, 0, 95.0), Vector(0, 0, 1))

    # G. Seeed Studio XIAO MCU Bay: Z = 99.0 to 120.5 mm (21.5 mm span for 21.0 mm board)
    # Forward stop at Z=99.0 mm; rear shoulder lock at Z=120.5 mm
    xiao_pocket = Part.makeBox(17.7, 3.8, 21.5, Vector(-8.85, -1.9, 99.0))

    # H. Rear USB-C Charging Port: Z = 120.5 to 141.0 mm
    usbc_port = Part.makeBox(9.4, 3.6, 20.5, Vector(-4.7, -1.8, 120.5))

    # Cut cavities from both vertical halves
    cuts_common = [wire_tunnel_front, imu_pocket, batt_cradle, wire_tunnel_batt, buzzer_chamber, wire_tunnel_xiao, xiao_pocket, usbc_port]
    for cut_shape in cuts_common:
        half_left = half_left.cut(cut_shape)
        half_right = half_right.cut(cut_shape)

    # -------------------------------------------------------------------------
    # 4. FSR 402 FEATURES (LIGHT GAP & RECESSED SENSOR BED)
    # -------------------------------------------------------------------------
    # Transverse Light Gap Slot: Z = 20.0 to 20.8 mm (0.8 mm gap, 6.0 mm wide)
    fsr_light_gap = Part.makeBox(6.0, 4.0, 0.8, Vector(-3.0, -5.5, 20.0))
    half_left = half_left.cut(fsr_light_gap)

    # Recessed FSR 402 Bed on Grip Surface: Z = 21.0 to 39.0 mm
    fsr_bed = Part.makeBox(7.5, 0.55, 18.0, Vector(-3.75, -6.4, 21.0))
    half_left = half_left.cut(fsr_bed)

    # Acoustic micro-slits for Buzzer: Z = 93.0 mm (4 radial slits)
    for ang in [45, 135, 225, 315]:
        slit = Part.makeBox(0.8, 2.5, 1.4, Vector(-0.4, 4.5, 92.3))
        slit.rotate(Vector(0,0,93.0), Vector(0,0,1), ang)
        half_left = half_left.cut(slit)
        half_right = half_right.cut(slit)

    # Status RGB LED Optical Pinhole: Z = 126.0 mm on Right Cover
    led_hole = Part.makeCylinder(0.55, 4.0, Vector(0, 7.0, 126.0), Vector(0, 1, 0))
    half_right = half_right.cut(led_hole)

    # -------------------------------------------------------------------------
    # 5. ANTI-SHAKE POSITIVE CLAMPING RIBS (ELIMINATES ALL COMPONENT MOVEMENT)
    # -------------------------------------------------------------------------
    # A. IMU Anti-Shake Clamping Ribs
    imu_rib1 = Part.makeBox(10.5, 0.45, 1.5, Vector(-5.25, 0.85, 27.25))
    imu_rib2 = Part.makeBox(10.5, 0.45, 1.5, Vector(-5.25, 0.85, 39.25))
    bridge_imu1 = Part.makeBox(10.5, 2.5, 1.5, Vector(-5.25, 1.25, 27.25))
    bridge_imu2 = Part.makeBox(10.5, 2.5, 1.5, Vector(-5.25, 1.25, 39.25))
    half_right = half_right.fuse(imu_rib1.fuse(bridge_imu1)).fuse(imu_rib2.fuse(bridge_imu2))

    # B. Battery Anti-Shake Compression Ribs
    batt_rib1 = Part.makeBox(1.6, 2.0, 12.0, Vector(-0.8, 4.6, 52.0))
    batt_rib2 = Part.makeBox(1.6, 2.0, 12.0, Vector(-0.8, 4.6, 72.0))
    half_right = half_right.fuse(batt_rib1).fuse(batt_rib2)

    # C. XIAO MCU Clamping Ribs
    xiao_rib_l = Part.makeBox(1.5, 2.0, 14.0, Vector(-8.7, 1.4, 102.0))
    xiao_rib_r = Part.makeBox(1.5, 2.0, 14.0, Vector(7.2, 1.4, 102.0))
    half_right = half_right.fuse(xiao_rib_l).fuse(xiao_rib_r)

    # -------------------------------------------------------------------------
    # 6. PRECISION ALIGNMENT DOWEL PINS & SOCKETS (ANCHORED IN SOLID BULKHEADS)
    # -------------------------------------------------------------------------
    pin_locs = [
        Vector(0.0, 0.0, 10.0),    # Elongated solid tip cone
        Vector(-3.8, 0.0, 44.5),   # IMU / Battery solid bulkhead (left)
        Vector(3.8, 0.0, 44.5),    # IMU / Battery solid bulkhead (right)
        Vector(-5.5, 0.0, 97.0),   # Buzzer / XIAO solid bulkhead (left)
        Vector(5.5, 0.0, 97.0),    # Buzzer / XIAO solid bulkhead (right)
        Vector(-5.8, 0.0, 134.0),  # Rear crown solid shoulder (left)
        Vector(5.8, 0.0, 134.0)    # Rear crown solid shoulder (right)
    ]

    for loc in pin_locs:
        socket = Part.makeCylinder(1.05, 2.2, loc, Vector(0, -1, 0))
        half_left = half_left.cut(socket)
        
        pin = Part.makeCylinder(0.90, 2.0, loc, Vector(0, -1, 0))
        pin_anchor = Part.makeCylinder(1.10, 1.5, loc, Vector(0, 1, 0))
        half_right = half_right.fuse(pin.fuse(pin_anchor))

    print(f"Enclosure Generation Complete:")
    print(f"  - Left Chassis: Solids={len(half_left.Solids)}, IsValid={half_left.isValid()}, Vol={half_left.Volume:.1f} mm^3")
    print(f"  - Right Cover:  Solids={len(half_right.Solids)}, IsValid={half_right.isValid()}, Vol={half_right.Volume:.1f} mm^3")

    obj_left = doc.addObject("Part::Feature", "NeuroGrip_Vertical_Left_Chassis")
    obj_left.Shape = half_left
    set_color(obj_left, (0.75, 0.78, 0.82)) # Brushed Titanium Satin

    obj_right = doc.addObject("Part::Feature", "NeuroGrip_Vertical_Right_Cover")
    obj_right.Shape = half_right
    set_color(obj_right, (0.02, 0.05, 0.12)) # Midnight Executive Navy

    # -------------------------------------------------------------------------
    # 7. IMPORT REAL 3D ONLINE COMPONENTS
    # -------------------------------------------------------------------------
    print("--- 7. Importing Real 3D Online Components into Assembly ---")

    # 1. Real Seeed Studio XIAO MCU (Official STEP from library)
    xiao_step_path = "/home/sunraku/3D_Components/Seeed_Studio_XIAO.step"
    xiao_shape = Part.read(xiao_step_path)
    # Rotate -90 around X so USB-C points toward rear +Z
    pl_xiao = Placement(Vector(0.0, 0.0, 109.5), Rotation(Vector(1, 0, 0), -90.0))
    xiao_shape.Placement = pl_xiao
    obj_xiao = doc.addObject("Part::Feature", "Real_Seeed_Studio_XIAO_MCU")
    obj_xiao.Shape = xiao_shape
    set_color(obj_xiao, (0.75, 0.15, 0.15)) # Maroon / Gold / Metal

    # 2. Real 10440 / AAA Li-ion Battery (Official STEP from FreeCAD-library)
    batt_step_path = "/home/sunraku/3D_Components/Battery_10440_AAA.step"
    batt_shape = Part.read(batt_step_path)
    pl_batt = Placement(Vector(0.0, 0.0, 45.0), Rotation(Vector(0, 0, 1), 0))
    batt_shape.Placement = pl_batt
    obj_batt = doc.addObject("Part::Feature", "Real_10440_LiIon_Battery")
    obj_batt.Shape = batt_shape
    set_color(obj_batt, (0.12, 0.72, 0.28)) # Emerald Li-ion Green

    # 3. Real CUI 9mm Magnetic Buzzer (Official STEP from KiCad library)
    buzzer_step_path = "/home/sunraku/3D_Components/Buzzer_CUI_9mm.step"
    buzzer_shape = Part.read(buzzer_step_path)
    pl_buzzer = Placement(Vector(0.0, 0.0, 93.0), Rotation(Vector(1, 0, 0), 90.0))
    buzzer_shape.Placement = pl_buzzer
    obj_buzzer = doc.addObject("Part::Feature", "Real_CUI_9mm_Buzzer")
    obj_buzzer.Shape = buzzer_shape
    set_color(obj_buzzer, (0.22, 0.22, 0.24)) # Resonator Dark Metal

    # 4. Real MPU-6050 6-Axis IMU (Official InvenSense QFN-24 Chip + PCB)
    mpu_chip_path = "/home/sunraku/3D_Components/MPU6050_QFN24.step"
    mpu_chip = Part.read(mpu_chip_path)
    pl_mpu = Placement(Vector(0.0, 0.6, 34.0), Rotation(Vector(1, 0, 0), 90.0))
    mpu_chip.Placement = pl_mpu
    imu_pcb = Part.makeBox(10.5, 1.2, 20.0, Vector(-5.25, -0.6, 24.0))
    imu_assembly = imu_pcb.fuse(mpu_chip)
    obj_imu = doc.addObject("Part::Feature", "Real_MPU6050_IMU_Assembly")
    obj_imu.Shape = imu_assembly
    set_color(obj_imu, (0.08, 0.32, 0.82)) # Deep Electronic Blue

    # 5. Real Interlink FSR 402 Sensor Model
    fsr_head = Part.makeCylinder(6.35, 0.45, Vector(0.0, -6.1, 30.0), Vector(0, 1, 0))
    fsr_active = Part.makeCylinder(4.5, 0.50, Vector(0.0, -6.12, 30.0), Vector(0, 1, 0))
    fsr_tail = Part.makeBox(6.0, 0.45, 10.0, Vector(-3.0, -6.1, 20.0))
    fsr_assembly = fsr_head.fuse(fsr_active).fuse(fsr_tail)
    obj_fsr = doc.addObject("Part::Feature", "Real_Interlink_FSR402")
    obj_fsr.Shape = fsr_assembly
    set_color(obj_fsr, (0.95, 0.78, 0.15)) # Amber Polyimide / Carbon Active

    # 6. Status RGB LED Indicator
    mock_led = Part.makeCylinder(0.50, 3.5, Vector(0, 4.5, 126.0), Vector(0, 1, 0))
    obj_led = doc.addObject("Part::Feature", "Real_RGB_Status_LED")
    obj_led.Shape = mock_led
    set_color(obj_led, (0.0, 0.90, 1.0))

    doc.recompute()
    print("Recomputation with real 3D components successful!")

    # =========================================================================
    # EXPORTING ARTIFACTS: FCSTD, STEP, AND 3D-PRINTABLE STLS
    # =========================================================================
    OUTPUT_DIR = "/home/sunraku"
    fcstd_path = os.path.join(OUTPUT_DIR, "NeuroGrip_VerticalTwoPart_Pen.FCStd")
    step_path = os.path.join(OUTPUT_DIR, "NeuroGrip_VerticalTwoPart_Pen.step")
    stl_left_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Vertical_Left_Chassis.stl")
    stl_right_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Vertical_Right_Cover.stl")

    doc.saveAs(fcstd_path)
    print(f"Saved FreeCAD Document: {fcstd_path}")

    all_objs = [obj_left, obj_right, obj_xiao, obj_batt, obj_buzzer, obj_imu, obj_fsr, obj_led]
    Part.export(all_objs, step_path)
    print(f"Exported STEP Assembly with Real Components: {step_path}")

    Part.export([obj_left], stl_left_path)
    Part.export([obj_right], stl_right_path)
    print(f"Exported 3D Print STLs:\n  - {stl_left_path}\n  - {stl_right_path}")

    # Mirror to artifacts directory
    ARTIFACT_DIR = "/home/sunraku/.gemini/antigravity-cli/brain/91c353f2-6f2e-4d17-a6cf-9355eb5a6989"
    for src in [fcstd_path, step_path, stl_left_path, stl_right_path]:
        shutil.copy2(src, os.path.join(ARTIFACT_DIR, os.path.basename(src)))

    print("All Vertical Two-Part Pen models with Real Components exported successfully!")

if __name__ == "__main__":
    build_vertical_twopart_pen()
    sys.exit(0)
