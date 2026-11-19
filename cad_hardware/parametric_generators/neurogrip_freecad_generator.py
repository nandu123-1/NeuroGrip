import sys
import os
import math

# Ensure FreeCAD lib path is present
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

def build_neurogrip_cad():
    doc = App.newDocument("NeuroGrip_Pen_Assembly")
    App.setActiveDocument("NeuroGrip_Pen_Assembly")
    print("Created FreeCAD Document: NeuroGrip_Pen_Assembly")

    # =========================================================================
    # PARAMETRIC CONSTANTS & TOLERANCES (All units in millimeters)
    # =========================================================================
    TOL_CLEARANCE = 0.20   # Standard FDM 3D printing slip-fit clearance
    WALL_MIN = 1.20        # Minimum structural wall thickness for FDM/SLA
    
    # Pen Outer Dimensions
    PEN_DIAMETER_OUTER = 14.50
    PEN_RADIUS_OUTER = PEN_DIAMETER_OUTER / 2.0  # 7.25 mm
    PEN_BORE_INNER = 13.20
    PEN_BORE_RADIUS = PEN_BORE_INNER / 2.0      # 6.60 mm
    
    # Internal Chassis Dimensions
    CHASSIS_DIAMETER = 13.00
    CHASSIS_RADIUS = CHASSIS_DIAMETER / 2.0      # 6.50 mm (0.1mm clearance to bore)
    CHASSIS_LENGTH = 118.00
    
    # Ink Refill Dimensions (Standard Parker/G2 or D1 refill)
    REFILL_DIAMETER = 3.00
    REFILL_RADIUS = (REFILL_DIAMETER + 0.3) / 2.0  # 1.65 mm bore
    NIB_APERTURE_RADIUS = 1.25                     # 2.5 mm hole for pen tip
    
    # Component Pocket Dimensions
    # 1. FSR Wiring Pass-through
    FSR_SLOT_WIDTH = 6.00
    FSR_SLOT_HEIGHT = 2.50
    FSR_SLOT_Z = 16.00
    
    # 2. MPU-6050 IMU Pocket (GY-521 or carrier breakout)
    IMU_LENGTH = 21.50
    IMU_WIDTH = 10.50
    IMU_DEPTH = 3.20
    IMU_Z_START = 24.00
    
    # 3. Battery Carriage Cradle (Cylindrical 10440 / LiPo)
    BATTERY_LENGTH = 44.00
    BATTERY_DIAM = 10.50
    BATTERY_RADIUS = BATTERY_DIAM / 2.0
    BATTERY_Z_START = 48.00
    
    # 4. Seeed Studio XIAO nRF52840 Pocket
    XIAO_LENGTH = 21.50
    XIAO_WIDTH = 11.50
    XIAO_DEPTH = 4.20
    XIAO_Z_START = 94.00
    
    # 5. Buzzer Cavity
    BUZZER_DIAM = 9.20
    BUZZER_RADIUS = BUZZER_DIAM / 2.0
    BUZZER_DEPTH = 4.00
    BUZZER_Z = 88.00
    
    # 6. USB-C Rear Receptacle Port
    USBC_WIDTH = 9.20
    USBC_HEIGHT = 3.60
    USBC_DEPTH = 8.00

    print("--- 1. Building Internal Component Chassis Sled ---")
    # Base solid cylinder for the chassis
    chassis_base = Part.makeCylinder(CHASSIS_RADIUS, CHASSIS_LENGTH, Vector(0, 0, 0), Vector(0, 0, 1))
    
    # A. Central longitudinal ink refill tunnel
    # Offset slightly towards the ventral side (-Y) so components sit above it (+Y)
    ink_tunnel = Part.makeCylinder(REFILL_RADIUS, CHASSIS_LENGTH + 4.0, Vector(0, -3.2, -2.0), Vector(0, 0, 1))
    chassis = chassis_base.cut(ink_tunnel)
    
    # B. Front nose docking tenon (step-down to fit into the lower grip housing)
    step_cutter = Part.makeCylinder(CHASSIS_RADIUS + 2.0, 14.0, Vector(0, 0, -1.0), Vector(0, 0, 1))
    step_core = Part.makeCylinder(5.0, 16.0, Vector(0, 0, -2.0), Vector(0, 0, 1))
    step_ring = step_cutter.cut(step_core)
    chassis = chassis.cut(step_ring)
    
    # C. FSR wiring pass-through slot
    fsr_slot = Part.makeBox(FSR_SLOT_WIDTH, 12.0, FSR_SLOT_HEIGHT, Vector(-FSR_SLOT_WIDTH/2.0, -6.0, FSR_SLOT_Z))
    chassis = chassis.cut(fsr_slot)
    
    # D. MPU-6050 IMU indexed mounting pocket
    imu_pocket = Part.makeBox(IMU_WIDTH, 10.0, IMU_LENGTH, Vector(-IMU_WIDTH/2.0, CHASSIS_RADIUS - IMU_DEPTH, IMU_Z_START))
    chassis = chassis.cut(imu_pocket)
    
    # E. Battery cradle trough (cylindrical scoop)
    battery_scoop = Part.makeCylinder(BATTERY_RADIUS, BATTERY_LENGTH, Vector(0, 1.2, BATTERY_Z_START), Vector(0, 0, 1))
    chassis = chassis.cut(battery_scoop)
    
    # F. Buzzer cavity
    buzzer_cavity = Part.makeCylinder(BUZZER_RADIUS, BUZZER_DEPTH + 4.0, Vector(0, CHASSIS_RADIUS - BUZZER_DEPTH, BUZZER_Z), Vector(0, 1, 0))
    chassis = chassis.cut(buzzer_cavity)
    
    # G. XIAO nRF52840 MCU carriage bay
    xiao_pocket = Part.makeBox(XIAO_WIDTH, 10.0, XIAO_LENGTH, Vector(-XIAO_WIDTH/2.0, CHASSIS_RADIUS - XIAO_DEPTH, XIAO_Z_START))
    chassis = chassis.cut(xiao_pocket)
    
    # H. Rear USB-C port exit tunnel
    usbc_port = Part.makeBox(USBC_WIDTH, USBC_HEIGHT, USBC_DEPTH + 4.0, Vector(-USBC_WIDTH/2.0, CHASSIS_RADIUS - XIAO_DEPTH + 0.4, CHASSIS_LENGTH - USBC_DEPTH))
    chassis = chassis.cut(usbc_port)
    
    # I. Longitudinal Wire Raceways (Left & Right side channels for 3.3V, GND, I2C lines)
    left_raceway = Part.makeBox(1.80, 2.50, CHASSIS_LENGTH - 10.0, Vector(-CHASSIS_RADIUS, -1.25, 10.0))
    right_raceway = Part.makeBox(1.80, 2.50, CHASSIS_LENGTH - 10.0, Vector(CHASSIS_RADIUS - 1.80, -1.25, 10.0))
    chassis = chassis.cut(left_raceway)
    chassis = chassis.cut(right_raceway)

    # Add Chassis to Document
    obj_chassis = doc.addObject("Part::Feature", "NeuroGrip_Internal_Chassis")
    obj_chassis.Shape = chassis
    set_color(obj_chassis, (0.25, 0.55, 0.85)) # Tech Blue

    print("--- 2. Building Ergonomic Lower Grip Housing ---")
    # Outer profile: Revolved ergonomic grip cone
    # From Z = -28.0 (tip) to Z = 24.0 (mid joint)
    p1 = Vector(NIB_APERTURE_RADIUS + 0.8, 0, -28.0)
    p2 = Vector(4.0, 0, -22.0)
    p3 = Vector(5.8, 0, -14.0)
    p4 = Vector(6.0, 0, -4.0)  # Ergonomic finger waist
    p5 = Vector(6.6, 0, 8.0)
    p6 = Vector(PEN_RADIUS_OUTER, 0, 24.0)
    p7 = Vector(0, 0, 24.0)
    p8 = Vector(0, 0, -28.0)
    
    wire_outer = Part.makePolygon([p8, p1, p2, p3, p4, p5, p6, p7, p8])
    face_outer = Part.Face(wire_outer)
    grip_solid = face_outer.revolve(Vector(0,0,0), Vector(0,0,1), 360.0)
    
    # Internal bore for chassis docking tenon and ink refill
    grip_inner_bore = Part.makeCylinder(5.20, 26.0, Vector(0, 0, 0.0), Vector(0, 0, 1))
    grip_nib_bore = Part.makeCylinder(NIB_APERTURE_RADIUS, 32.0, Vector(0, 0, -30.0), Vector(0, 0, 1))
    grip_housing = grip_solid.cut(grip_inner_bore)
    grip_housing = grip_housing.cut(grip_nib_bore)
    
    # Recessed FSR sensor pocket on the outer grip surface (+Y face)
    fsr_pocket = Part.makeBox(7.5, 4.0, 18.0, Vector(-3.75, 4.8, -10.0))
    grip_housing = grip_housing.cut(fsr_pocket)
    # FSR wire feed-through hole into the chassis
    fsr_wire_hole = Part.makeCylinder(1.5, 6.0, Vector(0, 4.0, 6.0), Vector(0, -1, 0))
    grip_housing = grip_housing.cut(fsr_wire_hole)

    obj_grip = doc.addObject("Part::Feature", "NeuroGrip_Grip_Housing")
    obj_grip.Shape = grip_housing
    set_color(obj_grip, (0.20, 0.22, 0.25)) # Dark Graphite

    print("--- 3. Building Upper Barrel & Display Shell ---")
    SHELL_LENGTH = 96.00
    SHELL_Z_START = 22.00
    
    # Outer and inner cylinders for the barrel sleeve
    shell_outer = Part.makeCylinder(PEN_RADIUS_OUTER, SHELL_LENGTH, Vector(0, 0, SHELL_Z_START), Vector(0, 0, 1))
    shell_bore = Part.makeCylinder(PEN_BORE_RADIUS, SHELL_LENGTH + 2.0, Vector(0, 0, SHELL_Z_START - 1.0), Vector(0, 0, 1))
    shell = shell_outer.cut(shell_bore)
    
    # A. OLED Display Viewing Window (+Y face)
    oled_window = Part.makeBox(8.5, 6.0, 23.0, Vector(-4.25, 4.0, 93.0))
    shell = shell.cut(oled_window)
    
    # B. RGB Halo Ring Seat (3.5mm step recess at lower joint)
    halo_step = Part.makeCylinder(PEN_RADIUS_OUTER + 1.0, 3.5, Vector(0, 0, SHELL_Z_START - 0.5), Vector(0, 0, 1))
    halo_core = Part.makeCylinder(PEN_BORE_RADIUS + 0.3, 5.0, Vector(0, 0, SHELL_Z_START - 1.0), Vector(0, 0, 1))
    halo_recess = halo_step.cut(halo_core)
    shell = shell.cut(halo_recess)
    
    # C. Buzzer sound venting micro-ports (4x holes on -Y face)
    for i, z_hole in enumerate([86.0, 88.0, 90.0]):
        sound_hole = Part.makeCylinder(0.60, 6.0, Vector(0, -4.0, z_hole), Vector(0, -1, 0))
        shell = shell.cut(sound_hole)
        
    # D. Rear End Cap USB-C Entry Bevel
    rear_usbc = Part.makeBox(USBC_WIDTH + 1.0, USBC_HEIGHT + 1.0, 10.0, Vector(-(USBC_WIDTH+1)/2.0, CHASSIS_RADIUS - XIAO_DEPTH - 0.1, SHELL_Z_START + SHELL_LENGTH - 6.0))
    shell = shell.cut(rear_usbc)

    obj_shell = doc.addObject("Part::Feature", "NeuroGrip_Upper_Shell")
    obj_shell.Shape = shell
    set_color(obj_shell, (0.12, 0.22, 0.38)) # Midnight Blue Anodized

    print("--- 4. Creating CAD Component Mockups for Fit Verification ---")
    # Ink Refill Mockup
    refill_geo = Part.makeCylinder(1.5, 125.0, Vector(0, -3.2, -26.0), Vector(0, 0, 1))
    nib_tip = Part.makeCone(1.5, 0.4, 4.0, Vector(0, -3.2, -30.0), Vector(0, 0, 1))
    refill_geo = refill_geo.fuse(nib_tip)
    obj_refill = doc.addObject("Part::Feature", "Mockup_Ink_Refill")
    obj_refill.Shape = refill_geo
    set_color(obj_refill, (0.85, 0.75, 0.30)) # Brass

    # Battery 10440 Mockup
    battery_geo = Part.makeCylinder(5.0, 43.5, Vector(0, 1.2, BATTERY_Z_START + 0.25), Vector(0, 0, 1))
    obj_batt = doc.addObject("Part::Feature", "Mockup_Battery_10440")
    obj_batt.Shape = battery_geo
    set_color(obj_batt, (0.20, 0.70, 0.40)) # Battery Green

    # XIAO nRF52840 Board Mockup
    xiao_geo = Part.makeBox(10.5, 3.2, 21.0, Vector(-5.25, CHASSIS_RADIUS - XIAO_DEPTH + 0.4, XIAO_Z_START + 0.25))
    obj_xiao = doc.addObject("Part::Feature", "Mockup_XIAO_nRF52840")
    obj_xiao.Shape = xiao_geo
    set_color(obj_xiao, (0.70, 0.15, 0.15)) # Board Red

    # MPU-6050 IMU Board Mockup
    imu_geo = Part.makeBox(10.0, 2.2, 20.5, Vector(-5.0, CHASSIS_RADIUS - IMU_DEPTH + 0.4, IMU_Z_START + 0.5))
    obj_imu = doc.addObject("Part::Feature", "Mockup_MPU6050_IMU")
    obj_imu.Shape = imu_geo
    set_color(obj_imu, (0.10, 0.30, 0.80)) # Board Blue

    # Recompute document
    doc.recompute()
    print("Recomputation successful!")

    # =========================================================================
    # EXPORTING ARTIFACTS: STEP, STL, AND FCSTD
    # =========================================================================
    OUTPUT_DIR = "/home/sunraku"
    fcstd_path = os.path.join(OUTPUT_DIR, "NeuroGrip_3D_Printable_Assembly.FCStd")
    step_path = os.path.join(OUTPUT_DIR, "NeuroGrip_3D_Printable_Assembly.step")
    stl_chassis_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Internal_Chassis.stl")
    stl_grip_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Grip_Housing.stl")
    stl_shell_path = os.path.join(OUTPUT_DIR, "NeuroGrip_Upper_Shell.stl")
    
    # Save FreeCAD Document
    doc.saveAs(fcstd_path)
    print(f"Saved FreeCAD Document: {fcstd_path}")
    
    # Export STEP assembly
    all_objs = [obj_chassis, obj_grip, obj_shell, obj_refill, obj_batt, obj_xiao, obj_imu]
    Part.export(all_objs, step_path)
    print(f"Exported STEP Exchange Model: {step_path}")
    
    # Export individual STLs for 3D printing
    Part.export([obj_chassis], stl_chassis_path)
    Part.export([obj_grip], stl_grip_path)
    Part.export([obj_shell], stl_shell_path)
    print(f"Exported 3D Print STLs:\n  - {stl_chassis_path}\n  - {stl_grip_path}\n  - {stl_shell_path}")
    
    # Copy exported files to artifacts directory for user inspection
    ARTIFACT_DIR = "/home/sunraku/.gemini/antigravity-cli/brain/91c353f2-6f2e-4d17-a6cf-9355eb5a6989"
    import shutil
    for src in [stl_chassis_path, stl_grip_path, stl_shell_path, step_path]:
        shutil.copy2(src, os.path.join(ARTIFACT_DIR, os.path.basename(src)))
        
    print("All CAD models, STEP files, and STLs generated successfully!")

if __name__ == "__main__":
    build_neurogrip_cad()
    sys.exit(0)
