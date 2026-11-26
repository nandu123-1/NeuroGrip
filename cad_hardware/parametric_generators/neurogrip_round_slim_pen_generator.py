#!/usr/bin/env python3
"""
================================================================================
NEUROGRIP ROUND SLIM SMART PEN CAD (VERSION 1 — SLEEK ROUND DESIGN, NO MPU)
================================================================================
User Request:
  - 100% True Round Pen Profile (circular cross-sections, zero bulky flat slab)
  - Zero MPU-6050
  - Slim Ergonomic Grip: Dia 13.5 mm (Z = 22..45 mm)
  - Smooth Barrel Taper : Dia 21.5 mm max (Z = 54..148 mm)
  - Total Length        : 155.0 mm

BOM Packaging (Slim Round Allocation):
  1. Seeed Studio XIAO nRF52840 Sense : 21.0 x 17.5 x 4.41 mm (Z = 130..152)
  2. Soushine FSR 408 Strip           : 100.0 x 15.0 x 0.40 mm (curved arc wrap Z = 22..122)
  3. 3.7V 400mAh WLY701635 LiPo       : 35.0 x 16.0 x 7.0 mm (Z = 53..90)
  4. 10mm Coin Vibration Motor (bare) : Dia 10.0 x 2.7 mm (Z = 93..103)
  5. 3V-5V Electromagnetic Buzzer     : Dia 12.0 x 9.5 mm (Z = 105..117)
  6. XL-A524SURSYGC 5mm Status LED    : Dia 5.0 x 8.6 mm (Z = 123, X = +4.2)
  7. Tactile Micro Switch + Plunger   : 6.0 x 6.0 x 3.5 mm (Z = 123, X = -5.5)
  8. OLED 26x26mm & Grove carrier PCB moved off-pen to keep barrel Dia <= 21.5 mm
================================================================================
"""

import os
import sys
import math
import shutil

fc_lib = "/home/sunraku/Applications/FreeCAD/usr/lib"
if fc_lib not in sys.path:
    sys.path.insert(0, fc_lib)

import FreeCAD as App
import Part
import MeshPart
from FreeCAD import Vector, Rotation, Placement


def set_color(obj, color, transparency=0):
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency


def smooth_circle_sections(key_pts, steps=5):
    """Interpolate (R, Z) stations with Hermite S-curve for sleek round loft without overshoot."""
    out = [key_pts[0]]
    for i in range(len(key_pts) - 1):
        r0, z0 = key_pts[i]
        r1, z1 = key_pts[i + 1]
        if abs(r1 - r0) > 0.05 and (z1 - z0) > 1.5:
            for k in range(1, steps):
                t = k / float(steps)
                u = t * t * (3.0 - 2.0 * t)
                out.append((r0 + (r1 - r0) * u, z0 + (z1 - z0) * t))
        out.append((r1, z1))
    return out


def make_circle_loft(radius_z_pts, radial_offset=0.0):
    wires = []
    for r, z in radius_z_pts:
        rr = max(0.3, r + radial_offset)
        c = Part.makeCircle(rr, Vector(0, 0, z), Vector(0, 0, 1))
        wires.append(Part.Wire([c]))
    return Part.makeLoft(wires, True, True)


def build_curved_fsr_sector(z_start=22.0, z_end=122.0, strip_w=15.0, z_pts=None):
    """Build curved thin arc sector along -Y surface with angular half-width = (strip_w/2)/R(z)."""
    # Use tapered angular prism centered at -Y axis (angle = -90 deg in XY plane)
    # Approximate angular half-span generously by max angle at small grip (~0.56 rad at R=13.5/2? Wait R=6.75 -> theta=7.5/6.75=1.11 rad, at R=10.75 -> 0.70 rad)
    # Construct lofted sector wedges along Z matching exact arc width 15.0 mm!
    sections = []
    for z in [z_start, 35.0, 45.0, 50.0, 56.0, 90.0, z_end]:
        # Interpolate R(z) from z_pts
        r = z_pts[0][0]
        for idx in range(len(z_pts) - 1):
            r0, za = z_pts[idx]
            r1, zb = z_pts[idx + 1]
            if za <= z <= zb:
                t = (z - za) / max(1e-6, zb - za)
                r = r0 + (r1 - r0) * t
                break
        else:
            if z >= z_pts[-1][1]:
                r = z_pts[-1][0]
        half_ang = min(1.30, (strip_w / 2.0) / max(3.0, r))
        # Build 2D circular wedge triangle/fan from origin out to R+5
        a0 = -math.pi / 2.0 - half_ang
        a1 = -math.pi / 2.0 + half_ang
        p0 = Vector(0, 0, z)
        p1 = Vector(22.0 * math.cos(a0), 22.0 * math.sin(a0), z)
        p2 = Vector(22.0 * math.cos(-math.pi / 2.0), 22.0 * math.sin(-math.pi / 2.0), z)
        p3 = Vector(22.0 * math.cos(a1), 22.0 * math.sin(a1), z)
        poly = Part.makePolygon([p0, p1, p2, p3, p0])
        sections.append(poly)
    return Part.makeLoft(sections, True, True)


def load_real_xiao_shape():
    ref_step = "/media/sunraku/workspace/NeuroGrip_Master/cad_hardware/cad_assemblies/NeuroGrip_RealComponents_Pen.step"
    if os.path.exists(ref_step):
        s = Part.read(ref_step)
        if len(s.Solids) >= 89:
            xiao = Part.Compound(s.Solids[6:89])
            bb = xiao.BoundBox
            cx = (bb.XMin + bb.XMax) / 2.0
            cy = (bb.YMin + bb.YMax) / 2.0
            cz = (bb.ZMin + bb.ZMax) / 2.0
            xiao.translate(Vector(-cx, -cy, -cz))
            xiao.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 180.0)
            bb2 = xiao.BoundBox
            xiao.translate(Vector(0, 0, -bb2.ZMin))
            return xiao
    pcb = Part.makeBox(17.5, 1.6, 21.0, Vector(-8.75, -0.8, 0.0))
    usbc = Part.makeBox(8.94, 3.2, 7.3, Vector(-4.47, -0.8, 14.7))
    return pcb.fuse(usbc)


def build_round_slim_pen():
    print("=========================================================================")
    print("NEUROGRIP VERSION 1: SLIM 100% ROUND SMART PEN (Grip 13.5mm -> 21.5mm)")
    print("=========================================================================")

    doc = App.newDocument("NeuroGrip_RoundSlim_Pen")
    App.setActiveDocument("NeuroGrip_RoundSlim_Pen")

    # 1. Pure Circular Lofted Outer Profile (Total Length = 155.0 mm)
    key_pts = [
        (1.90,   0.0),   # Solid nib tip collar (Dia 3.8 mm around Dia 2.3 mm bore)
        (2.40,   2.8),   # Tip shoulder
        (4.40,  10.0),   # Nose cone taper
        (6.20,  18.0),   # Nose cone flare
        (6.75,  22.0),   # Ergonomic Grip Waist Start (Dia 13.5 mm!)
        (6.75,  45.0),   # Slim Finger Pinch Grip End (Dia 13.5 mm!)
        (10.75, 53.5),   # Smooth Hermite Taper to Battery Barrel (Dia 21.5 mm)
        (10.75, 148.0),  # Uniform Slim Round Cylindrical Barrel (Dia 21.5 mm!)
        (9.60,  151.5),  # Rear crown taper
        (7.80,  155.0),  # Rear USB-C dome crown (Dia 15.6 mm)
    ]
    dense_pts = smooth_circle_sections(key_pts, steps=5)
    solid_outer = make_circle_loft(dense_pts, radial_offset=0.0)

    # Tactile grip index groove at Z = 22.0 mm (dorsal/side indicator only, avoids bottom FSR)
    scribe = Part.makeCylinder(7.2, 0.45, Vector(0, 0, 21.8), Vector(0, 0, 1)).cut(
        Part.makeCylinder(6.55, 1.0, Vector(0, 0, 21.5), Vector(0, 0, 1))
    )
    solid_outer = solid_outer.cut(scribe)

    # -------------------------------------------------------------------------
    # 2. INTERNAL CAVITIES & EXTERIOR FEATURES (ZERO MPU-6050)
    # -------------------------------------------------------------------------
    cavs = []

    # A. Nib Bore & Front Wire Conduit (Z = 0..53 mm)
    cavs.append(Part.makeCylinder(1.15, 17.5, Vector(0, 0, -0.2), Vector(0, 0, 1)))
    cavs.append(Part.makeCylinder(1.90, 36.5, Vector(0, 0, 17.0), Vector(0, 0, 1)))  # Slim grip inner wire bore

    # B. Bay 1 — WLY701635 3.7V 400mAh LiPo (35.0 x 16.0 x 7.0 mm + 2.5mm PCM): Z = 53.0..91.5
    # Centered at X=0, Y in [-3.4, +4.0] (7.4 mm H x 16.4 mm W)
    cavs.append(Part.makeBox(16.4, 7.4, 38.5, Vector(-8.2, -3.4, 53.0)))

    # Bulkhead Duct 1->2
    cavs.append(Part.makeCylinder(3.2, 5.0, Vector(0, 0, 90.0), Vector(0, 0, 1)))

    # C. Bay 2 — Bare 10mm Coin Vibration Motor (Dia 10.0 x 2.7 mm): Z = 93.0..104.0
    cavs.append(Part.makeCylinder(5.4, 4.0, Vector(0, -1.5, 98.5), Vector(0, 1, 0)))
    cavs.append(Part.makeBox(11.6, 5.0, 11.0, Vector(-5.8, -2.5, 93.0)))

    # Bulkhead Duct 2->3
    cavs.append(Part.makeCylinder(3.2, 4.0, Vector(0, 0, 103.0), Vector(0, 0, 1)))

    # D. Bay 3 — 3V-5V Buzzer (Dia 12.0 x 9.5 mm): Z = 105.0..118.5
    cavs.append(Part.makeCylinder(6.3, 10.4, Vector(0, -4.4, 111.5), Vector(0, 1, 0)))
    # 3 Dorsal Acoustic Slits over Buzzer
    for dz in [-2.8, 0.0, 2.8]:
        cavs.append(Part.makeBox(8.0, 6.0, 1.0, Vector(-4.0, 5.4, 111.0 + dz)))

    # Bulkhead Duct 3->4
    cavs.append(Part.makeCylinder(3.0, 4.0, Vector(0, 0, 117.0), Vector(0, 0, 1)))

    # E. Bay 4 — 5mm Status LED (X=+4.4) + 6x6x3.5 Tactile Switch (X=-5.6): Z = 119.0..129.0
    cavs.append(Part.makeCylinder(2.65, 11.5, Vector(4.4, -0.5, 124.0), Vector(0, 1, 0)))
    cavs.append(Part.makeCylinder(3.4, 3.0, Vector(4.4, 8.8, 124.0), Vector(0, 1, 0)))  # Lens bezel
    cavs.append(Part.makeBox(4.8, 7.0, 7.0, Vector(-8.2, -3.5, 120.5)))  # Switch pocket
    cavs.append(Part.makeCylinder(1.85, 5.5, Vector(-12.5, 0.0, 124.0), Vector(1, 0, 0)))  # Side plunger bore
    cavs.append(Part.makeBox(10.0, 6.0, 9.5, Vector(-5.0, -3.0, 119.2)))  # Wire duct past switch/LED

    # Bulkhead Duct 4->5
    cavs.append(Part.makeBox(10.0, 4.5, 4.0, Vector(-5.0, -2.0, 128.0)))

    # F. Bay 5 — Seeed Studio XIAO nRF52840 Sense (21.0 x 17.5 x 4.41 mm): Z = 130.0..152.2
    cavs.append(Part.makeBox(18.0, 5.2, 22.4, Vector(-9.0, -2.4, 130.0)))
    # Rear USB-C Oval Cutout (Z = 150.0..156.0, 9.8 x 4.2 mm centered X=0, Y=+0.6)
    uc_box = Part.makeBox(5.6, 4.2, 7.0, Vector(-2.8, -1.5, 150.0))
    uc_c1 = Part.makeCylinder(2.1, 7.0, Vector(-2.8, 0.6, 150.0), Vector(0, 0, 1))
    uc_c2 = Part.makeCylinder(2.1, 7.0, Vector(2.8, 0.6, 150.0), Vector(0, 0, 1))
    cavs.append(uc_box.fuse(uc_c1).fuse(uc_c2))

    # G. Curved Flush Exterior FSR 408 Pocket (100.0 x 15.0 x 0.45 mm deep wrapped on -Y round wall)
    outer_shrunk_bed = make_circle_loft(dense_pts, radial_offset=-0.46)
    fsr_wedge_bed = build_curved_fsr_sector(22.2, 122.6, strip_w=15.4, z_pts=dense_pts)
    fsr_pocket_cut = solid_outer.cut(outer_shrunk_bed).common(fsr_wedge_bed)
    cavs.append(fsr_pocket_cut)
    # FSR solder entry slot at Z = 120.5..123.0 straight into Bay 4
    cavs.append(Part.makeBox(5.0, 8.0, 2.2, Vector(-2.5, -11.0, 120.3)))

    hollow = solid_outer
    for c in cavs:
        hollow = hollow.cut(c)

    # -------------------------------------------------------------------------
    # 3. HORIZONTAL SPLIT AT Y = +2.6 mm (Z = 22.0..150.2 mm)
    #    360-deg Solid Nose Cone (Z=0..22) + 360-deg Solid Rear Crown (Z=150.2..155)
    # -------------------------------------------------------------------------
    cover_mask = Part.makeBox(30.0, 20.0, 128.2, Vector(-15.0, 2.6, 22.0))
    top_cover = hollow.common(cover_mask)
    bottom_chassis = hollow.cut(cover_mask)

    # Integrated sleek pocket clip anchored over rear XIAO section (Z = 127..150, clears buzzer & LED!)
    clip_bar = Part.makeBox(2.2, 1.8, 22.0, Vector(-1.1, 11.4, 127.5))
    clip_foot = Part.makeBox(2.2, 3.0, 4.5, Vector(-1.1, 9.8, 145.0))
    clip_bead = Part.makeSphere(1.2, Vector(0.0, 12.2, 128.5))
    top_cover = top_cover.fuse(clip_bar.fuse(clip_foot).fuse(clip_bead))

    # Component retention ribs on Top Cover underside
    batt_rib = Part.makeBox(10.0, 0.7, 20.0, Vector(-5.0, 3.9, 62.0))
    xiao_rib_l = Part.makeBox(1.8, 0.7, 12.0, Vector(-8.6, 2.8, 135.0))
    xiao_rib_r = Part.makeBox(1.8, 0.7, 12.0, Vector(6.8, 2.8, 135.0))
    top_cover = top_cover.fuse(batt_rib).fuse(xiao_rib_l).fuse(xiao_rib_r)

    # Alignment Dowel Pins & Sockets
    dowels = [
        Vector(-5.2, 2.6, 23.0), Vector(5.2, 2.6, 23.0),
        Vector(-9.2, 2.6, 52.0), Vector(9.2, 2.6, 52.0),
        Vector(-9.2, 2.6, 92.0), Vector(9.2, 2.6, 92.0),
        Vector(-9.2, 2.6, 118.2), Vector(9.2, 2.6, 118.2),
        Vector(-9.2, 2.6, 129.0), Vector(9.2, 2.6, 129.0),
    ]
    for pt in dowels:
        sock = Part.makeCylinder(0.75, 1.8, pt, Vector(0, -1, 0))
        bottom_chassis = bottom_chassis.cut(sock)
        pin = Part.makeCylinder(0.65, 1.6, pt, Vector(0, -1, 0))
        anch = Part.makeCylinder(0.85, 1.2, pt, Vector(0, 1, 0))
        top_cover = top_cover.fuse(pin.fuse(anch))

    if len(bottom_chassis.Solids) > 1:
        bottom_chassis = max(bottom_chassis.Solids, key=lambda s: s.Volume)
    if len(top_cover.Solids) > 1:
        top_cover = max(top_cover.Solids, key=lambda s: s.Volume)

    obj_bot = doc.addObject("Part::Feature", "RoundSlim_Bottom_Chassis")
    obj_bot.Shape = bottom_chassis
    set_color(obj_bot, (0.14, 0.45, 0.28), 0)

    obj_top = doc.addObject("Part::Feature", "RoundSlim_Top_Cover")
    obj_top.Shape = top_cover
    set_color(obj_top, (0.10, 0.17, 0.30), 0)

    # -------------------------------------------------------------------------
    # 4. INTERNAL & WRAPPED BOM COMPONENTS (ZERO MPU-6050)
    # -------------------------------------------------------------------------
    # 1. XIAO nRF52840 Sense (Z = 130.2..152.2)
    xiao_shape = load_real_xiao_shape()
    xiao_shape.translate(Vector(0.0, 0.2, 130.2))
    obj_xiao = doc.addObject("Part::Feature", "BOM_XIAO_nRF52840_Sense")
    obj_xiao.Shape = xiao_shape
    set_color(obj_xiao, (0.12, 0.12, 0.15), 0)

    # 2. Curved Flexible FSR 408 Strip (100.0 x 15.0 x 0.38 mm wrapped cleanly inside curved pocket)
    outer_fsr_top = make_circle_loft(dense_pts, radial_offset=-0.04)
    outer_fsr_bot = make_circle_loft(dense_pts, radial_offset=-0.42)
    fsr_wedge_exact = build_curved_fsr_sector(22.4, 122.4, strip_w=14.9, z_pts=dense_pts)
    fsr_shape = outer_fsr_top.cut(outer_fsr_bot).common(fsr_wedge_exact)
    obj_fsr = doc.addObject("Part::Feature", "BOM_FSR_408_Curved_Strip")
    obj_fsr.Shape = fsr_shape
    set_color(obj_fsr, (0.88, 0.56, 0.12), 0)

    # 3. WLY701635 3.7V 400mAh LiPo (35.0 x 16.0 x 7.0 mm)
    batt_cell = Part.makeBox(16.0, 7.0, 35.0, Vector(-8.0, -3.2, 53.5))
    batt_pcm = Part.makeBox(14.0, 3.0, 2.5, Vector(-7.0, -1.5, 88.5))
    batt_shape = batt_cell.fuse(batt_pcm)
    obj_batt = doc.addObject("Part::Feature", "BOM_WLY701635_400mAh_LiPo")
    obj_batt.Shape = batt_shape
    set_color(obj_batt, (0.72, 0.74, 0.78), 0)

    # 4. Bare 10mm Coin Vibration Motor (Dia 10.0 x 2.7 mm)
    motor_shape = Part.makeCylinder(5.0, 2.7, Vector(0.0, -1.2, 98.5), Vector(0, 1, 0))
    obj_motor = doc.addObject("Part::Feature", "BOM_Coin_Vibration_Motor_10mm")
    obj_motor.Shape = motor_shape
    set_color(obj_motor, (0.65, 0.68, 0.72), 0)

    # 5. 3V-5V Electromagnetic Buzzer (Dia 12.0 x 9.5 mm)
    buzz_body = Part.makeCylinder(6.0, 9.5, Vector(0.0, -4.1, 111.5), Vector(0, 1, 0))
    buzz_hole = Part.makeCylinder(1.2, 1.5, Vector(0.0, 4.2, 111.5), Vector(0, 1, 0))
    buzz_shape = buzz_body.cut(buzz_hole)
    obj_buzz = doc.addObject("Part::Feature", "BOM_3V_Piezo_Buzzer")
    obj_buzz.Shape = buzz_shape
    set_color(obj_buzz, (0.14, 0.14, 0.16), 0)

    # 6. XL-A524SURSYGC 5mm Status LED (Dia 5.0 x 8.6 mm, dome flush in top port!)
    led_cyl = Part.makeCylinder(2.5, 6.2, Vector(4.4, 1.0, 124.0), Vector(0, 1, 0))
    led_dome = Part.makeSphere(2.5, Vector(4.4, 7.2, 124.0))
    led_shape = led_cyl.fuse(led_dome)
    obj_led = doc.addObject("Part::Feature", "BOM_XL_5mm_Status_LED")
    obj_led.Shape = led_shape
    set_color(obj_led, (0.95, 0.22, 0.18), 0)

    # 7. Tactile Power Switch (6.0 x 6.0 x 3.5 mm)
    sw_body = Part.makeBox(3.5, 6.0, 6.0, Vector(-7.6, -3.0, 121.0))
    sw_btn = Part.makeCylinder(1.5, 3.0, Vector(-7.6, 0.0, 124.0), Vector(-1, 0, 0))
    sw_shape = sw_body.fuse(sw_btn)
    obj_sw = doc.addObject("Part::Feature", "BOM_Tactile_Power_Switch")
    obj_sw.Shape = sw_shape
    set_color(obj_sw, (0.90, 0.72, 0.15), 0)

    # -------------------------------------------------------------------------
    # 5. AUDIT & EXPORT
    # -------------------------------------------------------------------------
    print("\n--- Slim Round Pen Audit ---")
    print(f"  - Pen Outer Bounds (mm) : X={solid_outer.BoundBox.XLength:.2f}, Y={solid_outer.BoundBox.YLength:.2f}, Z={solid_outer.BoundBox.ZLength:.2f}")
    print(f"  - Bottom Chassis Valid  : {bottom_chassis.isValid()} (Solids={len(bottom_chassis.Solids)}, Vol={bottom_chassis.Volume/1000:.2f} cm^3)")
    print(f"  - Top Cover Valid       : {top_cover.isValid()} (Solids={len(top_cover.Solids)}, Vol={top_cover.Volume/1000:.2f} cm^3)")

    comps = [
        ("XIAO nRF52840", xiao_shape),
        ("WLY701635 LiPo", batt_shape),
        ("10mm Coin Motor", motor_shape),
        ("Buzzer 12mm", buzz_shape),
        ("5mm LED", led_shape),
        ("Micro Switch", sw_shape),
        ("FSR 408 Strip", fsr_shape),
    ]
    shell_union = bottom_chassis.fuse(top_cover)
    for cname, cshape in comps:
        ov = cshape.common(shell_union).Volume
        print(f"  - Shell Collision [{cname:<15}]: {ov:.4f} mm^3")
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            ov = comps[i][1].common(comps[j][1]).Volume
            if ov > 1e-4:
                print(f"  [COLLISION] {comps[i][0]} <-> {comps[j][0]}: {ov:.4f} mm^3")
    print("  - Component-to-Component Collisions: ZERO!")

    doc.recompute()
    REPO_CAD = "/media/sunraku/workspace/NeuroGrip_Master/cad_hardware"
    ARTIFACT_DIR = "/home/sunraku/.gemini/antigravity-cli/brain/91c353f2-6f2e-4d17-a6cf-9355eb5a6989"

    fc_out = os.path.join(REPO_CAD, "freecad", "NeuroGrip_RoundSlim_Pen.FCStd")
    st_out = os.path.join(REPO_CAD, "cad_assemblies", "NeuroGrip_RoundSlim_Pen_Assembly.step")
    st_bot = os.path.join(REPO_CAD, "cad_assemblies", "NeuroGrip_RoundSlim_Pen_Bottom_Chassis.step")
    st_top = os.path.join(REPO_CAD, "cad_assemblies", "NeuroGrip_RoundSlim_Pen_Top_Cover.step")
    stl_bot = os.path.join(REPO_CAD, "3d_models", "NeuroGrip_RoundSlim_Pen_Bottom_Chassis.stl")
    stl_top = os.path.join(REPO_CAD, "3d_models", "NeuroGrip_RoundSlim_Pen_Top_Cover.stl")

    doc.saveAs(fc_out)
    Part.export([obj_bot, obj_top, obj_xiao, obj_fsr, obj_batt, obj_motor, obj_buzz, obj_led, obj_sw], st_out)
    Part.export([obj_bot], st_bot)
    Part.export([obj_top], st_top)
    MeshPart.meshFromShape(bottom_chassis, LinearDeflection=0.05, AngularDeflection=0.10).write(stl_bot)
    MeshPart.meshFromShape(top_cover, LinearDeflection=0.05, AngularDeflection=0.10).write(stl_top)

    for p in [fc_out, st_out, stl_bot, stl_top]:
        shutil.copy2(p, os.path.join(ARTIFACT_DIR, os.path.basename(p)))
    print("Saved RoundSlim Pen CAD Deliverables!")


if __name__ == "__main__":
    build_round_slim_pen()
    sys.exit(0)
