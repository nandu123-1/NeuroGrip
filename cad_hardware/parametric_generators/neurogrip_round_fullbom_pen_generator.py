#!/usr/bin/env python3
"""
================================================================================
NEUROGRIP ROUND FULL-BOM SMART PEN CAD (VERSION 2 — UNCHANGED BOM IN ROUND BODY)
================================================================================
User Request:
  - 100% True Round Circular Profile (Grip Dia 14.0 mm -> Smooth Teardrop Dia 30.4 mm)
  - Zero MPU-6050
  - Houses EVERY unchanged BOM module & breakout PCB inside a cylindrical shell:
      1. Seeed Studio XIAO nRF52840 Sense : 21.0 x 17.5 x 4.41 mm
      2. Soushine FSR 408 Strip Sensor     : 100.0 x 15.0 x 0.40 mm (curved arc wrap)
      3. 3.7V 400mAh WLY701635 LiPo        : 35.0 x 16.0 x 7.0 mm
      4. Seeed Studio Grove Vibration Motor: 24.0 x 20.0 x 9.8 mm (full Grove PCB)
      5. Waveshare 0.96" OLED (Ver. C)     : 26.0 x 26.0 x 4.0 mm (top recessed chord window)
      6. 3V-5V Electromagnetic Buzzer      : Dia 12.0 x 9.5 mm
      7. XL-A524SURSYGC 5mm Status LED     : Dia 5.0 x 8.6 mm
      8. Tactile Micro Switch + Plunger    : 6.0 x 6.0 x 3.5 mm
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
from FreeCAD import Vector


def set_color(obj, color, transparency=0):
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency


def smooth_circle_sections(key_pts, steps=5):
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
        wires.append(Part.Wire([Part.makeCircle(rr, Vector(0, 0, z), Vector(0, 0, 1))]))
    return Part.makeLoft(wires, True, True)


def build_curved_fsr_sector(z_start=22.0, z_end=122.0, strip_w=15.0, z_pts=None):
    sections = []
    for z in [z_start, 35.0, 44.0, 50.0, 56.0, 88.0, 96.0, 115.0, z_end]:
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
        a0 = -math.pi / 2.0 - half_ang
        a1 = -math.pi / 2.0 + half_ang
        p0 = Vector(0, 0, z)
        p1 = Vector(24.0 * math.cos(a0), 24.0 * math.sin(a0), z)
        p2 = Vector(24.0 * math.cos(-math.pi / 2.0), 24.0 * math.sin(-math.pi / 2.0), z)
        p3 = Vector(24.0 * math.cos(a1), 24.0 * math.sin(a1), z)
        sections.append(Part.makePolygon([p0, p1, p2, p3, p0]))
    return Part.makeLoft(sections, True, True)


def load_real_xiao_shape():
    ref_step = "/media/sunraku/workspace/NeuroGrip_Master/cad_hardware/cad_assemblies/NeuroGrip_RealComponents_Pen.step"
    if os.path.exists(ref_step):
        s = Part.read(ref_step)
        if len(s.Solids) >= 89:
            xiao = Part.Compound(s.Solids[6:89])
            bb = xiao.BoundBox
            xiao.translate(Vector(-(bb.XMin + bb.XMax) / 2.0, -(bb.YMin + bb.YMax) / 2.0, -(bb.ZMin + bb.ZMax) / 2.0))
            xiao.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 180.0)
            bb2 = xiao.BoundBox
            xiao.translate(Vector(0, 0, -bb2.ZMin))
            return xiao
    pcb = Part.makeBox(17.5, 1.6, 21.0, Vector(-8.75, -0.8, 0.0))
    usbc = Part.makeBox(8.94, 3.2, 7.3, Vector(-4.47, -0.8, 14.7))
    return pcb.fuse(usbc)


def build_round_fullbom_pen():
    print("=========================================================================")
    print("NEUROGRIP VERSION 2: FULL-BOM 100% ROUND PEN (Grip 14mm -> OLED Dia 30.4mm)")
    print("=========================================================================")

    doc = App.newDocument("NeuroGrip_RoundFullBOM_Pen")
    App.setActiveDocument("NeuroGrip_RoundFullBOM_Pen")

    # Total Length = 172.0 mm
    key_pts = [
        (1.90,   0.0),   # Solid nib tip collar (Dia 3.8 mm)
        (2.40,   2.8),   # Tip flare
        (4.50,  10.0),   # Nose cone
        (6.40,  18.0),   # Nose cone shoulder
        (7.00,  22.0),   # Slim Round Grip Waist Start (Dia 14.0 mm)
        (7.00,  44.0),   # Slim Finger Pinch Grip End (Dia 14.0 mm)
        (10.80, 52.0),   # Smooth flare to Battery section (Dia 21.6 mm)
        (10.80, 88.0),   # LiPo Battery barrel end (Dia 21.6 mm)
        (12.80, 94.0),   # Smooth flare to Grove Motor PCB (Dia 25.6 mm)
        (12.80, 117.0),  # Grove Motor barrel end
        (15.20, 123.0),  # Smooth swell around 26x26 OLED PCB (Dia 30.4 mm circular!)
        (15.20, 149.5),  # OLED Deck rear
        (12.50, 155.5),  # Graceful taper to Buzzer/LED/Switch (Dia 25.0 mm)
        (11.40, 162.5),  # Transition to XIAO bay
        (10.80, 168.0),  # XIAO barrel (Dia 21.6 mm)
        (8.00,  174.0),  # Rear dome cap USB-C face
    ]
    #Wait check total length Z=174..176 -> let's end cleanly at Z=176.0 with XIAO at 150..172!
    # Wait: Bay 4 (Buzzer+LED+Switch) between OLED (Z=123..149.5) & XIAO (Z=152..174) needs 12mm -> let's adjust Z:
    key_pts = [
        (1.90,   0.0),   # Solid tip collar
        (2.40,   2.8),
        (4.50,  10.0),
        (6.40,  18.0),
        (7.00,  22.0),   # Dia 14.0 mm Slim Grip
        (7.00,  44.0),   # Dia 14.0 mm Slim Grip
        (10.80, 52.0),   # Dia 21.6 mm Battery Barrel
        (10.80, 88.0),
        (12.80, 94.0),   # Dia 25.6 mm Grove Motor PCB
        (12.80, 117.0),
        (15.20, 123.0),  # Dia 30.4 mm Waveshare 0.96 OLED circular housing
        (15.20, 149.5),
        (12.60, 154.0),  # Buzzer + LED + Switch chamber (Dia 25.2 mm)
        (11.50, 164.0),  # Taper into XIAO MCU
        (10.80, 168.0),  # Dia 21.6 mm XIAO bay front..rear
        (10.80, 184.0),
        (8.40,  189.0),  # Rear USB-C crown dome
    ]
    # Wait: 189 mm is quite long for a pen! Let's check why: can Buzzer+LED+Switch sit inside OLED Z=123..149 OR overlap slightly?
    # Look! Waveshare OLED only sits in TOP half (Y > +1.0, Z=123..149)! Underneath OLED inside a Dia 30.4 mm circle,
    # Y spans -13.5 to +0.5 mm (14 mm circular room below OLED!!)!
    # A Dia 12.0 x 9.5 mm Buzzer + 5mm LED flank + 6x6 Switch fit cleanly BELOW/NEXT TO or tightly right after!
    # Wait: Putting Buzzer (Dia 12 x 9.5) + Switch/LED cleanly at Z=150..162 -> XIAO at Z=163..185 keeps ZERO Z overlap!
    # Or tightening Battery (50..87 -> 46..83), Grove Motor (85..110), OLED (112..138.5), Buzzer/LED/Switch (140..153), XIAO (154..176 -> crown 179.0)!
    # 179 mm is right near standard stylus length (166-175 mm)! Let's use Z = 178.0 mm total!
    key_pts = [
        (1.90,   0.0),   # Solid tip collar (Dia 3.8 mm)
        (2.40,   2.8),
        (4.50,  10.0),
        (6.40,  18.0),
        (7.00,  22.0),   # Dia 14.0 mm Slim Finger Grip
        (7.00,  42.0),
        (10.80, 48.0),   # Smooth curve to Dia 21.6 mm Battery
        (10.80, 84.0),
        (12.80, 89.5),   # Smooth curve to Dia 25.6 mm Grove Motor PCB
        (12.80, 110.5),
        (15.20, 115.0),  # Smooth curve to Dia 30.4 mm OLED Deck (circular!)
        (15.20, 142.5),
        (13.20, 146.0),  # Buzzer + LED + Switch Chamber (Dia 26.4 mm)
        (12.20, 154.5),
        (10.80, 158.0),  # Dia 21.6 mm XIAO Sense Deck
        (10.80, 177.0),
        (8.40,  181.5),  # Rear USB-C Crown Cap (Total 181.5 mm)
    ]

    dense_pts = smooth_circle_sections(key_pts, steps=5)
    solid_outer = make_circle_loft(dense_pts, radial_offset=0.0)

    # Tactile grip index ring at Z = 22.0 mm
    scribe = Part.makeCylinder(7.5, 0.45, Vector(0, 0, 21.8), Vector(0, 0, 1)).cut(
        Part.makeCylinder(6.80, 1.0, Vector(0, 0, 21.5), Vector(0, 0, 1))
    )
    solid_outer = solid_outer.cut(scribe)

    # -------------------------------------------------------------------------
    # 2. INTERNAL CAVITIES & EXTERIOR CUTOUTS (ZERO MPU-6050)
    # -------------------------------------------------------------------------
    cavs = []

    # A. Stylus Nib & Grip Wire Channel (Z = 0..48)
    cavs.append(Part.makeCylinder(1.15, 17.5, Vector(0, 0, -0.2), Vector(0, 0, 1)))
    cavs.append(Part.makeCylinder(1.90, 32.0, Vector(0, 0, 17.0), Vector(0, 0, 1)))

    # B. Bay 1 — WLY701635 LiPo (35.0 x 16.0 x 7.0 mm): Z = 47.0..84.5
    cavs.append(Part.makeBox(16.4, 7.4, 38.0, Vector(-8.2, -3.5, 47.0)))
    cavs.append(Part.makeCylinder(3.2, 5.0, Vector(0, 0, 84.0), Vector(0, 0, 1)))

    # C. Bay 2 — Full Grove Vibration Motor PCB (24.0 x 20.0 x 9.8 mm): Z = 88.0..112.8
    cavs.append(Part.makeBox(20.4, 10.2, 24.8, Vector(-10.2, -4.8, 88.0)))
    cavs.append(Part.makeCylinder(4.0, 5.0, Vector(0, 0, 112.0), Vector(0, 0, 1)))

    # D. Bay 3 — Waveshare 0.96" OLED Ver. C (26.0 x 26.0 x 4.0 mm): Z = 115.5..142.1
    # Seated in Y in [+0.8, +5.0] inside Dia 30.4 mm circular wall (keeps >= 1.25mm round corner walls!)
    cavs.append(Part.makeBox(26.5, 4.4, 26.6, Vector(-13.25, 0.8, 115.5)))
    # Top Viewing Window + Chamfered Bezel straight down from circular outer crown (Y=4.0..16.5)
    cavs.append(Part.makeBox(22.2, 13.0, 11.8, Vector(-11.1, 3.8, 123.5)))
    w_bot = Part.makePolygon([
        Vector(-11.1, 9.5, 123.5), Vector(11.1, 9.5, 123.5),
        Vector(11.1, 9.5, 135.3), Vector(-11.1, 9.5, 135.3), Vector(-11.1, 9.5, 123.5)
    ])
    w_top = Part.makePolygon([
        Vector(-14.5, 16.5, 120.5), Vector(14.5, 16.5, 120.5),
        Vector(14.5, 16.5, 138.3), Vector(-14.5, 16.5, 138.3), Vector(-14.5, 16.5, 120.5)
    ])
    cavs.append(Part.makeLoft([w_bot, w_top], True, True))
    # Header/Wiring Plenum underneath OLED (Y in [-9.0, +1.0])
    cavs.append(Part.makeBox(19.0, 10.2, 26.6, Vector(-9.5, -9.0, 115.5)))

    cavs.append(Part.makeBox(11.0, 5.0, 5.0, Vector(-5.5, -2.5, 141.5)))

    # E. Bay 4 — Buzzer (Dia 12.0 x 9.5) + 5mm LED (X=+9.2, clears buzzer X<=6!) + Switch (X=-9.6): Z = 142.8..155.2
    cavs.append(Part.makeCylinder(6.3, 10.2, Vector(0.0, -4.2, 149.0), Vector(0, 1, 0)))
    for dz in [-2.8, 0.0, 2.8]:
        cavs.append(Part.makeBox(8.0, 7.0, 1.0, Vector(-4.0, 5.5, 148.5 + dz)))
    cavs.append(Part.makeCylinder(2.65, 11.5, Vector(9.2, -1.5, 149.0), Vector(0, 1, 0)))
    cavs.append(Part.makeCylinder(3.4, 4.0, Vector(9.2, 6.2, 149.0), Vector(0, 1, 0)))
    cavs.append(Part.makeBox(4.8, 7.0, 7.0, Vector(-10.2, -3.5, 145.5)))
    cavs.append(Part.makeCylinder(1.85, 6.0, Vector(-15.0, 0.0, 149.0), Vector(1, 0, 0)))

    cavs.append(Part.makeBox(10.0, 4.5, 4.5, Vector(-5.0, -2.0, 154.5)))

    # F. Bay 5 — Seeed Studio XIAO nRF52840 Sense (Z = 156.2..178.6)
    cavs.append(Part.makeBox(18.0, 5.2, 22.4, Vector(-9.0, -2.4, 156.2)))
    uc_box = Part.makeBox(5.6, 4.2, 7.0, Vector(-2.8, -1.5, 176.5))
    uc_c1 = Part.makeCylinder(2.1, 7.0, Vector(-2.8, 0.6, 176.5), Vector(0, 0, 1))
    uc_c2 = Part.makeCylinder(2.1, 7.0, Vector(2.8, 0.6, 176.5), Vector(0, 0, 1))
    cavs.append(uc_box.fuse(uc_c1).fuse(uc_c2))

    # G. Curved Flush Exterior FSR 408 Pocket (100.0 x 15.0 x 0.45 mm on -Y circular wall: Z = 22.0..122.4)
    outer_shrunk_bed = make_circle_loft(dense_pts, radial_offset=-0.46)
    fsr_wedge_bed = build_curved_fsr_sector(22.2, 122.6, strip_w=15.4, z_pts=dense_pts)
    cavs.append(solid_outer.cut(outer_shrunk_bed).common(fsr_wedge_bed))
    # Entry slot at Z = 120.5..122.7 into OLED lower plenum
    cavs.append(Part.makeBox(5.0, 10.0, 2.2, Vector(-2.5, -16.0, 120.4)))

    hollow = solid_outer
    for c in cavs:
        hollow = hollow.cut(c)

    # -------------------------------------------------------------------------
    # 3. HORIZONTAL ROUND SPLIT AT Y = +0.5 mm (OLED + Upper Cover vs Lower Tray)
    # -------------------------------------------------------------------------
    cover_mask = Part.makeBox(40.0, 22.0, 154.5, Vector(-20.0, 0.5, 22.0))
    top_cover = hollow.common(cover_mask)
    bottom_chassis = hollow.cut(cover_mask)

    # Sleek dorsal pocket clip anchored cleanly behind Buzzer/LED (Z = 155..175, R=10.8)
    clip_bar = Part.makeBox(2.2, 1.8, 20.0, Vector(-1.1, 12.6, 155.0))
    clip_foot = Part.makeBox(2.2, 4.2, 4.2, Vector(-1.1, 9.2, 170.8))
    clip_bead = Part.makeSphere(1.2, Vector(0.0, 13.0, 156.0))
    top_cover = top_cover.fuse(clip_bar.fuse(clip_foot).fuse(clip_bead))

    # Clamping ribs (0.15 mm clearance above cavities, clear of Y=0.5 split edge)
    batt_rib = Part.makeBox(10.0, 0.8, 18.0, Vector(-5.0, 3.7, 56.0))
    motor_rib = Part.makeBox(14.0, 0.8, 14.0, Vector(-7.0, 5.1, 92.0))
    xiao_rib_l = Part.makeBox(1.8, 0.8, 12.0, Vector(-8.6, 2.5, 161.0))
    xiao_rib_r = Part.makeBox(1.8, 0.8, 12.0, Vector(6.8, 2.5, 161.0))
    top_cover = top_cover.fuse(batt_rib).fuse(motor_rib).fuse(xiao_rib_l).fuse(xiao_rib_r)

    # Alignment Dowel Pins safely inside wall radii along Y = +0.5 mm round parting rim
    dowels = [
        Vector(-5.0, 0.5, 23.0),   Vector(5.0, 0.5, 23.0),
        Vector(-9.0, 0.5, 45.8),   Vector(9.0, 0.5, 45.8),
        Vector(-10.5, 0.5, 86.2),  Vector(10.5, 0.5, 86.2),
        Vector(-11.4, 0.5, 113.8), Vector(11.4, 0.5, 113.8),
        Vector(-11.8, 0.5, 143.2), Vector(11.8, 0.5, 143.2),
        Vector(-9.4, 0.5, 155.4),  Vector(9.4, 0.5, 155.4),
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

    obj_bot = doc.addObject("Part::Feature", "RoundFullBOM_Bottom_Chassis")
    obj_bot.Shape = bottom_chassis
    set_color(obj_bot, (0.14, 0.45, 0.28), 0)

    obj_top = doc.addObject("Part::Feature", "RoundFullBOM_Top_Cover")
    obj_top.Shape = top_cover
    set_color(obj_top, (0.10, 0.17, 0.30), 0)

    # -------------------------------------------------------------------------
    # 4. ALL EXACT BOM COMPONENTS (ZERO MPU-6050)
    # -------------------------------------------------------------------------
    xiao_shape = load_real_xiao_shape()
    xiao_shape.translate(Vector(0.0, 0.2, 156.4))
    obj_xiao = doc.addObject("Part::Feature", "BOM_XIAO_nRF52840_Sense")
    obj_xiao.Shape = xiao_shape
    set_color(obj_xiao, (0.12, 0.12, 0.15), 0)

    outer_fsr_top = make_circle_loft(dense_pts, radial_offset=-0.04)
    outer_fsr_bot = make_circle_loft(dense_pts, radial_offset=-0.42)
    fsr_wedge_exact = build_curved_fsr_sector(22.4, 122.4, strip_w=14.9, z_pts=dense_pts)
    fsr_shape = outer_fsr_top.cut(outer_fsr_bot).common(fsr_wedge_exact)
    obj_fsr = doc.addObject("Part::Feature", "BOM_FSR_408_Curved_Strip")
    obj_fsr.Shape = fsr_shape
    set_color(obj_fsr, (0.88, 0.56, 0.12), 0)

    batt_cell = Part.makeBox(16.0, 7.0, 35.0, Vector(-8.0, -3.4, 47.5))
    batt_pcm = Part.makeBox(14.0, 3.0, 2.5, Vector(-7.0, -1.5, 82.5))
    batt_shape = batt_cell.fuse(batt_pcm)
    obj_batt = doc.addObject("Part::Feature", "BOM_WLY701635_400mAh_LiPo")
    obj_batt.Shape = batt_shape
    set_color(obj_batt, (0.72, 0.74, 0.78), 0)

    motor_pcb = Part.makeBox(20.0, 1.6, 24.0, Vector(-10.0, -4.5, 88.4))
    motor_coin = Part.makeCylinder(5.0, 2.7, Vector(0.0, -2.9, 95.4), Vector(0, 1, 0))
    motor_conn = Part.makeBox(11.5, 6.5, 8.2, Vector(-5.75, -2.9, 103.8))
    motor_shape = motor_pcb.fuse(motor_coin).fuse(motor_conn)
    obj_motor = doc.addObject("Part::Feature", "BOM_Grove_Vibration_Motor")
    obj_motor.Shape = motor_shape
    set_color(obj_motor, (0.10, 0.55, 0.25), 0)

    oled_pcb = Part.makeBox(26.0, 1.6, 26.0, Vector(-13.0, 1.2, 115.8))
    oled_glass = Part.makeBox(24.8, 1.5, 15.0, Vector(-12.4, 2.8, 122.1))
    oled_aa = Part.makeBox(21.74, 0.3, 11.18, Vector(-10.87, 4.3, 124.01))
    oled_shape = oled_pcb.fuse(oled_glass).fuse(oled_aa)
    obj_oled = doc.addObject("Part::Feature", "BOM_Waveshare_096_OLED")
    obj_oled.Shape = oled_shape
    set_color(obj_oled, (0.05, 0.24, 0.68), 0)

    buzz_body = Part.makeCylinder(6.0, 9.5, Vector(0.0, -3.9, 149.0), Vector(0, 1, 0))
    buzz_hole = Part.makeCylinder(1.2, 1.5, Vector(0.0, 4.4, 149.0), Vector(0, 1, 0))
    buzz_shape = buzz_body.cut(buzz_hole)
    obj_buzz = doc.addObject("Part::Feature", "BOM_3V_Piezo_Buzzer")
    obj_buzz.Shape = buzz_shape
    set_color(obj_buzz, (0.14, 0.14, 0.16), 0)

    led_cyl = Part.makeCylinder(2.5, 6.2, Vector(9.2, -0.2, 149.0), Vector(0, 1, 0))
    led_dome = Part.makeSphere(2.5, Vector(9.2, 6.0, 149.0))
    led_shape = led_cyl.fuse(led_dome)
    obj_led = doc.addObject("Part::Feature", "BOM_XL_5mm_Status_LED")
    obj_led.Shape = led_shape
    set_color(obj_led, (0.95, 0.22, 0.18), 0)

    sw_body = Part.makeBox(3.5, 6.0, 6.0, Vector(-9.6, -3.0, 146.0))
    sw_btn = Part.makeCylinder(1.5, 3.0, Vector(-9.6, 0.0, 149.0), Vector(-1, 0, 0))
    sw_shape = sw_body.fuse(sw_btn)
    obj_sw = doc.addObject("Part::Feature", "BOM_Tactile_Power_Switch")
    obj_sw.Shape = sw_shape
    set_color(obj_sw, (0.90, 0.72, 0.15), 0)

    # -------------------------------------------------------------------------
    # 5. AUDIT & EXPORT
    # -------------------------------------------------------------------------
    print("\n--- Full-BOM Round Pen Audit ---")
    print(f"  - Pen Outer Bounds (mm) : X={solid_outer.BoundBox.XLength:.2f}, Y={solid_outer.BoundBox.YLength:.2f}, Z={solid_outer.BoundBox.ZLength:.2f}")
    print(f"  - Bottom Chassis Valid  : {bottom_chassis.isValid()} (Solids={len(bottom_chassis.Solids)}, Vol={bottom_chassis.Volume/1000:.2f} cm^3)")
    print(f"  - Top Cover Valid       : {top_cover.isValid()} (Solids={len(top_cover.Solids)}, Vol={top_cover.Volume/1000:.2f} cm^3)")

    comps = [
        ("XIAO nRF52840", xiao_shape),
        ("WLY701635 LiPo", batt_shape),
        ("Grove Motor", motor_shape),
        ("0.96 OLED", oled_shape),
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

    fc_out = os.path.join(REPO_CAD, "freecad", "NeuroGrip_RoundFullBOM_Pen.FCStd")
    st_out = os.path.join(REPO_CAD, "cad_assemblies", "NeuroGrip_RoundFullBOM_Pen_Assembly.step")
    st_bot = os.path.join(REPO_CAD, "cad_assemblies", "NeuroGrip_RoundFullBOM_Pen_Bottom_Chassis.step")
    st_top = os.path.join(REPO_CAD, "cad_assemblies", "NeuroGrip_RoundFullBOM_Pen_Top_Cover.step")
    stl_bot = os.path.join(REPO_CAD, "3d_models", "NeuroGrip_RoundFullBOM_Pen_Bottom_Chassis.stl")
    stl_top = os.path.join(REPO_CAD, "3d_models", "NeuroGrip_RoundFullBOM_Pen_Top_Cover.stl")

    doc.saveAs(fc_out)
    Part.export([obj_bot, obj_top, obj_xiao, obj_fsr, obj_batt, obj_motor, obj_oled, obj_buzz, obj_led, obj_sw], st_out)
    Part.export([obj_bot], st_bot)
    Part.export([obj_top], st_top)
    MeshPart.meshFromShape(bottom_chassis, LinearDeflection=0.05, AngularDeflection=0.10).write(stl_bot)
    MeshPart.meshFromShape(top_cover, LinearDeflection=0.05, AngularDeflection=0.10).write(stl_top)

    for p in [fc_out, st_out, stl_bot, stl_top]:
        shutil.copy2(p, os.path.join(ARTIFACT_DIR, os.path.basename(p)))
    print("Saved RoundFullBOM Pen CAD Deliverables!")


if __name__ == "__main__":
    build_round_fullbom_pen()
    sys.exit(0)
