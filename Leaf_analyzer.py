import numpy as np
import cv2 as cv
from cv2 import aruco
from matplotlib import pyplot as plt
import glob
import os
import hashlib
import csv
from PIL import Image
import argparse
from datetime import datetime
import sys

# --- RUNTIME ARGUMENTS ---
parser = argparse.ArgumentParser(description="Leaf Morphometrics Analysis with Auto-Calibration & Standalone Targets")
parser.add_argument('--generate-targets', action='store_true', help="Generate printable ChArUco board, background grid, and standalone scale strips, then exit")
parser.add_argument('--paper-size', choices=['letter', 'a4', 'arch_d'], default='letter', 
                    help="Target paper size: 'letter'/'a4' for HP LaserJet M479fdw, 'arch_d' (24x36 in) for Canon TA-30")
parser.add_argument('--petiole', action='store_true', help="Enable advanced automatic petiole tracking")
parser.add_argument('--manual-petiole', action='store_true', help="Enable manual point selection for petiole tracking")
parser.add_argument('--show', action='store_true', help="Display annotated images in popup windows")
parser.add_argument('--new-csv', action='store_true', help="Generate a new timestamped CSV instead of overwriting default")
args = parser.parse_args()

# --- CONFIGURATION & CALIBRATION SETUP ---
SQUARES_X = 7
SQUARES_Y = 5
SQUARE_LENGTH_MM = 30.0 
MARKER_LENGTH_MM = 22.0

dictionary = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
board = aruco.CharucoBoard((SQUARES_X, SQUARES_Y), SQUARE_LENGTH_MM, MARKER_LENGTH_MM, dictionary)
detectorParams = aruco.DetectorParameters()
detector = aruco.ArucoDetector(dictionary, detectorParams)

Image.MAX_IMAGE_PIXELS = None 

# =====================================================================
# FEATURE: TARGET & STANDALONE SCALE GENERATION
# =====================================================================
if args.generate_targets:
    print(f"--- Generating Calibration Targets & Standalone Scales [{args.paper_size.upper()}] ---")
    
    DPI = 300
    px_per_mm = DPI / 25.4
    px_per_cm = DPI / 2.54
    
    if args.paper_size == 'letter':
        page_w_in, page_h_in = 8.5, 11.0
    elif args.paper_size == 'a4':
        page_w_in, page_h_in = 8.27, 11.69
    elif args.paper_size == 'arch_d': 
        page_w_in, page_h_in = 24.0, 36.0

    page_w_px = int(page_w_in * DPI)
    page_h_px = int(page_h_in * DPI)
    margin_px = int(0.35 * DPI) # HP LaserJet unprintable safety margin
    
    # -----------------------------------------------------------------
    # 1. CHARUCO BOARD
    # -----------------------------------------------------------------
    board_w_px = page_w_px - (2 * margin_px)
    board_h_px = page_h_px - (2 * margin_px) - int(30 * px_per_mm)
    
    charuco_render = board.generateImage((board_w_px, board_h_px), marginSize=0)
    charuco_bgr = cv.cvtColor(charuco_render, cv.COLOR_GRAY2BGR)
    
    canvas_board = np.ones((page_h_px, page_w_px, 3), dtype=np.uint8) * 255
    y_offset = margin_px + int(25 * px_per_mm)
    canvas_board[y_offset:y_offset + board_h_px, margin_px:margin_px + board_w_px] = charuco_bgr
    
    ruler_start_x = margin_px
    ruler_y = margin_px + int(10 * px_per_mm)
    ruler_len_100mm_px = int(100.0 * px_per_mm)
    
    cv.line(canvas_board, (ruler_start_x, ruler_y), (ruler_start_x + ruler_len_100mm_px, ruler_y), (0, 0, 0), 4)
    cv.line(canvas_board, (ruler_start_x, ruler_y - 15), (ruler_start_x, ruler_y + 15), (0, 0, 0), 4)
    cv.line(canvas_board, (ruler_start_x + ruler_len_100mm_px, ruler_y - 15), (ruler_start_x + ruler_len_100mm_px, ruler_y + 15), (0, 0, 0), 4)
    
    cv.putText(canvas_board, f"CHARUCO BOARD [{args.paper_size.upper()}] - CALIPER VERIFICATION: 100.0 mm", 
               (ruler_start_x, ruler_y - 25), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    cv.imwrite(f"charuco_board_{args.paper_size}.png", canvas_board)
    print(f"[SAVED] charuco_board_{args.paper_size}.png")

    # -----------------------------------------------------------------
    # 2. 2-AXIS DROP-OUT GRID BACKGROUND
    # -----------------------------------------------------------------
    canvas_grid = np.ones((page_h_px, page_w_px, 3), dtype=np.uint8) * 255
    color_minor, color_major, color_text = (255, 220, 180), (230, 170, 100), (180, 120, 50)
    
    grid_x_start = margin_px
    grid_y_start = margin_px + int(25 * px_per_mm)
    grid_w_px = page_w_px - (2 * margin_px)
    grid_h_px = page_h_px - grid_y_start - margin_px
    
    max_cm_x = int(grid_w_px / px_per_cm)
    max_cm_y = int(grid_h_px / px_per_cm)

    for i in range(max_cm_x * 10 + 1):
        x_pos = grid_x_start + int(i * px_per_mm)
        if x_pos > (grid_x_start + grid_w_px): break
        thickness = 4 if i % 10 == 0 else (3 if i % 5 == 0 else 2)
        cv.line(canvas_grid, (x_pos, grid_y_start), (x_pos, grid_y_start + grid_h_px), color_major if i % 5 == 0 else color_minor, thickness)

    for i in range(max_cm_y * 10 + 1):
        y_pos = grid_y_start + int(i * px_per_mm)
        if y_pos > (grid_y_start + grid_h_px): break
        thickness = 4 if i % 10 == 0 else (3 if i % 5 == 0 else 2)
        cv.line(canvas_grid, (grid_x_start, y_pos), (grid_x_start + grid_w_px, y_pos), color_major if i % 5 == 0 else color_minor, thickness)

    for i in range(1, max_cm_x + 1):
        cv.putText(canvas_grid, f"{i}", (grid_x_start + int(i * px_per_cm) - 12, grid_y_start - 10), cv.FONT_HERSHEY_SIMPLEX, 0.6, color_text, 2)
    for i in range(1, max_cm_y + 1):
        cv.putText(canvas_grid, f"{i}", (grid_x_start - 35, grid_y_start + int(i * px_per_cm) + 8), cv.FONT_HERSHEY_SIMPLEX, 0.6, color_text, 2)

    cv.line(canvas_grid, (ruler_start_x, ruler_y), (ruler_start_x + ruler_len_100mm_px, ruler_y), (0, 0, 0), 4)
    cv.line(canvas_grid, (ruler_start_x, ruler_y - 15), (ruler_start_x, ruler_y + 15), (0, 0, 0), 4)
    cv.line(canvas_grid, (ruler_start_x + ruler_len_100mm_px, ruler_y - 15), (ruler_start_x + ruler_len_100mm_px, ruler_y + 15), (0, 0, 0), 4)
    cv.putText(canvas_grid, f"2-AXIS GRID [{args.paper_size.upper()}] - CALIPER VERIFICATION: 100.0 mm", 
               (ruler_start_x, ruler_y - 25), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    cv.imwrite(f"2_axis_scale_background_{args.paper_size}.png", canvas_grid)
    print(f"[SAVED] 2_axis_scale_background_{args.paper_size}.png")

    # -----------------------------------------------------------------
    # 3. INDEPENDENT CUT-OUT SCALE STRIPS & CARDS
    # -----------------------------------------------------------------
    canvas_strips = np.ones((page_h_px, page_w_px, 3), dtype=np.uint8) * 255
    
    # Page Header
    cv.putText(canvas_strips, f"CUT-OUT STANDALONE SCALE CARDS [{args.paper_size.upper()}] - VERIFY WITH CALIPERS PRIOR TO USE", 
               (margin_px, margin_px + 30), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    # Function to draw a 150mm linear scale card
    def draw_scale_card(img, start_x, start_y):
        card_w_mm, card_h_mm = 170, 40
        w_px, h_px = int(card_w_mm * px_per_mm), int(card_h_mm * px_per_mm)
        
        # Dashed border for cutting out
        cv.rectangle(img, (start_x, start_y), (start_x + w_px, start_y + h_px), (180, 180, 180), 2)
        
        ruler_x = start_x + int(10 * px_per_mm)
        base_y = start_y + int(25 * px_per_mm)
        
        # Main baseline (150 mm long)
        cv.line(img, (ruler_x, base_y), (ruler_x + int(150 * px_per_mm), base_y), (0, 0, 0), 3)
        
        # Ticks & labels
        for mm in range(151):
            tick_x = ruler_x + int(mm * px_per_mm)
            if mm % 10 == 0:
                cv.line(img, (tick_x, base_y), (tick_x, base_y - int(12 * px_per_mm)), (0, 0, 0), 3)
                if mm > 0 and mm < 150:
                    cv.putText(img, f"{mm//10}", (tick_x - 10, base_y - int(15 * px_per_mm)), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            elif mm % 5 == 0:
                cv.line(img, (tick_x, base_y), (tick_x, base_y - int(8 * px_per_mm)), (0, 0, 0), 2)
            else:
                cv.line(img, (tick_x, base_y), (tick_x, base_y - int(5 * px_per_mm)), (0, 0, 0), 1)
                
        cv.putText(img, "SCALE (cm)", (ruler_x, base_y + int(10 * px_per_mm)), cv.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv.putText(img, "100.0mm Verification Line", (ruler_x + int(60 * px_per_mm), base_y + int(10 * px_per_mm)), cv.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # Function to draw a 50mm 2-Axis Crosshair Scale Card
    def draw_crosshair_card(img, start_x, start_y):
        card_w_mm, card_h_mm = 80, 80
        w_px, h_px = int(card_w_mm * px_per_mm), int(card_h_mm * px_per_mm)
        cv.rectangle(img, (start_x, start_y), (start_x + w_px, start_y + h_px), (180, 180, 180), 2)
        
        cx, cy = start_x + w_px // 2, start_y + h_px // 2
        arm_px = int(25 * px_per_mm)
        
        cv.line(img, (cx - arm_px, cy), (cx + arm_px, cy), (0, 0, 0), 3)
        cv.line(img, (cx, cy - arm_px), (cx, cy + arm_px), (0, 0, 0), 3)
        
        for mm in range(-25, 26, 5):
            thickness = 2 if mm % 10 == 0 else 1
            length = int(6 * px_per_mm) if mm % 10 == 0 else int(3 * px_per_mm)
            
            # X Ticks
            tx = cx + int(mm * px_per_mm)
            cv.line(img, (tx, cy - length), (tx, cy + length), (0, 0, 0), thickness)
            
            # Y Ticks
            ty = cy + int(mm * px_per_mm)
            cv.line(img, (cx - length, ty), (cx + length, ty), (0, 0, 0), thickness)

    # Tile multiple scale cards onto the sheet
    y_cursor = margin_px + int(20 * px_per_mm)
    card_spacing_y = int(48 * px_per_mm)
    
    # Add 4 Linear Cards
    for k in range(4):
        if y_cursor + card_spacing_y < page_h_px - margin_px:
            draw_scale_card(canvas_strips, margin_px, y_cursor)
            y_cursor += card_spacing_y

    # Add 2 Crosshair Cards side-by-side at the bottom
    if y_cursor + int(85 * px_per_mm) < page_h_px - margin_px:
        draw_crosshair_card(canvas_strips, margin_px, y_cursor)
        draw_crosshair_card(canvas_strips, margin_px + int(85 * px_per_mm), y_cursor)

    cv.imwrite(f"standalone_scale_strips_{args.paper_size}.png", canvas_strips)
    print(f"[SAVED] standalone_scale_strips_{args.paper_size}.png")
    
    print("\nTarget generation complete! Print PNGs at 100% scale (No 'Fit to Page'). Exiting.")
    sys.exit(0)

# =====================================================================
# MAIN PROCESSING WORKFLOW
# =====================================================================
scan_folder = 'Scans'
annotated_folder = 'Annotated Scans'
os.makedirs(scan_folder, exist_ok=True)
os.makedirs(annotated_folder, exist_ok=True)

scan_files = glob.glob(os.path.join(scan_folder, '*.*'))
valid_files = [f for f in scan_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif'))]

if not valid_files:
    print(f"Please place your leaf images and ChArUco calibration image(s) into the '{scan_folder}' folder.")
    exit(1)

# --- PASS 1: GEOMETRIC CALIBRATION SEARCH ---
print("\n--- Pass 1: Searching for ChArUco Calibration Target ---")
all_charuco_corners, all_charuco_ids = [], []
image_size, calib_files, leaf_files = None, [], []

for fname in valid_files:
    img = cv.imread(fname)
    if img is None: continue
    
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)
    
    if ids is not None and len(ids) >= 4:
        res = aruco.interpolateCornersCharuco(corners, ids, gray, board)
        charuco_corners = res[1] if len(res) > 1 else None
        charuco_ids = res[2] if len(res) > 2 else None
        
        if charuco_corners is not None and len(charuco_corners) > 3:
            all_charuco_corners.append(charuco_corners)
            all_charuco_ids.append(charuco_ids)
            calib_files.append(fname)
            if image_size is None:
                image_size = gray.shape[::-1]
            print(f"  -> Detected Calibration Board in: {os.path.basename(fname)}")
    else:
        leaf_files.append(fname)

mtx, dist, dynamic_px_per_cm = None, None, None

if calib_files:
    print(f"\nComputing Geometric Lens Calibration from {len(calib_files)} target image(s)...")
    ret, mtx, dist, rvecs, tvecs = aruco.calibrateCameraCharuco(
        charucoCorners=all_charuco_corners, charucoIds=all_charuco_ids, board=board,
        imageSize=image_size, cameraMatrix=None, distCoeffs=None
    )
    print("  -> Geometric distortion map built successfully.")
    
    img = cv.imread(calib_files[0])
    h_img, w_img = img.shape[:2]
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w_img, h_img), 0, (w_img, h_img))
    undistorted_calib = cv.undistort(img, mtx, dist, None, newcameramtx)
    
    gray_undistorted = cv.cvtColor(undistorted_calib, cv.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray_undistorted)
    res = aruco.interpolateCornersCharuco(corners, ids, gray_undistorted, board)
    c_corners = res[1] if len(res) > 1 else None
    
    if c_corners is not None and len(c_corners) >= 2:
        pixel_distance = np.linalg.norm(c_corners[0][0] - c_corners[1][0])
        dynamic_px_per_cm = (pixel_distance / SQUARE_LENGTH_MM) * 10.0
        print(f"  -> Dynamic Scale Established: {dynamic_px_per_cm:.2f} pixels/cm")
else:
    print("\n[WARNING] No ChArUco board found. Processing raw images.")

# --- MANUAL PETIOLE SELECTOR ---
def select_manual_petiole(img, cnt, sf):
    print("  -> Opening Manual Petiole Selector...")
    x, y, w, h = cv.boundingRect(cnt)
    pad = int(50 * sf)
    crop = img[max(0, y-pad):min(img.shape[0], y+h+pad), max(0, x-pad):min(img.shape[1], x+w+pad)].copy()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(cv.cvtColor(crop, cv.COLOR_BGR2RGB))
    ax.set_title("1st Click: Petiole Tip | Last Click: Flare Point\n(L-Click: Add | R-Click: Undo | ENTER: Confirm)", fontsize=10, color='red')
    plt.axis('off')
    
    pts = plt.ginput(n=-1, timeout=0, show_clicks=True, mouse_add=1, mouse_pop=3)
    plt.close(fig)
    if not pts or len(pts) < 2: return None
    return [(int(p[0] + max(0, x-pad)), int(p[1] + max(0, y-pad))) for p in pts]

# --- PASS 2: LEAF SEGMENTATION & MORPHOMETRICS ---
csv_records, seen_hashes = [], set()

for Source in leaf_files:
    filename = os.path.basename(Source)
    img = cv.imread(Source)
    if img is None: continue

    if mtx is not None and dist is not None:
        h_img, w_img = img.shape[:2]
        newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w_img, h_img), 0, (w_img, h_img))
        img = cv.undistort(img, mtx, dist, None, newcameramtx)
        x_roi, y_roi, w_roi, h_roi = roi
        if w_roi > 0 and h_roi > 0:
            img = img[y_roi:y_roi+h_roi, x_roi:x_roi+w_roi]
    
    if dynamic_px_per_cm:
        pixels_per_cm = dynamic_px_per_cm
        dpi = int(pixels_per_cm * 2.54) 
    else:
        dpi = 1200
        try:
            with Image.open(Source) as img_meta:
                if 'dpi' in img_meta.info: dpi = round(img_meta.info['dpi'][0])
        except Exception: pass
        pixels_per_cm = dpi / 2.54
        
    pixels_per_cm2 = pixels_per_cm ** 2
    output_img = img.copy()
    
    sf = max(img.shape[0], img.shape[1]) / 2000.0
    contour_thickness = max(2, int(3 * sf))
    line_thickness = max(2, int(4 * sf))
    text_thickness_bold = max(2, int(2 * sf))
    text_thickness_thin = max(1, int(1 * sf))
    font_scale_id = 0.55 * sf
    font_scale_metrics = 0.38 * sf 

    # Masking out drop-out cyan lines / paper backgrounds
    lab = cv.cvtColor(img, cv.COLOR_BGR2LAB)
    l_channel = cv.split(lab)[0]
    _, mask_luminance = cv.threshold(l_channel, 185, 255, cv.THRESH_BINARY_INV)
    
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    v_channel = cv.split(hsv)[2]
    _, mask_value = cv.threshold(v_channel, 190, 255, cv.THRESH_BINARY_INV)
    
    combined_mask = cv.bitwise_or(mask_luminance, mask_value)
    kernel_clean = cv.getStructuringElement(cv.MORPH_ELLIPSE, (7, 7))
    mask_clean = cv.morphologyEx(combined_mask, cv.MORPH_OPEN, kernel_clean)
    mask_clean = cv.morphologyEx(mask_clean, cv.MORPH_CLOSE, kernel_clean)
    
    contours, _ = cv.findContours(mask_clean, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv.contourArea, reverse=True)
    min_area = (img.shape[0] * img.shape[1]) * 0.005 
    
    print(f"\n--- Processing Leaf: {filename} ({pixels_per_cm:.2f} px/cm) ---")
    
    for cnt in contours:
        area_px = cv.contourArea(cnt)
        if area_px < min_area: continue
            
        perimeter_px = cv.arcLength(cnt, True)
        pixel_edge_area_ratio = perimeter_px / area_px if area_px > 0 else 0
        
        M = cv.moments(cnt)
        cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else cv.boundingRect(cnt)[0] + cv.boundingRect(cnt)[2] // 2
        cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else cv.boundingRect(cnt)[1] + cv.boundingRect(cnt)[3] // 2
        com = np.array([cX, cY], dtype=np.float32)
        
        rect = cv.minAreaRect(cnt)
        rect_w, rect_h = rect[1]
        leaf_length_px = max(rect_w, rect_h)
        leaf_width_px = min(rect_w, rect_h)
        lw_ratio = leaf_length_px / leaf_width_px if leaf_width_px > 0 else 0
        
        petiole_length_px = 0.0
        com_to_petiole_end_px = 0.0
        p_end, p_flair = None, None
        curved_path, blade_cnt = [], cnt
        left_cut_idx, right_cut_idx = None, None
        cnt_points = cnt.reshape(-1, 2)

        manual_pts = None
        if args.manual_petiole: manual_pts = select_manual_petiole(img, cnt, sf)

        if manual_pts and len(manual_pts) >= 2:
            curved_path = [np.array(p, dtype=np.float32) for p in manual_pts]
            p_end = np.array(manual_pts[0], dtype=np.int32)
            p_flair = np.array(manual_pts[-1], dtype=np.int32)
            petiole_length_px = sum(np.linalg.norm(curved_path[k] - curved_path[k-1]) for k in range(1, len(curved_path)))
            com_to_petiole_end_px = float(np.linalg.norm(p_end - com))
            
            dists_to_flare = np.linalg.norm(cnt_points - p_flair, axis=1)
            flare_cnt_idx = np.argmin(dists_to_flare)
            N = len(cnt_points)
            step = max(5, int(0.01 * N))
            left_cut_idx, right_cut_idx = (flare_cnt_idx - step) % N, (flare_cnt_idx + step) % N
            
            blade_points = []
            curr = left_cut_idx
            while curr != right_cut_idx:
                blade_points.append(cnt_points[curr])
                curr = (curr + 1) % N
            blade_points.append(cnt_points[right_cut_idx])
            blade_cnt = np.array(blade_points).reshape((-1, 1, 2))

        elif args.petiole or (args.manual_petiole and manual_pts is None):
            distances_to_com = np.linalg.norm(cnt_points - com, axis=1)
            idx_petiole_end = np.argmax(distances_to_com)
            p_end = cnt_points[idx_petiole_end]  
            com_to_petiole_end_px = float(distances_to_com[idx_petiole_end])
            
            N = len(cnt_points)
            max_search, flare_sensitivity = int(N * 0.35), 1.35  
            min_petiole_length_px = 0.1 * leaf_length_px  
            baseline_calc_steps = max(15, int(0.015 * N))  
            consecutive_triggers_needed = max(3, int(0.005 * N)) 
            
            initial_width = np.linalg.norm(cnt_points[(idx_petiole_end + baseline_calc_steps) % N] - cnt_points[(idx_petiole_end - baseline_calc_steps) % N])
            
            if initial_width > (0.15 * leaf_width_px):
                print(f"  -> Stemless leaf detected (Base Width: {initial_width:.1f}px). Aborting petiole tracking.")
            else:
                curved_path = [p_end.astype(np.float32)]
                path_contour_indices = [(idx_petiole_end, idx_petiole_end)] 
                p_flair, curr_idx_B_offset = p_end.copy(), 1
                base_widths, trigger_count = [], 0
                
                for i in range(1, max_search):
                    idx_A = (idx_petiole_end + i) % N
                    pt_A = cnt_points[idx_A]
                    best_j_offset, min_w = curr_idx_B_offset, float('inf')
                    
                    for j in range(max(1, curr_idx_B_offset - 15), min(max_search, curr_idx_B_offset + 35)):
                        w = np.linalg.norm(pt_A - cnt_points[(idx_petiole_end - j) % N])
                        if w < min_w: min_w, best_j_offset = w, j
                            
                    curr_idx_B_offset = best_j_offset
                    idx_B_final = (idx_petiole_end - curr_idx_B_offset) % N
                    local_center = (pt_A + cnt_points[idx_B_final]) / 2.0
                    
                    petiole_length_px += np.linalg.norm(local_center - curved_path[-1])
                    curved_path.append(local_center)
                    path_contour_indices.append((idx_A, idx_B_final)) 
                    
                    if i <= baseline_calc_steps:
                        base_widths.append(min_w)
                        baseline = np.median(base_widths)
                    else:
                        if min_w > (baseline * flare_sensitivity) and petiole_length_px > min_petiole_length_px:
                            trigger_count += 1
                        else: trigger_count = 0 
                            
                        if trigger_count >= consecutive_triggers_needed:
                            flare_idx = max(0, len(curved_path) - consecutive_triggers_needed)
                            p_flair = curved_path[flare_idx].astype(int)
                            left_cut_idx, right_cut_idx = path_contour_indices[flare_idx]
                            
                            blade_points = []
                            curr = left_cut_idx
                            while curr != right_cut_idx:
                                blade_points.append(cnt_points[curr])
                                curr = (curr + 1) % N
                            blade_points.append(cnt_points[right_cut_idx])
                            blade_cnt = np.array(blade_points).reshape((-1, 1, 2))
                            
                            curved_path = curved_path[:flare_idx+1]
                            petiole_length_px = sum(np.linalg.norm(curved_path[k] - curved_path[k-1]) for k in range(1, len(curved_path)))
                            break

        actual_area_cm2 = area_px / pixels_per_cm2
        actual_perimeter_cm = perimeter_px / pixels_per_cm
        physical_edge_area_ratio = actual_perimeter_cm / actual_area_cm2 if actual_area_cm2 > 0 else 0
        leaf_length_cm = leaf_length_px / pixels_per_cm
        leaf_width_cm = leaf_width_px / pixels_per_cm
        petiole_length_cm = petiole_length_px / pixels_per_cm
        com_to_petiole_end_cm = com_to_petiole_end_px / pixels_per_cm
        
        hull = cv.convexHull(blade_cnt)
        hull_area = cv.contourArea(hull)
        blade_area_px = cv.contourArea(blade_cnt)
        blade_degree_of_lobing = 1.0 - (blade_area_px / hull_area if hull_area > 0 else 0)
        
        hasher = hashlib.md5()
        hasher.update(filename.encode('utf-8'))
        hasher.update(cnt.tobytes())
        base_hash = hasher.hexdigest()[:8].upper()
        
        leaf_hash = base_hash
        collision_counter = 1
        while leaf_hash in seen_hashes:
            leaf_hash = f"{base_hash}-{collision_counter}"
            collision_counter += 1
        seen_hashes.add(leaf_hash)
        
        cv.drawContours(output_img, [cnt], -1, (0, 255, 0), contour_thickness)
        cv.drawContours(output_img, [np.int64(cv.boxPoints(rect))], 0, (100, 100, 100), max(1, int(1 * sf)))
        cv.drawContours(output_img, [hull], -1, (0, 255, 255), max(1, int(1.5 * sf)))

        if len(curved_path) > 1:
            cv.polylines(output_img, [np.array(curved_path, dtype=np.int32).reshape((-1, 1, 2))], False, (0, 140, 255), line_thickness)
            if left_cut_idx is not None and right_cut_idx is not None:
                cv.line(output_img, tuple(cnt_points[left_cut_idx]), tuple(cnt_points[right_cut_idx]), (255, 255, 0), line_thickness)
        
        cv.circle(output_img, (int(cX), int(cY)), int(3 * sf), (255, 0, 0), -1)
        if p_end is not None and p_flair is not None:
            cv.circle(output_img, (int(p_end[0]), int(p_end[1])), int(3 * sf), (0, 0, 255), -1)
            cv.circle(output_img, (int(p_flair[0]), int(p_flair[1])), int(3 * sf), (255, 0, 255), -1)
        
        label_id = f"ID: {leaf_hash}"
        label_abs = f"Px A:{int(area_px)} | L:{int(leaf_length_px)} | W:{int(leaf_width_px)}"
        label_petiole_px = f"Px Petiole L:{int(petiole_length_px)} | CoM->Stem:{int(com_to_petiole_end_px)}"
        label_phys = f"Cm A:{actual_area_cm2:.1f}cm2 | L:{leaf_length_cm:.1f}cm | W:{leaf_width_cm:.1f}cm"
        label_petiole_cm = f"Cm Petiole L:{petiole_length_cm:.2f}cm | CoM->Stem:{com_to_petiole_end_cm:.2f}cm"
        label_ratios = f"L:W Ratio: {lw_ratio:.3f} | Blade Lobing: {blade_degree_of_lobing:.4f}"
        
        text_size_1, _ = cv.getTextSize(label_id, cv.FONT_HERSHEY_SIMPLEX, font_scale_id, text_thickness_bold)
        box_h = text_size_1[1] * 6 + int(72 * sf)
        pads = [int(20*sf), int(42*sf), int(64*sf), int(86*sf), int(108*sf), int(130*sf)]
        
        cv.putText(output_img, label_id, (cX - text_size_1[0]//2, cY - box_h//2 + pads[0]), cv.FONT_HERSHEY_SIMPLEX, font_scale_id, (255, 255, 255), text_thickness_bold)
        cv.putText(output_img, label_abs, (cX - cv.getTextSize(label_abs, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)[0][0]//2, cY - box_h//2 + pads[1]), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (0, 255, 255), text_thickness_thin) 
        cv.putText(output_img, label_petiole_px, (cX - cv.getTextSize(label_petiole_px, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)[0][0]//2, cY - box_h//2 + pads[2]), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (0, 255, 255), text_thickness_thin)
        cv.putText(output_img, label_phys, (cX - cv.getTextSize(label_phys, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)[0][0]//2, cY - box_h//2 + pads[3]), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (255, 180, 50), text_thickness_thin) 
        cv.putText(output_img, label_petiole_cm, (cX - cv.getTextSize(label_petiole_cm, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)[0][0]//2, cY - box_h//2 + pads[4]), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (255, 180, 50), text_thickness_thin)
        cv.putText(output_img, label_ratios, (cX - cv.getTextSize(label_ratios, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)[0][0]//2, cY - box_h//2 + pads[5]), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (100, 255, 100), text_thickness_thin) 
        
        print(f"  -> Leaf [{leaf_hash}] | Area: {actual_area_cm2:.2f} cm2 | Petiole: {petiole_length_cm:.2f} cm")
        
        csv_records.append({
            'Source_File': filename, 'Scan_DPI': dpi, 'Leaf_Hash_ID': leaf_hash,
            'Area_Pixels': int(area_px), 'Perimeter_Pixels': int(perimeter_px), 'Leaf_Length_Pixels': int(leaf_length_px), 'Leaf_Width_Pixels': int(leaf_width_px),
            'Petiole_Length_Pixels': round(petiole_length_px, 2), 'CoM_to_Petiole_End_Pixels': round(com_to_petiole_end_px, 2),
            'Area_cm2': round(actual_area_cm2, 4), 'Perimeter_cm': round(actual_perimeter_cm, 4), 'Leaf_Length_cm': round(leaf_length_cm, 4), 'Leaf_Width_cm': round(leaf_width_cm, 4),
            'Petiole_Length_cm': round(petiole_length_cm, 4), 'CoM_to_Petiole_End_cm': round(com_to_petiole_end_cm, 4),
            'Length_Width_Ratio': round(lw_ratio, 6), 'Pixel_Edge_Area_Ratio': round(pixel_edge_area_ratio, 8),
            'Physical_Edge_Area_Ratio_cm1': round(physical_edge_area_ratio, 4), 'Degree_of_Lobing': round(blade_degree_of_lobing, 6)
        })

    annotated_path = os.path.join(annotated_folder, f"Annotated_{filename}")
    cv.imwrite(annotated_path, output_img)

    if args.show:
        plt.figure(figsize=(12, 10))
        plt.imshow(cv.cvtColor(output_img, cv.COLOR_BGR2RGB))
        plt.axis('off')
        plt.title(f"Leaf Morphometrics: {filename}")
        plt.tight_layout()
        plt.show()

# --- CSV EXPORT ---
if csv_records:
    csv_filename = f'leaf_comprehensive_morphometrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv' if args.new_csv else 'leaf_comprehensive_morphometrics.csv'
    try:
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_records[0].keys()))
            writer.writeheader()
            writer.writerows(csv_records)
        print(f"\n[SUCCESS] Exported {len(csv_records)} leaves to '{csv_filename}'!")
    except IOError:
        print(f"\n[ERROR] Close '{csv_filename}' and try again.")