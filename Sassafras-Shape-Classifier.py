import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt
import glob
import os

known_folders = {
    'mitten': 'Mitten',
    'glove': 'Glove',
    'oval': 'Oval'
}
test_folder = 'Test Images'

for folder in known_folders.values():
    os.makedirs(folder, exist_ok=True)

valid_shapes = ['mitten', 'glove', 'oval']
test_files = glob.glob(os.path.join(test_folder, '*.*'))

for Source in test_files:
    if not Source.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue
        
    filename = os.path.basename(Source)
    img = cv.imread(Source)
    if img is None:
        continue
        
    original_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)

    # 1. Blur and extract Saturation
    blur = cv.GaussianBlur(img, (11, 11), 0)
    hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)
    s_channel = hsv[:, :, 1]
    
    # 2. Thresholding
    _, mask_raw = cv.threshold(s_channel, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    
    # 3. HEAVY EDGE-SEALING (The Fix)
    # This dynamic brush scales with your image size. It bridges over narrow glare-gashes
    # that touch the edge of the leaf, turning them back into internal voids.
    close_size = max(5, int(max(img.shape[:2]) * 0.015))
    kernel_close = cv.getStructuringElement(cv.MORPH_ELLIPSE, (close_size, close_size))
    mask_raw = cv.morphologyEx(mask_raw, cv.MORPH_CLOSE, kernel_close)
    
    # 4. Strict Perimeter Extraction
    # RETR_EXTERNAL explicitly ignores internal holes. Because we sealed the edges above,
    # the glare spots are now trapped inside and fully ignored.
    contours_raw, _ = cv.findContours(mask_raw, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    mask_extraction = np.zeros_like(mask_raw)
    
    min_area = (img.shape[0] * img.shape[1]) * 0.005
    valid_raw_cnts = [cnt for cnt in contours_raw if cv.contourArea(cnt) > min_area]
    
    # Draw as a completely solid polygon to guarantee no internal voids exist
    cv.drawContours(mask_extraction, valid_raw_cnts, -1, 255, thickness=cv.FILLED)
    
    final_ext_contours, _ = cv.findContours(mask_extraction, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    final_ext_contours = sorted(final_ext_contours, key=cv.contourArea, reverse=True)[:5]
    
    k_size = max(3, int(max(img.shape[:2]) * 0.015))
    kernel_open = cv.getStructuringElement(cv.MORPH_ELLIPSE, (k_size, k_size))
    mask_math = cv.morphologyEx(mask_extraction, cv.MORPH_OPEN, kernel_open)
    
    math_contours, _ = cv.findContours(mask_math, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    math_contours = sorted([cnt for cnt in math_contours if cv.contourArea(cnt) > min_area], key=cv.contourArea, reverse=True)[:5]
    
    match_tally = {"mitten": 0, "glove": 0, "oval": 0}
    unmatched_count = 0
    leaves_to_review = []
    
    buffer_size = 60 
    edge_padding_pixels = 50 
    
    for idx, cnt_math in enumerate(math_contours, 1):
        M = cv.moments(cnt_math)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            x, y, w, h = cv.boundingRect(cnt_math)
            cX, cY = x + w // 2, y + h // 2

        matched_ext_cnt = cnt_math 
        for ext_cnt in final_ext_contours:
            if cv.pointPolygonTest(ext_cnt, (cX, cY), False) >= 0:
                matched_ext_cnt = ext_cnt
                break
        
        rx, ry, rw, rh = cv.boundingRect(matched_ext_cnt)
        
        x_start = max(0, rx - buffer_size)
        y_start = max(0, ry - buffer_size)
        x_end = min(img.shape[1], rx + rw + buffer_size)
        y_end = min(img.shape[0], ry + rh + buffer_size)
        
        roi_color = img[y_start:y_end, x_start:x_end]
        
        # Create the exact mask for extraction, strictly filled as a single solid polygon
        single_leaf_mask = np.zeros_like(mask_extraction)
        cv.fillPoly(single_leaf_mask, [matched_ext_cnt], 255)
        roi_mask_exact = single_leaf_mask[y_start:y_end, x_start:x_end]
        
        if edge_padding_pixels > 0:
            pad_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (edge_padding_pixels, edge_padding_pixels))
            roi_mask_padded = cv.dilate(roi_mask_exact, pad_kernel, iterations=1)
        else:
            roi_mask_padded = roi_mask_exact
        
        roi_bgra = cv.cvtColor(roi_color, cv.COLOR_BGR2BGRA)
        roi_bgra[:, :, 3] = roi_mask_padded
        
        scale = max(rw, rh) 
        area = cv.contourArea(cnt_math)
        
        epsilon = 0.008 * cv.arcLength(cnt_math, True)
        approx_cnt = cv.approxPolyDP(cnt_math, epsilon, True)
        
        hull_pts = cv.convexHull(approx_cnt)
        hull_area = cv.contourArea(hull_pts)
        solidity = float(area) / hull_area if hull_area > 0 else 0
        
        hull_indices = cv.convexHull(approx_cnt, returnPoints=False)
        deep_defects = 0
        
        if hull_indices is not None and len(hull_indices) > 3:
            try:
                defects = cv.convexityDefects(approx_cnt, hull_indices)
                if defects is not None:
                    for i in range(defects.shape[0]):
                        s, e, f, d = defects[i, 0]
                        depth = d / 256.0 
                        
                        if depth > scale * 0.12: 
                            deep_defects += 1
            except cv.error:
                pass 
                
        best_match_name = "unknown"
        
        if deep_defects == 0:
            best_match_name = "oval"
        elif deep_defects == 1:
            best_match_name = "mitten"
        elif deep_defects == 2:
            best_match_name = "glove"

        if best_match_name in match_tally:
            match_tally[best_match_name] += 1
            cv.drawContours(original_rgb, [approx_cnt], -1, (0, 255, 0), 4)
            cv.drawContours(original_rgb, [hull_pts], -1, (255, 255, 0), 2)
            cv.putText(original_rgb, f"#{idx} {best_match_name}", (cX - 40, cY), cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 3)
        else:
            unmatched_count += 1
            cv.drawContours(original_rgb, [approx_cnt], -1, (255, 0, 0), 4)
            cv.putText(original_rgb, f"#{idx} Unknown (Defects:{deep_defects})", (cX - 40, cY), cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 3)

        leaves_to_review.append((roi_bgra, best_match_name, cnt_math, idx))

    print(f"--- Results for {filename} ---")
    for name, count in match_tally.items():
        print(f"{name.capitalize()}: {count}")
    print(f"Unidentified/Ignored shapes: {unmatched_count}")
    
    plt.figure(figsize=(10, 8))
    plt.imshow(original_rgb)
    plt.axis('off')
    plt.title(f"Results: {filename}")
    plt.show()
    
    if leaves_to_review:
        print("\n--- Reviewing Leaves ---")
        for roi_bgra, predicted_name, cnt_test, leaf_id in leaves_to_review:
            plt.figure(f"Reviewing Leaf #{leaf_id}")
            roi_rgba = cv.cvtColor(roi_bgra, cv.COLOR_BGRA2RGBA)
            plt.imshow(roi_rgba)
            plt.axis('off')
            plt.show(block=False)
            plt.pause(0.1)
            
            print(f"\nLeaf #{leaf_id} - Auto-Detected as: {predicted_name.capitalize()}")
            user_input = input("Save? [y = Yes, n = No, or type mitten/glove/oval]: ").strip().lower()
            
            plt.close()
            
            if user_input != 'n' and user_input != '':
                final_name = predicted_name.lower() if user_input == 'y' else user_input
                
                if final_name in valid_shapes:
                    target_folder = known_folders[final_name]
                    existing_files = glob.glob(os.path.join(target_folder, f"{final_name}_*.*"))
                    
                    max_num = 0
                    for f in existing_files:
                        try:
                            base = os.path.basename(f).rsplit('.', 1)[0]
                            num_str = base.split('_')[-1]
                            num = int(num_str)
                            if num > max_num:
                                max_num = num
                        except ValueError:
                            pass
                    
                    new_num = max_num + 1
                    save_path = os.path.join(target_folder, f"{final_name}_{new_num}.png")
                    
                    cv.imwrite(save_path, roi_bgra)
                    print(f"Saved solid, void-free PNG to {save_path}!")
                else:
                    print(f"Invalid classification '{final_name}'. Must be mitten, glove, or oval. Skipping.")
            else:
                print("Skipped.")