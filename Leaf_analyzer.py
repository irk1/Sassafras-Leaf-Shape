import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt
import glob
import os
import hashlib
import csv
from PIL import Image
import argparse
from datetime import datetime

# --- RUNTIME ARGUMENTS ---
parser = argparse.ArgumentParser(description="Leaf Morphometrics Analysis")
parser.add_argument('--petiole', action='store_true', help="Enable advanced petiole tracking and calculations")
parser.add_argument('--show', action='store_true', help="Display annotated images in popup windows")
parser.add_argument('--new-csv', action='store_true', help="Generate a new timestamped CSV instead of overwriting the default")
args = parser.parse_args()
# -------------------------

# --- BYPASS PILLOW DECOMPRESSION BOMB LIMIT ---
Image.MAX_IMAGE_PIXELS = None 
# ----------------------------------------------

scan_folder = 'Scans'
annotated_folder = 'Annotated Scans'
os.makedirs(scan_folder, exist_ok=True)
os.makedirs(annotated_folder, exist_ok=True)

scan_files = glob.glob(os.path.join(scan_folder, '*.*'))

if not scan_files:
    print(f"Please place some scanned leaf images into the '{scan_folder}' folder and run again.")

DEFAULT_DPI = 1200 
csv_records = []
seen_hashes = set() # Track hashes to prevent collisions

for Source in scan_files:
    if not Source.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        continue
        
    filename = os.path.basename(Source)
    
    # Extract DPI metadata safely
    dpi = DEFAULT_DPI
    try:
        with Image.open(Source) as img_meta:
            metadata_info = img_meta.info
            if 'dpi' in metadata_info:
                dpi = round(metadata_info['dpi'][0])
    except Exception as e:
        print(f"DPI Metadata Warning [{filename}]: Could not read DPI, using default {DEFAULT_DPI}. Error: {e}")
    
    # Conversion factors for secondary unit (cm)
    pixels_per_cm = dpi / 2.54
    pixels_per_cm2 = pixels_per_cm ** 2

    img = cv.imread(Source)
    if img is None:
        continue
        
    output_img = img.copy()
    
    # Dynamic UI scaling setup for massive high-res layouts
    sf = max(img.shape[0], img.shape[1]) / 2000.0
    contour_thickness = max(2, int(3 * sf))
    line_thickness = max(2, int(4 * sf))
    text_thickness_bold = max(2, int(2 * sf))
    text_thickness_thin = max(1, int(1 * sf))
    font_scale_id = 0.55 * sf
    font_scale_metrics = 0.38 * sf 

    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    _, mask = cv.threshold(gray, 200, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)
    
    kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
    mask_clean = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)
    
    contours, _ = cv.findContours(mask_clean, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv.contourArea, reverse=True)
    
    min_area = (img.shape[0] * img.shape[1]) * 0.005 
    
    print(f"\n--- Processing File: {filename} ({dpi} DPI) ---")
    
    for cnt in contours:
        # --- 1. PRIMARY ANALYSIS (PIXELS) ---
        area_px = cv.contourArea(cnt)
        if area_px < min_area:
            continue
            
        perimeter_px = cv.arcLength(cnt, True)
        pixel_edge_area_ratio = perimeter_px / area_px if area_px > 0 else 0
        
        # Center of Mass (Centroid)
        M = cv.moments(cnt)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            x_b, y_b, w_b, h_b = cv.boundingRect(cnt)
            cX, cY = x_b + w_b // 2, y_b + h_b // 2
        com = np.array([cX, cY], dtype=np.float32)
        
        # Length & Width via Rotated Bounding Box
        rect = cv.minAreaRect(cnt)
        rect_w, rect_h = rect[1]
        leaf_length_px = max(rect_w, rect_h)
        leaf_width_px = min(rect_w, rect_h)
        lw_ratio = leaf_length_px / leaf_width_px if leaf_width_px > 0 else 0
        
        # Default Petiole Initialization
        petiole_length_px = 0.0
        com_to_petiole_end_px = 0.0
        p_end = None
        p_flair = None
        curved_path = []

        if args.petiole:
            # Advanced Petiole Sizing via Vector Tracking
            cnt_points = cnt.reshape(-1, 2)
            distances_to_com = np.linalg.norm(cnt_points - com, axis=1)
            idx_petiole_end = np.argmax(distances_to_com)
            p_end = cnt_points[idx_petiole_end]  # Stem attachment point
            
            com_to_petiole_end_px = float(distances_to_com[idx_petiole_end])
            
            # === MODIFICATION START: CURVED PETIOLE INTEGRATION ===
            N = len(cnt_points)
            max_search = int(N * 0.35)  
            
            # --- TUNING PARAMETERS ---
            flare_sensitivity = 1.35  # Multiplier (e.g., 1.35 = 35% wider than the petiole)
            min_petiole_length_px = 0.1 * leaf_length_px  # Must travel 10% of leaf length before checking
            baseline_calc_steps = max(15, int(0.015 * N))  # Dynamic physical distance to sample base width
            consecutive_triggers_needed = max(3, int(0.005 * N)) # Must STAY wide for N steps to ignore bumps
            # -------------------------
            
            curved_path = [p_end.astype(np.float32)]
            p_flair = p_end.copy()
            curr_idx_B_offset = 1
            
            base_widths = []
            trigger_count = 0
            
            for i in range(1, max_search):
                idx_A = (idx_petiole_end + i) % N
                pt_A = cnt_points[idx_A]
                
                best_j_offset = curr_idx_B_offset
                min_w = float('inf')
                
                # Widened search window to accommodate high-res shifting
                start_j = max(1, curr_idx_B_offset - 15)
                end_j = min(max_search, curr_idx_B_offset + 35)
                
                for j in range(start_j, end_j):
                    idx_B = (idx_petiole_end - j) % N
                    pt_B = cnt_points[idx_B]
                    w = np.linalg.norm(pt_A - pt_B)
                    if w < min_w:
                        min_w = w
                        best_j_offset = j
                        
                curr_idx_B_offset = best_j_offset
                idx_B_final = (idx_petiole_end - curr_idx_B_offset) % N
                pt_B_final = cnt_points[idx_B_final]
                
                local_width = min_w
                local_center = (pt_A + pt_B_final) / 2.0
                
                step_dist = np.linalg.norm(local_center - curved_path[-1])
                petiole_length_px += step_dist
                curved_path.append(local_center)
                
                # Phase 1: Build a robust statistical baseline using the Median (ignores cut-point noise)
                if i <= baseline_calc_steps:
                    base_widths.append(local_width)
                    baseline = np.median(base_widths)
                    
                # Phase 2: Look for sustained, continuous expansion
                else:
                    if local_width > (baseline * flare_sensitivity) and petiole_length_px > min_petiole_length_px:
                        trigger_count += 1
                    else:
                        # If the width shrinks again, it was just a bump. Reset the trigger.
                        trigger_count = 0 
                        
                    # If it stays expanded for the required number of steps, we found the true blade
                    if trigger_count >= consecutive_triggers_needed:
                        # Step back visually to the exact point the flare started
                        flare_idx = max(0, len(curved_path) - consecutive_triggers_needed)
                        p_flair = curved_path[flare_idx].astype(int)
                        
                        # Trim the visual path line so it doesn't bleed into the blade
                        curved_path = curved_path[:flare_idx+1]
                        petiole_length_px = sum(np.linalg.norm(curved_path[k] - curved_path[k-1]) for k in range(1, len(curved_path)))
                        break
                        
            # === MODIFICATION END =================================

        # --- 2. SECONDARY CALIBRATION (CENTIMETERS) ---
        actual_area_cm2 = area_px / pixels_per_cm2
        actual_perimeter_cm = perimeter_px / pixels_per_cm
        physical_edge_area_ratio = actual_perimeter_cm / actual_area_cm2 if actual_area_cm2 > 0 else 0
        leaf_length_cm = leaf_length_px / pixels_per_cm
        leaf_width_cm = leaf_width_px / pixels_per_cm
        petiole_length_cm = petiole_length_px / pixels_per_cm
        com_to_petiole_end_cm = com_to_petiole_end_px / pixels_per_cm
        
        # Dimensionless Shape Values
        hull = cv.convexHull(cnt)
        hull_area = cv.contourArea(hull)
        solidity = area_px / hull_area if hull_area > 0 else 0
        degree_of_lobing = 1.0 - solidity
        
        # Generate repeatable unique Hash mapping with collision prevention
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
        
        # --- DRAW VISUAL ANNOTATIONS ---
        cv.drawContours(output_img, [cnt], -1, (0, 255, 0), contour_thickness)
        box_points = np.int64(cv.boxPoints(rect))
        cv.drawContours(output_img, [box_points], 0, (100, 100, 100), max(1, int(1 * sf)))
        
        # === MODIFICATION START: DRAWING CURVED PATH ===
        if args.petiole and len(curved_path) > 1:
            points_poly = np.array(curved_path, dtype=np.int32).reshape((-1, 1, 2))
            cv.polylines(output_img, [points_poly], False, (0, 140, 255), line_thickness)
        # === MODIFICATION END =========================
        
        cv.circle(output_img, (int(cX), int(cY)), int(3 * sf), (255, 0, 0), -1)
        if args.petiole and p_end is not None and p_flair is not None:
            cv.circle(output_img, (int(p_end[0]), int(p_end[1])), int(3 * sf), (0, 0, 255), -1)
            cv.circle(output_img, (int(p_flair[0]), int(p_flair[1])), int(3 * sf), (255, 0, 255), -1)
        
        
        # --- UI DATA PANEL GENERATION (PIXEL DOMINANT) ---
        label_id = f"ID: {leaf_hash}"
        label_abs = f"Px A:{int(area_px)} | L:{int(leaf_length_px)} | W:{int(leaf_width_px)}"
        label_petiole_px = f"Px Petiole L:{int(petiole_length_px)} | CoM->Stem:{int(com_to_petiole_end_px)}"
        label_phys = f"Cm A:{actual_area_cm2:.1f}cm2 | L:{leaf_length_cm:.1f}cm | W:{leaf_width_cm:.1f}cm"
        label_petiole_cm = f"Cm Petiole L:{petiole_length_cm:.2f}cm | CoM->Stem:{com_to_petiole_end_cm:.2f}cm"
        label_ratios = f"L:W Ratio: {lw_ratio:.3f} | Lobing Deg: {degree_of_lobing:.4f}"
        
        text_size_1, _ = cv.getTextSize(label_id, cv.FONT_HERSHEY_SIMPLEX, font_scale_id, text_thickness_bold)
        text_size_2, _ = cv.getTextSize(label_abs, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        text_size_3, _ = cv.getTextSize(label_petiole_px, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        text_size_4, _ = cv.getTextSize(label_phys, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        text_size_5, _ = cv.getTextSize(label_petiole_cm, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        text_size_6, _ = cv.getTextSize(label_ratios, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        
        box_w = max(text_size_1[0], text_size_2[0], text_size_3[0], text_size_4[0], text_size_5[0], text_size_6[0]) + int(24 * sf)
        box_h = text_size_1[1] + text_size_2[1] + text_size_3[1] + text_size_4[1] + text_size_5[1] + text_size_6[1] + int(72 * sf)
        
        pad1, pad2, pad3, pad4, pad5, pad6 = int(20*sf), int(42*sf), int(64*sf), int(86*sf), int(108*sf), int(130*sf)
        
        # Render Box Background
        #cv.rectangle(output_img, (cX - box_w//2, cY - box_h//2), (cX + box_w//2, cY + box_h//2), (0, 0, 0), -1)
        
        # Print Text Data Lines
        cv.putText(output_img, label_id, (cX - text_size_1[0]//2, cY - box_h//2 + pad1), cv.FONT_HERSHEY_SIMPLEX, font_scale_id, (255, 255, 255), text_thickness_bold)
        cv.putText(output_img, label_abs, (cX - text_size_2[0]//2, cY - box_h//2 + pad2), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (0, 255, 255), text_thickness_thin) # Cyan for primary px
        cv.putText(output_img, label_petiole_px, (cX - text_size_3[0]//2, cY - box_h//2 + pad3), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (0, 255, 255), text_thickness_thin)
        cv.putText(output_img, label_phys, (cX - text_size_4[0]//2, cY - box_h//2 + pad4), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (255, 180, 50), text_thickness_thin) # Orange for secondary cm
        cv.putText(output_img, label_petiole_cm, (cX - text_size_5[0]//2, cY - box_h//2 + pad5), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (255, 180, 50), text_thickness_thin)
        cv.putText(output_img, label_ratios, (cX - text_size_6[0]//2, cY - box_h//2 + pad6), cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (100, 255, 100), text_thickness_thin) # Green for ratios
        
        print(f"Leaf [{leaf_hash}] -> Px Petiole: {int(petiole_length_px)} px ({petiole_length_cm:.2f} cm) | L:W Ratio: {lw_ratio:.3f}")
        
        # Save metrics to database tracking record list
        csv_records.append({
            'Source_File': filename,
            'Scan_DPI': dpi,
            'Leaf_Hash_ID': leaf_hash,
            'Area_Pixels': int(area_px),
            'Perimeter_Pixels': int(perimeter_px),
            'Leaf_Length_Pixels': int(leaf_length_px),
            'Leaf_Width_Pixels': int(leaf_width_px),
            'Petiole_Length_Pixels': round(petiole_length_px, 2),
            'CoM_to_Petiole_End_Pixels': round(com_to_petiole_end_px, 2),
            'Area_cm2': round(actual_area_cm2, 4),
            'Perimeter_cm': round(actual_perimeter_cm, 4),
            'Leaf_Length_cm': round(leaf_length_cm, 4),
            'Leaf_Width_cm': round(leaf_width_cm, 4),
            'Petiole_Length_cm': round(petiole_length_cm, 4),
            'CoM_to_Petiole_End_cm': round(com_to_petiole_end_cm, 4),
            'Length_Width_Ratio': round(lw_ratio, 6),
            'Pixel_Edge_Area_Ratio': round(pixel_edge_area_ratio, 8),
            'Physical_Edge_Area_Ratio_cm1': round(physical_edge_area_ratio, 4),
            'Degree_of_Lobing': round(degree_of_lobing, 6)
        })

    # Save out the high-quality annotated diagnostic file
    annotated_filename = f"Annotated_{filename}"
    annotated_path = os.path.join(annotated_folder, annotated_filename)
    cv.imwrite(annotated_path, output_img)
    print(f"[SAVED ANNOTATION] -> {annotated_path}")

    # Render localized notebook view window if --show is passed
    if args.show:
        output_rgb = cv.cvtColor(output_img, cv.COLOR_BGR2RGB)
        plt.figure(figsize=(12, 10))
        plt.imshow(output_rgb)
        plt.axis('off')
        plt.title(f"Comprehensive Pixel-Primary Morphometrics: {filename}")
        plt.tight_layout()
        plt.show()

# --- EXPORT COMPLETE SHEET TO CSV ---
if args.new_csv:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f'leaf_comprehensive_morphometrics_{timestamp}.csv'
else:
    csv_filename = 'leaf_comprehensive_morphometrics.csv'

csv_headers = [
    'Source_File', 'Scan_DPI', 'Leaf_Hash_ID', 
    'Area_Pixels', 'Perimeter_Pixels', 'Leaf_Length_Pixels', 'Leaf_Width_Pixels', 'Petiole_Length_Pixels', 'CoM_to_Petiole_End_Pixels',
    'Area_cm2', 'Perimeter_cm', 'Leaf_Length_cm', 'Leaf_Width_cm', 'Petiole_Length_cm', 'CoM_to_Petiole_End_cm',
    'Length_Width_Ratio', 'Pixel_Edge_Area_Ratio', 'Physical_Edge_Area_Ratio_cm1', 'Degree_of_Lobing'
]

try:
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_records)
    print(f"\n[SUCCESS] Exported complete database ({len(csv_records)} rows) to '{csv_filename}'!")
except IOError:
    print(f"\n[ERROR] Close '{csv_filename}' if it's open in Excel, then run again.")