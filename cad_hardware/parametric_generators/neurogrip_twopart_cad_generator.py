import sys
import os
import math

# Add FreeCAD lib path
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

def create_stadium_prism(length_z, radius_r, width_x, z_offset=0.0):
    """
    Creates a rounded rectangular / stadium cylinder along the Z axis.
    Cross section in XY: two semi-circles of radius R separated by flat width.
    width_x is total width across X.
    height_y is 2 * radius_r across Y.
    """
    flat_w = max(0.0, width_x - 2.0 * radius_r)
    # Box in middle
    box = Part.makeBox(flat_w, 2.0 * radius_r, length_z, Vector(-flat_w/2.0, -radius_r, z_offset))
    # Left cylinder
    cyl_l = Part.makeCylinder(radius_r, length_z, Vector(-flat_w/2.0, 0, z_offset), Vector(0, 0, 1))
    # Right cylinder
    cyl_r = Part.makeCylinder(radius_r, length_z, Vector(flat_w/2.0, 0, z_offset), Vector(0, 0, 1))
    shape = box.fuse(cyl_l).fuse(cyl_r)
    return shape

def build_twopart_pen():
    doc = App.newDocument("NeuroGrip_2Part_Pen")
    App.setActiveDocument("NeuroGrip_2Part_Pen")
    print("Created FreeCAD Document: NeuroGrip_2Part_Pen")

    # =========================================================================
    # PARAMETRIC DIMENSIONS (All in millimeters)
    # Total pen: L = 150mm, W = 18.5mm, H = 16.0mm
    # Parting plane: Y = 0 (Bottom Chassis: Y <= 0, Top Cover: Y >= 0)
    # =========================================================================
    TOTAL_LENGTH = 150.0
    BODY_WIDTH = 18.5
    BODY_HEIGHT = 16.0
    BODY_RADIUS_Y = BODY_HEIGHT / 2.0  # 8.0 mm
    
    # --- 1. OUTER SOLID GENERATION ---
    print("--- 1. Generating Master Outer Body ---")
    # A. Front Stylus Tip (Z = 0 to 18mm): Closed, smooth conical nose with rounded tip
    # Tip cone: R1 = 2.5mm at Z = 0, R2 = 6.5mm at Z = 18
    tip_cone = Part.makeCone(2.5, 6.5, 18.0, Vector(0, 0, 0), Vector(0, 0, 1))
    # Round hemisphere at very tip
    tip_sphere = Part.makeSphere(2.5, Vector(0, 0, 0))
    stylus_nose = tip_cone.fuse(tip_sphere)
    
    # B. Ergonomic Grip Section (Z = 18 to 52mm):
    # Taper from 13.0mm to 12.0mm finger waist, expanding to stadium body
    grip_cone1 = Part.makeCone(6.5, 6.0, 16.0, Vector(0, 0, 18.0), Vector(0, 0, 1)) # to waist at Z=34
    grip_cone2 = Part.makeCone(6.0, 7.5, 18.0, Vector(0, 0, 34.0), Vector(0, 0, 1)) # to Z=52
    grip_section = grip_cone1.fuse(grip_cone2)
    
    # C. Main Electronics Barrel (Z = 52 to 146mm):
    # Stadium profile: W = 18.5mm, H = 16.0mm (R = 8.0mm)
    barrel_length = 146.0 - 52.0
    main_barrel = create_stadium_prism(barrel_length, BODY_RADIUS_Y, BODY_WIDTH, z_offset=52.0)
    
    # D. Rear Dome Cap (Z = 146 to 150mm):
    rear_cap = create_stadium_prism(4.0, BODY_RADIUS_Y - 0.4, BODY_WIDTH - 0.8, z_offset=146.0)
    
    # Fuse entire outer solid
    master_outer = stylus_nose.fuse(grip_section).fuse(main_barrel).fuse(rear_cap)

    # --- 2. SPLITTING INTO BOTTOM CHASSIS & TOP COVER (Y = 0 Plane) ---
    print("--- 2. Splitting into Two Halves along Parting Line Y = 0 ---")
    cutter_top = Part.makeBox(60.0, 30.0, TOTAL_LENGTH + 20.0, Vector(-30.0, 0.0, -10.0))
    cutter_bottom = Part.makeBox(60.0, 30.0, TOTAL_LENGTH + 20.0, Vector(-30.0, -30.0, -10.0))
    
    bottom_solid = master_outer.cut(cutter_top)     # Y <= 0
    top_solid = master_outer.cut(cutter_bottom)       # Y >= 0

    # --- 3. INTERNAL COMPONENT CARRIAGES IN BOTTOM CHASSIS ---
    print("--- 3. Machining Component Bays in Bottom Chassis ---")
    # A. MPU-6050 6-Axis IMU Bay (Z = 24.0 to 45.5mm)
    # Fits standard 21.0 x 15.5 x 2.5 mm board
    imu_pocket = Part.makeBox(16.0, 3.8, 22.0, Vector(-8.0, -3.8, 24.0))
    bottom_chassis = bottom_solid.cut(imu_pocket)
    
    # B. FSR Grip Sensor Pocket & Wire Channel (on Grip Surface)
    # Recessed pad seat on finger rest: 18.0 x 7.5 x 0.8 mm
    fsr_pocket = Part.makeBox(7.5, 4.0, 18.0, Vector(-3.75, -7.8, 22.0))
    bottom_chassis = bottom_chassis.cut(fsr_pocket)
    # Wire lead slot from FSR into IMU bay
    fsr_wire_slot = Part.makeBox(3.0, 8.0, 4.0, Vector(-1.5, -7.0, 26.0))
    bottom_chassis = bottom_chassis.cut(fsr_wire_slot)

    # C. Rechargeable 10440 Battery Cradle (Z = 48.0 to 93.0mm)
    # Semi-cylindrical scoop: D = 11.0mm, Length = 44.5mm
    batt_cradle = Part.makeCylinder(5.5, 45.0, Vector(0, 0, 48.0), Vector(0, 0, 1))
    bottom_chassis = bottom_chassis.cut(batt_cradle)

    # D. Buzzer Resonance Well (Z = 95.0 to 106.0mm)
    # Cylindrical well: D = 9.5mm, Depth = 4.2mm
    buzzer_well = Part.makeCylinder(4.75, 4.2, Vector(0, -4.2, 100.5), Vector(0, 1, 0))
    bottom_chassis = bottom_chassis.cut(buzzer_well)

    # E. Seeed Studio XIAO nRF52840 MCU Bay (Z = 108.0 to 131.0mm)
    # Carriage pocket: 18.0 x 4.2 x 22.5 mm
    xiao_pocket = Part.makeBox(18.0, 4.5, 22.5, Vector(-9.0, -4.5, 108.0))
    bottom_chassis = bottom_chassis.cut(xiao_pocket)

    # F. Rear USB-C Charging Port Slot (Z = 142.0 to 150.0mm)
    usbc_port = Part.makeBox(9.4, 2.0, 9.0, Vector(-4.7, -2.0, 142.0))
    bottom_chassis = bottom_chassis.cut(usbc_port)

    # G. Continuous Longitudinal Wire Raceways (Left & Right channels)
    # 2.0 x 2.0 mm channels along both flanks
    raceway_left = Part.makeBox(2.2, 2.5, 120.0, Vector(-8.5, -2.5, 24.0))
    raceway_right = Part.makeBox(2.2, 2.5, 120.0, Vector(6.3, -2.5, 24.0))
    bottom_chassis = bottom_chassis.cut(raceway_left).cut(raceway_right)

    # H. Alignment Pin Sockets (4x sockets along mating seam)
    socket_locs = [
        Vector(-7.5, 0.0, 22.0),
        Vector(7.5, 0.0, 22.0),
        Vector(-7.5, 0.0, 94.0),
        Vector(7.5, 0.0, 94.0),
        Vector(-7.5, 0.0, 142.0),
        Vector(7.5, 0.0, 142.0)
    ]
    for loc in socket_locs:
        hole = Part.makeCylinder(1.15, 3.2, loc - Vector(0, 3.2, 0), Vector(0, 1, 0))
        bottom_chassis = bottom_chassis.cut(hole)

    # I. Perimeter Lap Joint Mating Step (0.8mm step)
    step_rim = Part.makeBox(18.8, 0.8, 128.0, Vector(-9.4, -0.8, 20.0))
    step_core = Part.makeBox(17.0, 2.0, 130.0, Vector(-8.5, -1.0, 19.0))
    step_lip = step_rim.cut(step_core)
    bottom_chassis = bottom_chassis.cut(step_lip)

    # --- 4. MACHINING TOP ENCLOSURE LID ---
    print("--- 4. Machining Top Enclosure Lid ---")
    # Cut front portion of lid so the front stylus tip is single-piece solid on bottom
    front_tip_trim = Part.makeBox(40.0, 30.0, 20.0, Vector(-20.0, 0.0, -5.0))
    top_cover = top_solid.cut(front_tip_trim)

    # A. OLED Display Viewing Window (Z = 108.0 to 131.0mm)
    # 22.5 x 8.8 mm through-cutout
    oled_window = Part.makeBox(8.8, 12.0, 22.5, Vector(-4.4, 0.0, 108.0))
    top_cover = top_cover.cut(oled_window)

    # B. RGB LED Status Indicator Light Window (Z = 134.0 to 142.0mm)
    led_window = Part.makeBox(12.0, 12.0, 4.0, Vector(-6.0, 0.0, 134.0))
    top_cover = top_cover.cut(led_window)

    # C. Buzzer Sound Acoustic Ports (4x micro-holes above buzzer chamber at Z = 98..104mm)
    for z_hole in [98.0, 100.0, 102.0, 104.0]:
        sound_port = Part.makeCylinder(0.65, 12.0, Vector(0, 0, z_hole), Vector(0, 1, 0))
        top_cover = top_cover.cut(sound_port)

    # D. Rear USB-C Port Upper Clearance
    usbc_top = Part.makeBox(9.4, 2.0, 9.0, Vector(-4.7, 0.0, 142.0))
    top_cover = top_cover.cut(usbc_top)

    # E. Internal Clearance Relief (Hollow out inside of lid by 2.0mm for wire/component headspace)
    internal_relief = Part.makeBox(15.0, 2.2, 124.0, Vector(-7.5, 0.0, 22.0))
    top_cover = top_cover.cut(internal_relief)

    # F. Add Alignment Dowel Pins (Matching bottom chassis sockets)
    for loc in socket_locs:
        pin = Part.makeCylinder(1.05, 2.8, loc - Vector(0, 2.8, 0), Vector(0, 1, 0))
        top_cover = top_cover.fuse(pin)

    # --- 5. ADD OBJECTS TO FREECAD DOCUMENT ---
    obj_bottom = doc.addObject("Part::Feature", "NeuroGrip_Bottom_Chassis")
    obj_bottom.Shape = bottom_chassis
    set_color(obj_bottom, (0.15, 0.45, 0.85)) # Technical Blue

    obj_top = doc.addObject("Part::Feature", "NeuroGrip_Top_Cover")
    obj_top.Shape = top_cover
    set_color(obj_top, (0.05, 0.12, 0.22)) # Deep Midnight Slate

    # --- 6. ADD ACCURATE COMPONENT MOCKUPS FOR CLEARANCE VERIFICATION ---
    print("--- 6. Adding Electronic Component Mockups ---")
    # MPU-6050 IMU Mockup
    mock_imu = Part.makeBox(15.5, 2.5, 21.0, Vector(-7.75, -3.2, 24.5))
    obj_imu = doc.addObject("Part::Feature", "Mockup_MPU6050_IMU")
    obj_imu.Shape = mock_imu
    set_color(obj_imu, (0.10, 0.30, 0.85))

    # 10440 Battery Mockup
    mock_batt = Part.makeCylinder(5.0, 43.5, Vector(0, 0, 49.0), Vector(0, 0, 1))
    obj_batt = doc.addObject("Part::Feature", "Mockup_Battery_10440")
    obj_batt.Shape = mock_batt
    set_color(obj_batt, (0.15, 0.75, 0.35))

    # Buzzer Mockup
    mock_buzzer = Part.makeCylinder(4.5, 3.5, Vector(0, -3.8, 100.5), Vector(0, 1, 0))
    obj_buzzer = doc.addObject("Part::Feature", "Mockup_Buzzer")
    obj_buzzer.Shape = mock_buzzer
    set_color(obj_buzzer, (0.25, 0.25, 0.25))

    # Seeed Studio XIAO nRF52840 MCU Mockup
    mock_xiao = Part.makeBox(17.5, 3.5, 21.0, Vector(-8.75, -4.0, 108.5))
    obj_xiao = doc.addObject("Part::Feature", "Mockup_XIAO_nRF52840")
    obj_xiao.Shape = mock_xiao
    set_color(obj_xiao, (0.80, 0.15, 0.15))

    # FSR Sensor Pad Mockup
    mock_fsr = Part.makeBox(7.0, 0.6, 17.5, Vector(-3.5, -7.8, 22.2))
    obj_fsr = doc.addObject("Part::Feature", "Mockup_FSR_Pad")
    obj_fsr.Shape = mock_fsr
    set_color(obj_fsr, (0.90, 0.75, 0.20))

    # Recompute document
    doc.recompute()
    print("Recomputation successful!")

    # =========================================================================
    # EXPORTING 2-PART FILES: FCSTD, STEP, AND INDIVIDUAL STLS
    # =========================================================================
    OUTPUT_DIR = "/home/sunraku"
    fcstd_path = os.path.join(OUTPUT_DIR, "NeuroGrip_TwoPart_Assembly.FCStd")
    step_path = os.path.join(OUTPUT_DIR, "NeuroGrip_TwoPart_Assembly.step")
    stl_bottom_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Bottom_Chassis.stl")
    stl_top_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Top_Cover.stl")

    doc.saveAs(fcstd_path)
    print(f"Saved FreeCAD Document: {fcstd_path}")

    all_objs = [obj_bottom, obj_top, obj_imu, obj_batt, obj_buzzer, obj_xiao, obj_fsr]
    Part.export(all_objs, step_path)
    print(f"Exported STEP Exchange Assembly: {step_path}")

    # Export individual STLs ready for 3D printing (BambuStudio / PrusaSlicer)
    Part.export([obj_bottom], stl_bottom_path)
    Part.export([obj_top], stl_top_path)
    print(f"Exported 3D Print STLs:\n  - {stl_bottom_path}\n  - {stl_top_path}")

    # Copy to artifacts directory
    ARTIFACT_DIR = "/home/sunraku/.gemini/antigravity-cli/brain/91c353f2-6f2e-4d17-a6cf-9355eb5a6989"
    import shutil
    for src in [fcstd_path, step_path, stl_bottom_path, stl_top_path]:
        shutil.copy2(src, os.path.join(ARTIFACT_DIR, os.path.basename(src)))

    print("All Two-Part Pen models and 3D print STLs generated successfully!")

if __name__ == "__main__":
    build_twopart_pen()
    sys.exit(0)
