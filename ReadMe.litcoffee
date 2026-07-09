# Leaf Morphometrics & Advanced Petiole Tracker

An automated, pixel-dominant computer vision pipeline designed for processing high-resolution botanical scans. This program extracts clean geometric data from leaf specimens, establishes repeatable phenotypic profiles via localized data tracking, and uses statistical center-line modeling to reliably separate the petiole (stem) from the leaf blade.

---

## Key Features

* **High-Resolution Specimen Management:** Safely bypasses default image decompression safeguards to process massive ultra-high-DPI botanical scans without memory faults.
* **Metadata-Driven Calibration:** Automatically parses image header metadata to extract native DPI, converting raw pixel data into exact real-world metric units ($\text{cm}$ and $\text{cm}^2$).
* **Dynamic UI Adaptability:** Universally auto-scales all visual overlays, contour weights, diagnostic dots, and information text displays relative to the dimensions of the input image. 
* **Repeatable Specimen Hashing:** Generates deterministic, 8-character cryptographic alphanumeric IDs based on absolute contour topologies to prevent duplicate tracking or database row collisions.
* **Noise-Resistant Petiole Pathing:** Employs an adaptive geometric search that tracks a leaf’s base width, filters out biological bumps using localized median tracking, and flags the exact transition to the leaf blade.

---

## Directory Structure

Upon its first execution, the program sets up a standardized localized workspace:

    ├── leaf_analyzer.py                      # Main executable script
    ├── leaf_comprehensive_morphometrics.csv  # Auto-generated relational database
    ├── Scans/                          # Drop-zone for raw specimen scans (.png, .jpg, .tiff)
    └── Annotated Scans/                      # Generated visual diagnostic sheets

---
## Command-Line Execution Flags

This analyzer can be customized at runtime using several command-line arguments. By default, the script is optimized for batch-processing speed—meaning it runs silently, skips the advanced petiole math, and overwrites the default CSV. 

You can modify its behavior by passing any combination of the following flags:

* `--petiole`: **Enables advanced petiole tracking.** The script actively maps the transition boundary between the blade and the stem using vector tracking to calculate precise, curved petiole lengths.
* `--show`: **Enables visual diagnostics.** Displays a high-quality popup window for each leaf as it processes. *(Note: You must close the popup window to advance to the next leaf).*
* `--new-csv`: **Creates a unique database export.** Generates a fresh CSV file stamped with the current date and time (e.g., `leaf_comprehensive_morphometrics_20260709_112407.csv`) to prevent overwriting your previous datasets.

**Example Usage:**
    
    # Run with all features active and generate a new dataset
    python leaf_analyzer.py --petiole --show --new-csv
---
## Technical Pipeline: How It Works

```text
[ Raw Image Input ] ─────> [ Metadata DPI Extraction ] ─────> [ Grayscale & Otsu Threshold ]
                                                                             │
                                                                             ▼
[ Area & Perimeter ] <──── [ Area Filter (<0.5% Canvas) ] <──── [ Morphological Clean-up ]
         │
         ▼
[ Moment Centroid ] ─────> [ Rotated Bounding Box (L/W) ] ─────> [ Stem Terminus Localization ]
                                                                             │
                                                                             ▼
[ Physical Conversion ] <─── [ Stem Flare Detection ] <─────── [ Sliding-Window Pathing ]
         │
         ▼
[ Convex Hull & Lobing ] ──> [ MD5 Cryptographic Hashing ] ──> [ CSV Database & UI Export ]
```
### 1. Preprocessing & Segmentation
1. **Physical Scaling Calculation:** The system attempts to read the native resolution array from the image metadata. If missing, it defaults to $1200\text{ DPI}$ (This Can Be Modified At Line 24). Conversion ratios are established dynamically:
$$\text{Pixels\_per\_cm}=\frac{\text{DPI}}{2.54}$$
2. **Binarization:** Images are downsampled to grayscale, and an automated Otsu adaptive thresholding technique separates the specimen from the background canvas:
$$\text{Thresholding\_Option}=\text{cv.THRESH\_BINARY\_INV}+\text{cv.THRESH\_OTSU}$$
3. **Morphological Filtering:** A $5\times 5$ elliptical structural kernel executes a morphological opening sequence to dissolve dust artifacts, frayed structural hairs, and floating scan anomalies.

### 2. Global Geometric Metrics
* **Spatial Centroid Calculation:** The exact structural Center of Mass ($\text{CoM}$) is resolved using localized physical image moments:
$$cX=\frac{M_{10}}{M_{00}},\quad cY=\frac{M_{01}}{M_{00}}$$
If an anomalous edge artifact disrupts the moment boundaries, the program cleanly defaults to the exact midpoint of a standard orthogonal bounding box. Center of Mass ($\text{CoM}$) may be reffered to as Center of Gravity in the code.
* **Rotated Structural Bounds:** A minimum area enclosing rectangle (`cv.minAreaRect`) fits around the contour. The longer axis defines the absolute maximum Leaf Length, and the perpendicular axis establishes the Leaf Width.
* **Solidity & Lobing Coefficients:** The program derives dimensionless shape identifiers by computing a convex envelope profile over the contour boundaries:
$$\text{Solidity}=\frac{\text{Area}_{\text{Contour}}}{\text{Area}_{\text{Hull}}}$$
$$\text{Degree\_of\_Lobing}=1.0-\text{Solidity}$$

---

## Advanced Feature: The Petiole Flare Algorithm

Locating where a petiole officially transitions into a leaf blade is notoriously challenging due to variable tapers and localized surface bumps. This application solves this through a localized center-line widening profile:

                      _.-'''''''-._
                    .'             '.
                   /                 \
                  |                   | <--- Leaf Blade
                   \                 /
      Flare Point   '.             .'  
       (p_flair) ====> '._      _.' <----- Sustained Expansion Triggered
                          |    |
                          |    |     <---- Moving Median Baseline Measured
                          |    |
      Stem Attachment ===> \__/
       (p_end)

### The Pathing & Flare Separation Logic

1. **Origin Anchoring ($p_{end}$):** The system calculates Euclidean distance vectors from the Centroid to every coordinate on the continuous outer boundary. The maximum value identifies the tail tip where the petiole was cut from the plant:
$$p_{end}=\arg\max_{p\in\text{contour}}\|p-\text{CoM}\|$$
2. **Bilateral Contour Walk:** Starting at $p_{end}$, the loop marches symmetrically outward in both clockwise and counter-clockwise directions along the contour index array.
3. **Localized Center & Width Resolution:** For every index step $i$, a localized vector search matches point $A$ on the left wall with its nearest counterpart point $B$ on the right wall. This calculates the changing cross-sectional thickness ($local\_width$) and the physical core path ($local\_center$).
4. **Statistical Median Baseline:** To avoid being tricked by tears, jagged cuts, or immediate flare artifacts right at the base of the stem, the program monitors the first $1.5\%$ of the total contour point array to establish a true average thickness baseline using a median calculation:
$$\text{Baseline\_Width}=\text{median}(local\_width_{1\dots i})$$
5. **Sustained Flare Condition:** As the tracking path travels up the stem, it evaluates two strict conditions before it can call a point the "leaf blade":
   * **Minimum Travel Constraint:** The accumulated path length must be greater than a baseline minimum ($10\%$ of global leaf length) to stop short petioles from triggering early.
   * **Sustained Expansion Run:** The local width must exceed the baseline by the `flare_sensitivity` coefficient. To ensure a small structural bump doesn't falsely halt tracking, this expansion must hold true continuously for a specific number of consecutive steps (`consecutive_triggers_needed`).
6. **Visual Rollback Optimization:** Once a sustained flare is confirmed, the engine steps back along the path history to the exact index where the widening first began, assigning the **Magenta Flare Dot** ($p_{flair}$) cleanly at the true anatomical intersection.

---

## Tuning Parameters

You can easily recalibrate the sensitivity thresholds inside the script's core logic:

| Parameter Name | Target Purpose | Default Value | Tuning Impact |
| :--- | :--- | :--- | :--- |
| `flare_sensitivity` | Width multiplier indicating blade expansion. | `1.35` | Lower values capture subtle tapers. Higher values require a sharp flare. |
| `min_petiole_length_px` | Minimum distance required before flare checking opens. | `0.1 * leaf_length_px` | Prevents erratic tracking anomalies right at a jagged cut petiole base. |
| `baseline_calc_steps` | Number of initial samples used to define average stem width.| `max(15, int(0.015 * N))` | Increase for heavily textured petioles; decrease if petioles are extremely short. |
| `consecutive_triggers_needed` | Step window required to confirm a continuous blade flare. | `max(3, int(0.005 * N))` | Higher values ignore large petiole bumps; lower values trigger instantly on crisp edges. |

---

## Diagnostic Outputs & Visual Annotations

Every processed scan generates an asset layout featuring dynamic, color-coded visual markers:

* **Blue Node:** The spatial center of mass (Centroid).
* **Red Node:** The base attachment tip of the petiole tail. (where its cut from the stem)

* **Magenta Node:** The identified petiole flare entry point into the leaf blade.
* **Orange Ribbon Line:** The dynamically traced center-line path running through the core of the petiole.
* **Thin Grey Frame:** The minimum area enclosing bounding box mapping the main growth orientation axes.
* **Integrated Metadata Panel:** A rendered dashboard painted directly onto the center of the canvas detailing identification hashes, pixel measurements, calibrated metric calculations, and shape ratios.

---

## Relational Database Fields

All numerical calculations are exported cleanly to `leaf_comprehensive_morphometrics.csv` with the following structures:

| CSV Column Identifier | Data Type | Analytical Description |
| :--- | :--- | :--- |
| `Source_File` | String | System name of the input image file. |
| `Scan_DPI` | Integer | Resolution value parsed from metadata header or program default. |
| `Leaf_Hash_ID` | String | Unique 8-character cryptographic hash signature of the specimen. |
| `Area_Pixels` | Integer | Count of all interior mask pixels defining the leaf structure. |
| `Perimeter_Pixels` | Integer | Total contour pixel length around the specimen perimeter. |
| `Leaf_Length_Pixels` | Integer | Length of the long axis of the minimum rotated bounding box. |
| `Leaf_Width_Pixels` | Integer | Width of the short axis of the minimum rotated bounding box. |
| `Petiole_Length_Pixels`| Float | Total distance computed along the curved petiole core path. |
| `CoM_to_Petiole_End_Pixels`| Float | Direct straight-line distance from the center mass to the stem base. |
| `Area_cm2` | Float | Calibrated surface area of the leaf specimen. |
| `Perimeter_cm` | Float | Calibrated boundary length of the leaf specimen. |
| `Leaf_Length_cm` | Float | Calibrated real-world length of the primary growth axis. |
| `Leaf_Width_cm` | Float | Calibrated real-world width of the secondary growth axis. |
| `Petiole_Length_cm` | Float | Calibrated anatomical length of the petiole path. |
| `CoM_to_Petiole_End_cm` | Float | Calibrated straight-line metric distance from the center of mass to the stem base. |
| `Length_Width_Ratio` | Float | Aspect ratio indicating overall leaf elongation. |
| `Pixel_Edge_Area_Ratio` | Float | Raw ratio of perimeter pixels relative to area pixels. |
| `Physical_Edge_Area_Ratio_cm1` | Float | Calibrated boundary-to-surface-area ratio in metric units. |
| `Degree_of_Lobing` | Float | Geometric ratio ($0.0$ to $1.0$) indicating edge complexity and sinus depths. |
---
# Future Plans

* **Manual Petiole Tracking:** A popup window where you place a series of points to track the petiole manually and the program connects the dots instead of finding the petiole itself.