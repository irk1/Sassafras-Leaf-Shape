import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt
import glob
import os
import hashlib
import csv
from PIL import Image

# --- BYPASS PILLOW DECOMPRESSION BOMB LIMIT ---
# This stops Python from throwing errors on massive ultra-high-res scans
Image.MAX_IMAGE_PIXELS = None 
# ----------------------------------------------

# Set the folder where your scanned images are located
scan_folder = 'Test Images'
os.makedirs(scan_folder, exist_ok=True)

scan_files = glob.glob(os.path.join(scan_folder, '*.*'))

if not scan_files:
    print(f"Please place some scanned leaf images into the '{scan_folder}' folder and run again.")

# FALLBACK DPI: Used if an image is missing DPI data entirely
DEFAULT_DPI = 1200 

# Master list to hold data for the final CSV export
csv_records = []

for Source in scan_files:
    if not Source.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        continue
        
    filename = os.path.basename(Source)
    
    # Extract DPI metadata safely now that the pixel cap is removed
    dpi = DEFAULT_DPI
    try:
        with Image.open(Source) as img_meta:
            metadata_info = img_meta.info
            if 'dpi' in metadata_info:
                dpi = round(metadata_info['dpi'][0])
    except Exception as e:
        print(f"DPI Metadata Warning [{filename}]: Could not read DPI, using default {DEFAULT_DPI}. Error: {e}")
    
    # Calculate conversion factors based on DPI
    pixels_per_cm = dpi / 2.54
    pixels_per_cm2 = pixels_per_cm ** 2

    img = cv.imread(Source)
    if img is None:
        continue
        
    output_img = img.copy()
    
    # Dynamic UI scaling setup for massive high-res layouts
    sf = max(img.shape[0], img.shape[1]) / 2000.0
    contour_thickness = max(2, int(3 * sf))
    text_thickness_bold = max(2, int(2 * sf))
    text_thickness_thin = max(1, int(1 * sf))
    font_scale_id = 0.55 * sf
    font_scale_metrics = 0.40 * sf # Slightly smaller to fit more data lines nicely

    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    _, mask = cv.threshold(gray, 200, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)
    
    kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
    mask_clean = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)
    
    contours, _ = cv.findContours(mask_clean, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv.contourArea, reverse=True)
    
    min_area = (img.shape[0] * img.shape[1]) * 0.005 
    
    print(f"\n--- Processing File: {filename} ({dpi} DPI) ---")
    
    for cnt in contours:
        # --- ABSTRACT PIXEL MEASUREMENTS ---
        area_px = cv.contourArea(cnt)
        if area_px < min_area:
            continue
            
        perimeter_px = cv.arcLength(cnt, True)
        pixel_edge_area_ratio = perimeter_px / area_px if area_px > 0 else 0
        
        # --- PHYSICAL METRIC MEASUREMENTS ---
        actual_area_cm2 = area_px / pixels_per_cm2
        actual_perimeter_cm = perimeter_px / pixels_per_cm
        physical_edge_area_ratio = actual_perimeter_cm / actual_area_cm2 if actual_area_cm2 > 0 else 0
        
        # Geometric Shape Values
        hull = cv.convexHull(cnt)
        hull_area = cv.contourArea(hull)
        solidity = area_px / hull_area if hull_area > 0 else 0
        degree_of_lobing = 1.0 - solidity
        
        # Generate repeatable unique Hash mapping
        hasher = hashlib.md5()
        hasher.update(filename.encode('utf-8'))
        hasher.update(cnt.tobytes())
        leaf_hash = hasher.hexdigest()[:8].upper()
        
        M = cv.moments(cnt)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            x, y, w, h = cv.boundingRect(cnt)
            cX, cY = x + w // 2, y + h // 2
            
        cv.drawContours(output_img, [cnt], -1, (0, 255, 0), contour_thickness)
        
        # UI Text generation showing BOTH Abstract and Physical parameters
        label_id = f"ID: {leaf_hash}"
        label_abstract = f"Px A:{int(area_px)} | Px P:{int(perimeter_px)} | Px R:{pixel_edge_area_ratio:.6f}"
        label_physical = f"Cm A:{actual_area_cm2:.2f}cm2 | Cm P:{actual_perimeter_cm:.2f}cm | Cm R:{physical_edge_area_ratio:.4f}"
        label_lobing = f"Lobing Deg: {degree_of_lobing:.4f}"
        
        text_size_1, _ = cv.getTextSize(label_id, cv.FONT_HERSHEY_SIMPLEX, font_scale_id, text_thickness_bold)
        text_size_2, _ = cv.getTextSize(label_abstract, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        text_size_3, _ = cv.getTextSize(label_physical, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        text_size_4, _ = cv.getTextSize(label_lobing, cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, text_thickness_thin)
        
        box_w = max(text_size_1[0], text_size_2[0], text_size_3[0], text_size_4[0]) + int(24 * sf)
        box_h = text_size_1[1] + text_size_2[1] + text_size_3[1] + text_size_4[1] + int(48 * sf)
        
        pad1 = int(20 * sf)
        pad2 = int(42 * sf)
        pad3 = int(64 * sf)
        pad4 = int(86 * sf)
        
        cv.rectangle(output_img, (cX - box_w//2, cY - box_h//2), (cX + box_w//2, cY + box_h//2), (0, 0, 0), -1)
        
        cv.putText(output_img, label_id, (cX - text_size_1[0]//2, cY - box_h//2 + pad1), 
                   cv.FONT_HERSHEY_SIMPLEX, font_scale_id, (255, 255, 255), text_thickness_bold)
        cv.putText(output_img, label_abstract, (cX - text_size_2[0]//2, cY - box_h//2 + pad2), 
                   cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (0, 255, 255), text_thickness_thin)
        cv.putText(output_img, label_physical, (cX - text_size_3[0]//2, cY - box_h//2 + pad3), 
                   cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (255, 180, 50), text_thickness_thin) # Blue-ish tint for physical metrics
        cv.putText(output_img, label_lobing, (cX - text_size_4[0]//2, cY - box_h//2 + pad4), 
                   cv.FONT_HERSHEY_SIMPLEX, font_scale_metrics, (0, 255, 255), text_thickness_thin)
        
        print(f"Leaf [{leaf_hash}] Processed. Px Area: {int(area_px)} | Cm Area: {actual_area_cm2:.2f} cm2")
        
        # Save both Abstract and Physical metrics to the output list
        csv_records.append({
            'Source_File': filename,
            'Scan_DPI': dpi,
            'Leaf_Hash_ID': leaf_hash,
            'Area_Pixels': int(area_px),
            'Perimeter_Pixels': int(perimeter_px),
            'Pixel_Edge_Area_Ratio': round(pixel_edge_area_ratio, 8),
            'Area_cm2': round(actual_area_cm2, 4),
            'Perimeter_cm': round(actual_perimeter_cm, 4),
            'Physical_Edge_Area_Ratio_cm1': round(physical_edge_area_ratio, 4),
            'Degree_of_Lobing': round(degree_of_lobing, 6)
        })

    output_rgb = cv.cvtColor(output_img, cv.COLOR_BGR2RGB)
    plt.figure(figsize=(12, 10))
    plt.imshow(output_rgb)
    plt.axis('off')
    plt.title(f"Dual Metric Analysis: {filename}")
    plt.tight_layout()
    plt.show()

# --- EXPORT COMPLETE SHEET TO CSV ---
csv_filename = 'leaf_comprehensive_morphometrics.csv'
csv_headers = [
    'Source_File', 'Scan_DPI', 'Leaf_Hash_ID', 
    'Area_Pixels', 'Perimeter_Pixels', 'Pixel_Edge_Area_Ratio', 
    'Area_cm2', 'Perimeter_cm', 'Physical_Edge_Area_Ratio_cm1', 
    'Degree_of_Lobing'
]

try:
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_records)
    print(f"\n[SUCCESS] Exported complete database ({len(csv_records)} rows) containing abstract and physical measurements to '{csv_filename}'!")
except IOError:
    print(f"\n[ERROR] Close '{csv_filename}' if it's open in Excel, then run again.")