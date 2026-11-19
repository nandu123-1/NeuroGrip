#!/usr/bin/env python3
"""
================================================================================
NEUROGRIP 3.5" TOUCH DIGITIZER & ESP32 ENCLOSURE GENERATOR FOR FREECAD
================================================================================
Hardware Target:
  - Display: Waveshare 3.5" (F) Capacitive Touch LCD (ST7796S + GT911)
             Module: 92.44 mm x 61.00 mm x 8.5 mm (Active: 73.84 x 49.36 mm)
  - Controller: ESP32 DevKit V1 (30-pin, 51.8 mm x 28.5 mm x 12.0 mm)
  - Power: Direct USB cable connection (no battery, zero battery maintenance)
  - Assembly: 4x M3 screws (20mm) + M3 heat-set threaded inserts or self-tapping

Generated Outputs:
  - NeuroGrip_3.5_Enclosure.FCStd (Native FreeCAD project)
  - NeuroGrip_Enclosure_Bottom_Base.step / .stl (3D Printable Base)
  - NeuroGrip_Enclosure_Top_Bezel.step / .stl (3D Printable Bezel)
  - NeuroGrip_Full_Assembly.step / .stl (Full Multi-Body Assembly)
================================================================================
"""

import sys
import os
import math
import FreeCAD as App
import Part
import MeshPart

def build_neurogrip_enclosure(output_dir="/home/sunraku"):
    print("[1/5] Initializing FreeCAD Parametric Document...")
    doc = App.newDocument("NeuroGrip_3_5_Enclosure")

    # -------------------------------------------------------------
    # Mechanical Tolerances & Dimensions (in mm) - Adjusted for Real Hardware
    # -------------------------------------------------------------
    ENC_W = 118.0          # Exterior Width (X)
    ENC_D = 88.0           # Exterior Depth (Y)
    BASE_H = 30.0          # Base Height (Z: 0 -> 30) - Increased from 18 to 30mm for DuPont clearance!
    BEZEL_H = 4.0          # Top Bezel Height (Z: 30 -> 34)
    TOTAL_H = BASE_H + BEZEL_H # 34.0 mm total assembly height
    CORNER_R = 5.0         # Ergonomic corner radius

    WALL_T = 2.5           # Heavy-duty 3D print wall thickness
    FLOOR_T = 2.4          # Rigid base floor thickness

    # Waveshare 3.5" (F) Display Specs
    DISP_PCB_W = 92.44
    DISP_PCB_D = 61.00
    DISP_PCB_H = 1.60
    DISP_GLASS_W = 85.00
    DISP_GLASS_D = 56.50
    DISP_GLASS_H = 2.20
    DISP_ACTIVE_W = 73.84
    DISP_ACTIVE_D = 49.36
    DISP_REST_Z = 24.0     # Height where display PCB rests (21.6 mm clear space below!)

    # ESP32 DevKit V1 & Real Hardware Stack
    ESP_PCB_W = 51.8
    ESP_PCB_D = 28.5
    ESP_PCB_H = 1.6
    STANDOFF_GAP = 10.0    # 10mm metal standoff between display PCB and lower plane
    ESP_Z = DISP_REST_Z - STANDOFF_GAP - ESP_PCB_H # ~12.4 mm

    # M3 Fasteners & Bosses
    SCREW_X = 50.0
    SCREW_Y = 35.0
    BOSS_OD = 7.2
    BOSS_ID = 2.8          # Core hole for M3 heat-set insert or tap
    SCREW_CLEAR_D = 3.4    # M3 through hole
    SCREW_CBORE_D = 6.4    # M3 socket head counterbore
    SCREW_CBORE_H = 2.2

    # USB Power Port Cutout (Flipped to RIGHT Wall as in real hardware!)
    USB_W = 14.0           # Extra wide for easy USB cable boot insertion
    USB_H = 8.5            # Cable boot height
    USB_Z = DISP_REST_Z - 5.5 # Directly underneath display PCB right edge

    # -------------------------------------------------------------
    # [2/5] Construct Bottom Base Enclosure
    # -------------------------------------------------------------
    print("[2/5] Generating Bottom Base Chassis...")
    base_outer = Part.makeBox(ENC_W, ENC_D, BASE_H, App.Vector(-ENC_W/2, -ENC_D/2, 0))

    # Fillet vertical corners
    v_edges = []
    for e in base_outer.Edges:
        v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
        if abs(v1.x - v2.x) < 1e-3 and abs(v1.y - v2.y) < 1e-3 and abs(v1.z - v2.z) > 1e-3:
            v_edges.append(e)
    base_outer = base_outer.makeFillet(CORNER_R, v_edges)

    # Hollow internal cavity
    cavity_w = ENC_W - 2 * WALL_T
    cavity_d = ENC_D - 2 * WALL_T
    cavity_h = BASE_H - FLOOR_T + 2.0
    cavity_box = Part.makeBox(cavity_w, cavity_d, cavity_h, App.Vector(-cavity_w/2, -cavity_d/2, FLOOR_T))

    c_edges = []
    for e in cavity_box.Edges:
        v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
        if abs(v1.x - v2.x) < 1e-3 and abs(v1.y - v2.y) < 1e-3 and abs(v1.z - v2.z) > 1e-3:
            c_edges.append(e)
    cavity_box = cavity_box.makeFillet(CORNER_R - WALL_T, c_edges)

    base = base_outer.cut(cavity_box)

    # Fuse 4 corner M3 screw bosses
    bosses = []
    for sx in [-SCREW_X, SCREW_X]:
        for sy in [-SCREW_Y, SCREW_Y]:
            b = Part.makeCylinder(BOSS_OD/2, BASE_H - FLOOR_T, App.Vector(sx, sy, FLOOR_T), App.Vector(0,0,1))
            bosses.append(b)

    for b in bosses:
        base = base.fuse(b)

    # Fuse 4 Display Support Corner Shelves at Z = DISP_REST_Z (12.0 mm)
    shelf_w = 12.0
    shelf_d = 10.0
    shelf_h = DISP_REST_Z - FLOOR_T
    for sx, sy in [(-DISP_PCB_W/2, -DISP_PCB_D/2), (DISP_PCB_W/2 - shelf_w, -DISP_PCB_D/2),
                  (-DISP_PCB_W/2, DISP_PCB_D/2 - shelf_d), (DISP_PCB_W/2 - shelf_w, DISP_PCB_D/2 - shelf_d)]:
        sh = Part.makeBox(shelf_w, shelf_d, shelf_h, App.Vector(sx, sy, FLOOR_T))
        base = base.fuse(sh)

    # Fuse 4 ESP32 Standoffs with alignment pips
    esp_hole_dx = 44.0 / 2.0
    esp_hole_dy = 23.0 / 2.0
    for ex in [-esp_hole_dx, esp_hole_dx]:
        for ey in [-esp_hole_dy, esp_hole_dy]:
            post = Part.makeCylinder(3.0, 3.0, App.Vector(ex, ey, FLOOR_T), App.Vector(0,0,1))
            pip = Part.makeCylinder(1.2, 1.5, App.Vector(ex, ey, FLOOR_T + 3.0), App.Vector(0,0,1))
            base = base.fuse(post.fuse(pip))

    # Cut M3 core holes in the bosses
    for sx in [-SCREW_X, SCREW_X]:
        for sy in [-SCREW_Y, SCREW_Y]:
            hole = Part.makeCylinder(BOSS_ID/2, 18.0, App.Vector(sx, sy, BASE_H - 16.0), App.Vector(0,0,1))
            base = base.cut(hole)

    # Cut USB Power Port on RIGHT Wall (X = +ENC_W/2) matching real hardware!
    usb_cut = Part.makeBox(WALL_T + 6.0, USB_W, USB_H, App.Vector(ENC_W/2 - WALL_T - 2.0, -USB_W/2, USB_Z - USB_H/2))
    base = base.cut(usb_cut)

    # Cut passive thermal ventilation slots under ESP32
    for i in range(-2, 3):
        slot = Part.makeBox(22.0, 2.0, FLOOR_T + 2.0, App.Vector(-11.0, i * 4.5 - 1.0, -1.0))
        base = base.cut(slot)

    # Cut 4x non-slip rubber foot recesses on bottom face
    for fx in [-48.0, 48.0]:
        for fy in [-33.0, 33.0]:
            foot = Part.makeCylinder(4.25, 1.2, App.Vector(fx, fy, -0.2), App.Vector(0,0,1))
            base = base.cut(foot)

    # -------------------------------------------------------------
    # [3/5] Construct Top Bezel (Faceplate)
    # -------------------------------------------------------------
    print("[3/5] Generating Top Bezel Faceplate...")
    bezel_outer = Part.makeBox(ENC_W, ENC_D, BEZEL_H, App.Vector(-ENC_W/2, -ENC_D/2, BASE_H))

    bv_edges = []
    for e in bezel_outer.Edges:
        v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
        if abs(v1.x - v2.x) < 1e-3 and abs(v1.y - v2.y) < 1e-3 and abs(v1.z - v2.z) > 1e-3:
            bv_edges.append(e)
    bezel_outer = bezel_outer.makeFillet(CORNER_R, bv_edges)

    # Active display touch window aperture
    screen_cut_w = 75.5
    screen_cut_d = 50.5
    screen_cutter = Part.makeBox(screen_cut_w, screen_cut_d, BEZEL_H + 4.0, 
                                 App.Vector(-screen_cut_w/2, -screen_cut_d/2, BASE_H - 2.0))
    bezel = bezel_outer.cut(screen_cutter)

    # Underside stepped retention pocket for display perimeter
    pocket_w = DISP_PCB_W + 1.0
    pocket_d = DISP_PCB_D + 1.0
    disp_pocket = Part.makeBox(pocket_w, pocket_d, 2.2, App.Vector(-pocket_w/2, -pocket_d/2, BASE_H - 0.2))
    bezel = bezel.cut(disp_pocket)

    # 4x Screw Counterbore Holes in Bezel
    for sx in [-SCREW_X, SCREW_X]:
        for sy in [-SCREW_Y, SCREW_Y]:
            through_h = Part.makeCylinder(SCREW_CLEAR_D/2, BEZEL_H + 4.0, App.Vector(sx, sy, BASE_H - 2.0), App.Vector(0,0,1))
            cbore_h = Part.makeCylinder(SCREW_CBORE_D/2, SCREW_CBORE_H + 1.0, App.Vector(sx, sy, TOTAL_H - SCREW_CBORE_H), App.Vector(0,0,1))
            bezel = bezel.cut(through_h).cut(cbore_h)

    # -------------------------------------------------------------
    # [4/5] Construct Hardware Mockups (Display, ESP32 & Real Standoffs)
    # -------------------------------------------------------------
    print("[4/5] Generating Hardware Virtual Mocks with Real-World Standoffs...")
    disp_pcb = Part.makeBox(DISP_PCB_W, DISP_PCB_D, DISP_PCB_H, App.Vector(-DISP_PCB_W/2, -DISP_PCB_D/2, DISP_REST_Z))
    disp_glass = Part.makeBox(DISP_GLASS_W, DISP_GLASS_D, DISP_GLASS_H, App.Vector(-DISP_GLASS_W/2, -DISP_GLASS_D/2, DISP_REST_Z + DISP_PCB_H))
    disp_active = Part.makeBox(DISP_ACTIVE_W, DISP_ACTIVE_D, 0.2, App.Vector(-DISP_ACTIVE_W/2, -DISP_ACTIVE_D/2, DISP_REST_Z + DISP_PCB_H + DISP_GLASS_H))
    disp_mock = disp_pcb.fuse(disp_glass).fuse(disp_active)

    # 4 Metal standoffs matching photo
    for sx, sy in [(-29.0, -24.5), (29.0, -24.5), (-29.0, 24.5), (29.0, 24.5)]:
        so = Part.makeCylinder(2.5, STANDOFF_GAP, App.Vector(sx, sy, DISP_REST_Z - STANDOFF_GAP), App.Vector(0,0,1))
        disp_mock = disp_mock.fuse(so)

    # ESP32 positioned under display with USB pointing RIGHT (+X)
    esp_pcb = Part.makeBox(ESP_PCB_W, ESP_PCB_D, ESP_PCB_H, App.Vector(-ESP_PCB_W/2, -ESP_PCB_D/2, ESP_Z))
    esp_can = Part.makeBox(18.0, 25.5, 3.0, App.Vector(-10.0, -12.75, ESP_Z + ESP_PCB_H))
    esp_usb = Part.makeBox(7.5, 6.0, 3.0, App.Vector(ESP_PCB_W/2 - 5.5, -3.0, ESP_Z + 0.5))
    esp_mock = esp_pcb.fuse(esp_can).fuse(esp_usb)

    # DuPont jumper connector block mock underneath showing 14mm vertical clearance
    dupont_block = Part.makeBox(28.0, 15.0, 12.0, App.Vector(-24.0, -7.5, ESP_Z - 12.0))
    esp_mock = esp_mock.fuse(dupont_block)

    # Add objects to FreeCAD Document tree
    obj_base = doc.addObject("Part::Feature", "Bottom_Base_Enclosure")
    obj_base.Shape = base

    obj_bezel = doc.addObject("Part::Feature", "Top_Bezel_Cover")
    obj_bezel.Shape = bezel

    obj_disp = doc.addObject("Part::Feature", "Waveshare_3_5_Display_Mock")
    obj_disp.Shape = disp_mock

    obj_esp = doc.addObject("Part::Feature", "ESP32_DevKit_V1_Mock")
    obj_esp.Shape = esp_mock

    doc.recompute()

    # -------------------------------------------------------------
    # [5/5] Export All CAD & Mesh Formats
    # -------------------------------------------------------------
    print("[5/5] Exporting FreeCAD .FCStd, STEP, and STL formats...")
    fcstd_file = os.path.join(output_dir, "NeuroGrip_3.5_Enclosure.FCStd")
    doc.saveAs(fcstd_file)

    Part.export([obj_base], os.path.join(output_dir, "NeuroGrip_Enclosure_Bottom_Base.step"))
    Part.export([obj_bezel], os.path.join(output_dir, "NeuroGrip_Enclosure_Top_Bezel.step"))
    Part.export([obj_base, obj_bezel, obj_disp, obj_esp], os.path.join(output_dir, "NeuroGrip_Full_Assembly.step"))

    m_base = MeshPart.meshFromShape(base, LinearDeflection=0.08, AngularDeflection=0.15)
    m_base.write(os.path.join(output_dir, "NeuroGrip_Enclosure_Bottom_Base.stl"))

    m_bezel = MeshPart.meshFromShape(bezel, LinearDeflection=0.08, AngularDeflection=0.15)
    m_bezel.write(os.path.join(output_dir, "NeuroGrip_Enclosure_Top_Bezel.stl"))

    assembly_shape = base.fuse(bezel)
    m_assembly = MeshPart.meshFromShape(assembly_shape, LinearDeflection=0.08, AngularDeflection=0.15)
    m_assembly.write(os.path.join(output_dir, "NeuroGrip_Enclosure_Assembly.stl"))

    print("SUCCESS: All models and manufacturing assets exported cleanly!")

if __name__ == "__main__":
    build_neurogrip_enclosure()
