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

def build_compact_pen_assembly():
    doc = App.newDocument("NeuroGrip_RealComponents_Pen")
    App.setActiveDocument("NeuroGrip_RealComponents_Pen")
    print("Created FreeCAD Document: NeuroGrip_RealComponents_Pen (OLED Removed, Ultra-Compact)")

    # =========================================================================
    # PARAMETRIC ARCHITECTURE (OLED REMOVED):
    # 1. Elongated Green Nose Cone: 22.0 mm length (Z = 0.0 to 22.0 mm)
    # 2. Slender Grip: Dia 13.0 mm (Z = 22.0 to 45.0 mm)
    # 3. FSR 402 Recessed Grip Bed + 0.8 mm Light Gap Slot (Z = 20.0 to 39.0 mm)
    # 4. FSR-402 Screw Terminal Breakout Board + MPU-6050 Bay (Z = 24.0 to 47.0 mm)
    # 5. 10440 Li-ion Battery Cradle (Z = 48.0 to 92.5 mm)
    # 6. KY-012 Active Buzzer Module Chamber with Sound Slits (Z = 93.5 to 112.0 mm)
    # 7. Seeed Studio XIAO MCU Bay with Rear USB-C Port (Z = 113.0 to 140.0 mm)
    # 8. Longitudinal Clamshell Split along Y = 0 (Two Vertical Parts)
    # 9. Anti-Shake Internal Ribs, Bulkheads & 7 Alignment Dowels
    # =========================================================================

    # -------------------------------------------------------------------------
    # 1. ULTRA-COMPACT SLEEK MASTER SOLID (Total Length: 140.0 mm, Max Width: 19.0 mm)
    # -------------------------------------------------------------------------
    slices = [
        (2.0, 2.0, 0.0),       # Stylus apex
        (2.8, 2.8, 2.5),       # Tip collar
        (5.0, 5.0, 8.0),       # Elongated green cone
        (8.0, 8.0, 15.0),      # Elongated green cone
        (13.0, 13.0, 22.0),    # Grip waist (OD = 13.0 mm)
        (13.0, 13.0, 45.0),    # Finger pinch grip
        (14.5, 14.0, 60.0),    # Battery barrel section
        (15.5, 14.5, 90.0),    # Battery rear bulkhead
        (19.0, 15.5, 105.0),   # KY-012 Buzzer chamber (max width only 19.0 mm!)
        (18.5, 15.0, 125.0),   # Seeed Studio XIAO MCU deck
        (15.0, 13.5, 135.0),   # Crown taper
        (12.0, 10.5, 140.0)    # Rear dome cap top
    ]

    wires = [make_4edge_stadium(w, h, z) for w, h, z in slices]
    solid_outer = Part.makeLoft(wires, True)

    # Architectural pocket clip on outer barrel
    clip_body = Part.makeBox(2.2, 2.4, 38.0, Vector(-1.1, -9.8, 92.0))
    clip_attach = Part.makeBox(2.2, 2.8, 6.0, Vector(-1.1, -9.6, 124.0))
    clip_ball = Part.makeSphere(1.3, Vector(0, -9.0, 93.5))
    solid_outer = solid_outer.fuse(clip_body.fuse(clip_attach).fuse(clip_ball))

    # -------------------------------------------------------------------------
    # 2. TWO VERTICAL LENGTHWISE PARTS (Parting Plane Y = 0)
    # -------------------------------------------------------------------------
    cutter_pos_y = Part.makeBox(60.0, 40.0, 180.0, Vector(-30.0, 0.0, -20.0))
    half_left = solid_outer.cut(cutter_pos_y)    # Y <= 0 (Left Chassis)

    cutter_neg_y = Part.makeBox(60.0, 40.0, 180.0, Vector(-30.0, -40.0, -20.0))
    half_right = solid_outer.cut(cutter_neg_y)  # Y >= 0 (Right Cover)

    # -------------------------------------------------------------------------
    # 3. INTERNAL COMPONENT BAYS & CAVITIES
    # -------------------------------------------------------------------------
    # A. Front cartridge bore: Z = 0.0 to 16.0 mm
    cartridge_bore = Part.makeCylinder(1.25, 16.0, Vector(0, 0, 0.0), Vector(0, 0, 1))

    # B. Front wire tunnel: Z = 16.0 to 23.0 mm
    wire_tunnel_front = Part.makeCylinder(1.5, 7.0, Vector(0, 0, 16.0), Vector(0, 0, 1))

    # C. FSR 402 Screw Terminal Breakout Board Bay: Z = 24.0 to 46.5 mm
    fsr_pcb_bay = Part.makeBox(12.0, 8.5, 22.5, Vector(-6.0, -4.25, 24.0))

    # D. 10440 Battery Cradle: Z = 48.0 to 92.5 mm (Dia 10.3 mm cradle)
    batt_cradle = Part.makeCylinder(5.15, 44.5, Vector(0, 0, 48.0), Vector(0, 0, 1))

    # E. KY-012 Active Buzzer Module Chamber: Z = 93.5 to 112.0 mm
    # Fits 18.5 x 15.0 mm PCB + Dia 12.0 x 9.5 mm buzzer cylinder
    buzzer_cyl = Part.makeCylinder(6.2, 10.0, Vector(0, 0, 96.0), Vector(0, 0, 1))
    buzzer_pcb_cav = Part.makeBox(18.6, 5.5, 15.5, Vector(-9.3, -2.75, 95.0))

    # F. Seeed Studio XIAO MCU Bay: Z = 113.0 to 134.0 mm
    xiao_pocket = Part.makeBox(17.8, 4.2, 21.0, Vector(-8.9, -2.1, 113.0))

    # G. USB-C Port Cutout: Z = 134.0 to 140.0 mm
    usbc_port = Part.makeBox(9.4, 3.6, 8.0, Vector(-4.7, -1.8, 134.0))

    for c in [cartridge_bore, wire_tunnel_front, fsr_pcb_bay, batt_cradle, buzzer_cyl, buzzer_pcb_cav, xiao_pocket, usbc_port]:
        half_left = half_left.cut(c)
        half_right = half_right.cut(c)

    # H. FSR 402 Light Gap Slot at Z = 20.0 to 20.8 mm (Transverse relief slot)
    fsr_light_gap = Part.makeBox(6.0, 4.0, 0.8, Vector(-3.0, -5.5, 20.0))
    half_left = half_left.cut(fsr_light_gap)

    # I. FSR 402 Recessed Sensor Bed at Z = 21.0 to 39.0 mm (Finger Pinch Grip)
    fsr_bed = Part.makeBox(7.5, 0.55, 18.0, Vector(-3.75, -6.6, 21.0))
    half_left = half_left.cut(fsr_bed)

    # J. Buzzer acoustic sound slits at Z = 101.0 mm (Dorsal face)
    for ang in [-30, 0, 30]:
        slit = Part.makeBox(1.2, 4.5, 3.0, Vector(-0.6, 5.5, 99.5))
        slit.rotate(Vector(0,0,101.0), Vector(0,0,1), ang)
        half_right = half_right.cut(slit)

    # K. RGB Status LED pinhole at Z = 134.5 mm
    led_hole = Part.makeCylinder(1.0, 4.0, Vector(0, 3.5, 134.5), Vector(0, 1, 0))
    half_right = half_right.cut(led_hole)

    # -------------------------------------------------------------------------
    # 4. ANTI-SHAKE RETENTION RIBS & ALIGNMENT DOWEL PINS
    # -------------------------------------------------------------------------
    # Battery compression friction ribs in half_right
    batt_rib1 = Part.makeBox(1.6, 1.8, 8.0, Vector(-0.8, 4.2, 54.0))
    batt_rib2 = Part.makeBox(1.6, 1.8, 8.0, Vector(-0.8, 4.2, 78.0))
    half_right = half_right.fuse(batt_rib1).fuse(batt_rib2)

    # FSR Breakout Board clamping ledge
    fsr_clamp = Part.makeBox(2.0, 1.8, 6.0, Vector(-1.0, 3.6, 32.0))
    half_right = half_right.fuse(fsr_clamp)

    # Buzzer & XIAO clamping ledges
    buzzer_clamp = Part.makeBox(2.0, 1.8, 4.0, Vector(-1.0, 3.8, 103.0))
    xiao_clamp = Part.makeBox(2.0, 1.8, 6.0, Vector(-1.0, 3.8, 120.0))
    half_right = half_right.fuse(buzzer_clamp).fuse(xiao_clamp)

    # 7 Solid-anchored alignment pins & sockets along parting plane Y = 0
    pin_locs = [
        Vector(0.0, 0.0, 10.0),    # Solid tip cone
        Vector(-4.5, 0.0, 47.0),   # FSR / Battery solid bulkhead (left)
        Vector(4.5, 0.0, 47.0),    # FSR / Battery solid bulkhead (right)
        Vector(-6.0, 0.0, 93.0),   # Battery / Buzzer bulkhead (left)
        Vector(6.0, 0.0, 93.0),    # Battery / Buzzer bulkhead (right)
        Vector(-7.5, 0.0, 112.5),  # Buzzer / XIAO bulkhead (left)
        Vector(7.5, 0.0, 112.5)    # Buzzer / XIAO bulkhead (right)
    ]

    for loc in pin_locs:
        socket = Part.makeCylinder(1.05, 2.0, loc, Vector(0, -1, 0))
        half_left = half_left.cut(socket)
        
        pin = Part.makeCylinder(0.90, 1.8, loc, Vector(0, -1, 0))
        pin_anchor = Part.makeCylinder(1.10, 1.2, loc, Vector(0, 1, 0))
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
    # 5. INTEGRATE REAL USER 3D COMPONENTS (NO OLED)
    # -------------------------------------------------------------------------
    print("--- Integrating Real 3D Component Models (No OLED) ---")

    # A. Real FSR 402 with Screw Terminal Breakout Module (from images.jpeg)
    fsr_step_path = "/home/sunraku/3D_Components/FSR402_Breakout_Module.step"
    if os.path.exists(fsr_step_path):
        fsr_raw = Part.read(fsr_step_path)
        pl_fsr = Placement(Vector(0.0, -1.2, 24.5), Rotation(Vector(0,0,1), 0))
        fsr_raw.Placement = pl_fsr
        obj_fsr = doc.addObject("Part::Feature", "Real_FSR402_Breakout_Module")
        obj_fsr.Shape = fsr_raw
        obj_fsr.Visibility = True
        set_color(obj_fsr, (0.08, 0.35, 0.75))

    # B. Real 10440 / AAA Li-ion Battery
    batt_step_path = "/home/sunraku/3D_Components/Battery_10440_AAA.step"
    batt_shape = Part.read(batt_step_path)
    pl_batt = Placement(Vector(0.0, 0.0, 48.0), Rotation(Vector(0, 0, 1), 0))
    batt_shape.Placement = pl_batt
    obj_batt = doc.addObject("Part::Feature", "Real_10440_LiIon_Battery")
    obj_batt.Shape = batt_shape
    obj_batt.Visibility = True
    set_color(obj_batt, (0.10, 0.72, 0.25))

    # C. Real KY-012 Active Buzzer Module (from images (1).jpeg)
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

    # E. MPU-6050 6-Axis IMU
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

    print("All Compact OLED-Free Pen models exported successfully!")

build_compact_pen_assembly()
