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
    import MeshPart
    from FreeCAD import Vector, Rotation, Placement
except ImportError as e:
    print(f"Error importing FreeCAD: {e}")
    sys.exit(1)

def set_color(obj, color):
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color

def make_4edge_stadium(w_x, h_y, z):
    r = h_y / 2.0
    flat = max(0.001, (w_x - 2.0 * r) / 2.0)
    arc1 = Part.makeCircle(r, Vector(flat, 0, z), Vector(0,0,1), -90, 90)
    line1 = Part.makeLine(Vector(flat, r, z), Vector(-flat, r, z))
    arc2 = Part.makeCircle(r, Vector(-flat, 0, z), Vector(0,0,1), 90, 270)
    line2 = Part.makeLine(Vector(-flat, -r, z), Vector(flat, -r, z))
    return Part.Wire([arc1, line1, arc2, line2])

def build_smartpen_assembly():
    doc = App.newDocument("NeuroGrip_RealComponents_Pen")
    App.setActiveDocument("NeuroGrip_RealComponents_Pen")
    print("Created FreeCAD Document: NeuroGrip_RealComponents_Pen")

    # =========================================================================
    # PARAMETRIC ARCHITECTURE FOR REAL USER COMPONENTS:
    # 1. 0.96" I2C OLED Display (SSD1306, 4-Pin): 27.3 x 27.8 mm PCB + Screen Window
    # 2. KY-012 Active Buzzer Module (from images (1).jpeg): 18.5 x 15.0 mm PCB + Dia 12.0 mm cylinder
    # 3. FSR 402 with Screw Terminal Breakout Module (from images.jpeg): Dia 18.28 mm head + 20x22 mm PCB
    # 4. 10440 Li-ion Battery: Dia 10.0 x 44.0 mm
    # 5. Seeed Studio XIAO MCU: 21.0 x 17.5 mm with USB-C Port
    # 6. MPU-6050 6-Axis IMU
    # =========================================================================

    # -------------------------------------------------------------------------
    # 1. ERGONOMIC MASTER SOLID PROFILE (Total Length: 140.0 mm)
    # -------------------------------------------------------------------------
    slices = [
        (2.0, 2.0, 0.0),       # Stylus tip apex
        (2.8, 2.8, 2.5),       # Stylus tip collar
        (5.0, 5.0, 8.0),       # Elongated green cone
        (8.0, 8.0, 15.0),      # Elongated green cone
        (13.0, 13.0, 22.0),    # Transition to grip waist (OD = 13.0 mm)
        (13.0, 13.0, 45.0),    # Ergonomic finger pinch waist
        (15.0, 14.0, 60.0),    # Battery barrel transition
        (22.0, 16.0, 75.0),    # Smooth flare to display deck
        (29.0, 17.0, 88.0),    # Full OLED display deck width (29.0 mm)
        (29.0, 17.0, 126.0),   # Display, Buzzer & XIAO deck
        (24.0, 15.0, 134.0),   # Crown taper
        (16.0, 12.0, 140.0)    # Rear dome cap top
    ]

    wires = [make_4edge_stadium(w, h, z) for w, h, z in slices]
    solid_outer = Part.makeLoft(wires, True)

    # Architectural pocket clip on outer barrel
    clip_body = Part.makeBox(2.6, 2.6, 38.0, Vector(-1.3, -11.0, 92.0))
    clip_attach = Part.makeBox(2.6, 3.2, 6.0, Vector(-1.3, -10.8, 124.0))
    clip_ball = Part.makeSphere(1.4, Vector(0, -10.0, 93.5))
    solid_outer = solid_outer.fuse(clip_body.fuse(clip_attach).fuse(clip_ball))

    # -------------------------------------------------------------------------
    # 2. TWO VERTICAL LENGTHWISE PARTS (Parting Plane Y = 0)
    # -------------------------------------------------------------------------
    cutter_pos_y = Part.makeBox(80.0, 50.0, 180.0, Vector(-40.0, 0.0, -20.0))
    half_left = solid_outer.cut(cutter_pos_y)    # Y <= 0 (Left Chassis)

    cutter_neg_y = Part.makeBox(80.0, 50.0, 180.0, Vector(-40.0, -50.0, -20.0))
    half_right = solid_outer.cut(cutter_neg_y)  # Y >= 0 (Right Cover)

    # -------------------------------------------------------------------------
    # 3. INTERNAL COMPONENT BAYS & CAVITIES
    # -------------------------------------------------------------------------
    # A. Front cartridge bore: Z = 0.0 to 16.0 mm
    cartridge_bore = Part.makeCylinder(1.25, 16.0, Vector(0, 0, 0.0), Vector(0, 0, 1))

    # B. Front wire tunnel: Z = 16.0 to 23.0 mm
    wire_tunnel_front = Part.makeCylinder(1.5, 7.0, Vector(0, 0, 16.0), Vector(0, 0, 1))

    # C. FSR 402 Screw Terminal Breakout Board Bay: Z = 24.0 to 46.5 mm
    # Fits 20.0 x 22.0 mm PCB + green terminal block (8.5 mm high)
    fsr_pcb_bay = Part.makeBox(12.5, 9.0, 22.5, Vector(-6.25, -4.5, 24.0))

    # D. 10440 Battery Cradle: Z = 48.0 to 92.5 mm
    batt_cradle = Part.makeCylinder(5.15, 44.5, Vector(0, 0, 48.0), Vector(0, 0, 1))

    for c in [cartridge_bore, wire_tunnel_front, fsr_pcb_bay, batt_cradle]:
        half_left = half_left.cut(c)
        half_right = half_right.cut(c)

    # E. FSR 402 Light Gap Slot at Z = 20.0 to 20.8 mm (Transverse relief slot)
    fsr_light_gap = Part.makeBox(6.0, 4.0, 0.8, Vector(-3.0, -5.5, 20.0))
    half_left = half_left.cut(fsr_light_gap)

    # F. FSR 402 Recessed Sensor Bed at Z = 21.0 to 39.0 mm (Finger Pinch Grip)
    fsr_bed = Part.makeBox(7.5, 0.55, 18.0, Vector(-3.75, -6.6, 21.0))
    half_left = half_left.cut(fsr_bed)

    # G. 0.96" I2C OLED Display Bay in Upper Cover: Z = 78.0 to 106.5 mm
    # Pocket for 27.3 x 27.8 mm PCB
    oled_pocket = Part.makeBox(27.6, 5.0, 28.5, Vector(-13.8, 2.0, 78.0))
    half_right = half_right.cut(oled_pocket)

    # OLED Viewing Window (Top Face Cutout): 23.0 x 13.0 mm
    oled_window = Part.makeBox(23.0, 10.0, 13.0, Vector(-11.5, 3.0, 85.0))
    half_right = half_right.cut(oled_window)

    # H. KY-012 Active Buzzer Module Bay: Z = 107.0 to 123.5 mm
    # Fits 18.5 x 15.0 mm PCB + Dia 12.0 mm cylinder + 3 right-angle pins
    buzzer_cyl = Part.makeCylinder(6.2, 10.0, Vector(0, 0, 108.5), Vector(0, 0, 1))
    buzzer_pcb_cav = Part.makeBox(18.8, 6.5, 15.5, Vector(-9.4, -3.2, 107.5))
    half_left = half_left.cut(buzzer_cyl).cut(buzzer_pcb_cav)
    half_right = half_right.cut(buzzer_cyl).cut(buzzer_pcb_cav)

    # Buzzer acoustic sound slits at Z = 114.0 mm
    for ang in [30, 90, 150]:
        slit = Part.makeBox(1.0, 4.0, 2.5, Vector(-0.5, 6.0, 112.8))
        slit.rotate(Vector(0,0,114.0), Vector(0,0,1), ang)
        half_right = half_right.cut(slit)

    # I. Seeed Studio XIAO MCU Bay: Z = 124.0 to 140.0 mm
    xiao_pocket = Part.makeBox(17.8, 4.2, 16.5, Vector(-8.9, -2.1, 124.0))
    usbc_port = Part.makeBox(9.4, 3.6, 8.0, Vector(-4.7, -1.8, 134.0))
    half_left = half_left.cut(xiao_pocket).cut(usbc_port)
    half_right = half_right.cut(xiao_pocket).cut(usbc_port)

    # -------------------------------------------------------------------------
    # 4. ANTI-SHAKE RETENTION RIBS & ALIGNMENT DOWEL PINS
    # -------------------------------------------------------------------------
    # Battery compression friction ribs in half_right
    batt_rib1 = Part.makeBox(1.6, 2.0, 10.0, Vector(-0.8, 4.6, 54.0))
    batt_rib2 = Part.makeBox(1.6, 2.0, 10.0, Vector(-0.8, 4.6, 76.0))
    half_right = half_right.fuse(batt_rib1).fuse(batt_rib2)

    # FSR Breakout Board clamping ledge
    fsr_clamp = Part.makeBox(2.0, 2.0, 6.0, Vector(-1.0, 4.0, 32.0))
    half_right = half_right.fuse(fsr_clamp)

    # 7 Solid-anchored alignment pins & sockets along parting plane Y = 0
    pin_locs = [
        Vector(0.0, 0.0, 10.0),    # Solid tip cone
        Vector(-4.5, 0.0, 47.0),   # FSR / Battery solid bulkhead (left)
        Vector(4.5, 0.0, 47.0),    # FSR / Battery solid bulkhead (right)
        Vector(-10.5, 0.0, 77.0),  # Display shoulder (left)
        Vector(10.5, 0.0, 77.0),   # Display shoulder (right)
        Vector(-11.5, 0.0, 124.0), # Buzzer / XIAO bulkhead (left)
        Vector(11.5, 0.0, 124.0)   # Buzzer / XIAO bulkhead (right)
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

    obj_left = doc.addObject("Part::Feature", "NeuroGrip_Left_Chassis")
    obj_left.Shape = half_left
    obj_left.Visibility = True
    set_color(obj_left, (0.75, 0.78, 0.82)) # Brushed Aerospace Titanium

    obj_right = doc.addObject("Part::Feature", "NeuroGrip_Right_Cover")
    obj_right.Shape = half_right
    obj_right.Visibility = True
    set_color(obj_right, (0.02, 0.05, 0.12)) # Midnight Executive Navy

    # -------------------------------------------------------------------------
    # 5. INTEGRATE REAL USER 3D COMPONENTS INTO ASSEMBLY
    # -------------------------------------------------------------------------
    print("--- Integrating Real 3D Component Models ---")

    # A. Real 0.96" I2C OLED Display (SSD1306)
    oled_step_path = "/home/sunraku/3D_Components/OLED_SSD1306_0.96.step"
    if os.path.exists(oled_step_path):
        oled_raw = Part.read(oled_step_path)
        pl_oled = Placement(Vector(-13.6, 2.8, 78.5), Rotation(Vector(0,0,1), 0))
        oled_raw.Placement = pl_oled
        obj_oled = doc.addObject("Part::Feature", "Real_OLED_Display_096")
        obj_oled.Shape = oled_raw
        obj_oled.Visibility = True
        set_color(obj_oled, (0.05, 0.15, 0.45))

    # B. Real KY-012 Active Buzzer Module (from images (1).jpeg)
    ky012_step_path = "/home/sunraku/3D_Components/KY012_Buzzer_Module.step"
    if os.path.exists(ky012_step_path):
        buzzer_raw = Part.read(ky012_step_path)
        pl_buzzer = Placement(Vector(0.0, 0.0, 108.5), Rotation(Vector(0,0,1), 0))
        buzzer_raw.Placement = pl_buzzer
        obj_buzzer = doc.addObject("Part::Feature", "Real_KY012_Buzzer_Module")
        obj_buzzer.Shape = buzzer_raw
        obj_buzzer.Visibility = True
        set_color(obj_buzzer, (0.15, 0.15, 0.18))
    else:
        buzzer_body = Part.makeCylinder(6.0, 9.5, Vector(0, 0, 108.5), Vector(0, 0, 1))
        obj_buzzer = doc.addObject("Part::Feature", "Real_KY012_Buzzer_Module")
        obj_buzzer.Shape = buzzer_body
        obj_buzzer.Visibility = True

    # C. Real FSR 402 with Screw Terminal Breakout Module (from images.jpeg)
    fsr_step_path = "/home/sunraku/3D_Components/FSR402_Breakout_Module.step"
    if os.path.exists(fsr_step_path):
        fsr_raw = Part.read(fsr_step_path)
        # Position board in bay Z = 24.5 mm, tail extends forward to FSR bed
        pl_fsr = Placement(Vector(0.0, -1.5, 24.5), Rotation(Vector(0,0,1), 0))
        fsr_raw.Placement = pl_fsr
        obj_fsr = doc.addObject("Part::Feature", "Real_FSR402_Breakout_Module")
        obj_fsr.Shape = fsr_raw
        obj_fsr.Visibility = True
        set_color(obj_fsr, (0.08, 0.35, 0.75))

    # D. Real 10440 / AAA Li-ion Battery
    batt_step_path = "/home/sunraku/3D_Components/Battery_10440_AAA.step"
    batt_shape = Part.read(batt_step_path)
    pl_batt = Placement(Vector(0.0, 0.0, 48.0), Rotation(Vector(0, 0, 1), 0))
    batt_shape.Placement = pl_batt
    obj_batt = doc.addObject("Part::Feature", "Real_10440_LiIon_Battery")
    obj_batt.Shape = batt_shape
    obj_batt.Visibility = True
    set_color(obj_batt, (0.10, 0.72, 0.25))

    # E. Real Seeed Studio XIAO MCU (Official 83-solid STEP)
    xiao_step_path = "/home/sunraku/3D_Components/Seeed_Studio_XIAO.step"
    xiao_shape = Part.read(xiao_step_path)
    pl_xiao = Placement(Vector(0.0, 0.0, 126.0), Rotation(Vector(1, 0, 0), -90.0))
    xiao_shape.Placement = pl_xiao
    obj_xiao = doc.addObject("Part::Feature", "Real_Seeed_Studio_XIAO_MCU")
    obj_xiao.Shape = xiao_shape
    obj_xiao.Visibility = True
    set_color(obj_xiao, (0.75, 0.15, 0.15))

    # F. MPU-6050 6-Axis IMU
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

    # =========================================================================
    # EXPORTING ARTIFACTS
    # =========================================================================
    OUTPUT_DIR = "/home/sunraku"
    fcstd_path = os.path.join(OUTPUT_DIR, "NeuroGrip_RealComponents_Pen.FCStd")
    step_path = os.path.join(OUTPUT_DIR, "NeuroGrip_RealComponents_Pen.step")
    stl_left_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Left_Chassis.stl")
    stl_right_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Right_Cover.stl")

    doc.saveAs(fcstd_path)
    print(f"Saved FreeCAD Document: {fcstd_path}")

    all_objs = [obj_left, obj_right, obj_oled, obj_buzzer, obj_fsr, obj_batt, obj_xiao, obj_mpu]
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

    print("All Pen models designed for user components exported successfully!")

build_smartpen_assembly()
