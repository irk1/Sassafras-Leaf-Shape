# Leaf Morphometrics & Advanced Petiole Tracker

An automated, pixel-dominant computer vision pipeline designed for processing high-resolution botanical scans. This program extracts clean geometric data from leaf specimens, establishes repeatable phenotypic profiles via localized data tracking, and uses statistical center-line modeling to reliably separate the petiole (stem) from the leaf blade.

---

## Key Features



* **High-Resolution Specimen Management:** Safely bypasses default image decompression safeguards to process massive ultra-high-DPI botanical scans without memory faults.
* **Metadata-Driven Calibration:** Automatically parses image header metadata to extract native DPI, converting raw pixel data into exact real-world metric units ($\text{cm}$ and $\text{cm}^2$).
* **Dynamic UI Adaptability:** Universally auto-scales all visual overlays, contour weights, diagnostic dots, and information text displays relative to the dimensions of the input image. 
* **Repeatable Specimen Hashing:** Generates deterministic, 8-character cryptographic alphanumeric IDs based on absolute contour topologies of the raw, physical binarized footprint to prevent duplicate tracking or database row collisions.
* **Noise-Resistant Petiole Pathing:** Employs an adaptive geometric search that tracks a leaf’s base width, filters out biological bumps using localized median tracking, and flags the exact transition to the leaf blade.
* **Digital Blade Amputation:** Once the petiole flare is identified, the script digitally "severs" the stem contour from the leaf blade. Advanced shape metrics (such as Convex Hull and Degree of Lobing) are calculated exclusively on this pristine blade, preventing long stems from distorting biological shape profiles.
* **Sessile (Stemless) Safeguard:** Features an automated baseline width check at the base of the leaf. If a specimen naturally lacks a petiole (sessile) or is broken, the script automatically aborts the tracking process to prevent accidental clipping of the leaf blade's natural apex.

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
```
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
         │                   (With Sessile Safety Check)
         ▼
[ Amputated Blade Contour ] ──> [ Convex Hull & Lobing ] ──> [ MD5 Cryptographic Hashing ] ──> [ Export ]
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
* **Solidity & Lobing Coefficients:** The program derives dimensionless shape identifiers by computing a convex envelope profile over the contour boundaries. When `--petiole` is active, this math runs on the isolated, amputated blade contour ($\text{Blade}_{\text{Contour}}$):
$$\text{Solidity}=\frac{\text{Area}_{\text{Blade\_Contour}}}{\text{Area}_{\text{Hull}}}$$
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
       (p_flair) ====> '._       _.' <----- Sustained Expansion Triggered
                          |  |        [======= Digital Amputation Line =======]
                          |  |     
                          |  |     <---- Moving Median Baseline Measured
                          |  |
     Stem Attachment ===> \__/
       (p_end)
### The Pathing & Flare Separation Logic


1. **Origin Anchoring ($p_{end}$):** The system calculates Euclidean distance vectors from the Centroid to every coordinate on the continuous outer boundary. The maximum value identifies the tail tip where the petiole was cut from the plant:
$$p_{end}=\arg\max_{p\in\text{contour}}\|p-\text{CoM}\|$$
2. **Sessile (Stemless) Abort Guard:** Before mapping the stem, the script measures the contour's width near $p_{end}$ over a localized window of steps. If this base width exceeds $15\%$ of the overall leaf width, the algorithm identifies the specimen as a stemless (sessile) leaf. It safely aborts the tracker, bypassing amputation to prevent cutting the leaf apex.
3. **Bilateral Contour Walk:** If a stem is validated, starting at $p_{end}$, the loop marches symmetrically outward in both clockwise and counter-clockwise directions along the contour index array.
4. **Statistical Median Baseline:** To avoid being tricked by tears, jagged cuts, or immediate flare artifacts right at the base of the stem, the program monitors the first $1.5\%$ of the total contour point array to establish a true average thickness baseline using a median calculation:
$$\text{Baseline\_Width}=\text{median}(local\_width_{1\dots i})$$
5. **Sustained Flare Condition:** As the tracking path travels up the stem, it evaluates two strict conditions before it can call a point the "leaf blade":
   * **Minimum Travel Constraint:** The accumulated path length must be greater than a baseline minimum ($10\%$ of global leaf length) to stop short petioles from triggering early.
   * **Sustained Expansion Run:** The local width must exceed the baseline by the `flare_sensitivity` coefficient. To ensure a small structural bump doesn't falsely halt tracking, this expansion must hold true continuously for a specific number of consecutive steps (`consecutive_triggers_needed`).
6. **Visual Rollback Optimization:** Once a sustained flare is confirmed, the engine steps back along the path history to the exact index where the widening first began, assigning the **Magenta Flare Dot** ($p_{flair}$) cleanly at the true anatomical intersection.
7. **Visual Rollback & Digital Amputation:** Once a sustained flare is confirmed, the engine steps back along the path history to the exact index where the widening first began, assigning the **Magenta Flare Dot** ($p_{flair}$). It then isolates all contour indices located above this boundary line, creating a second contour representation: the amputated **blade-only contour** (`blade_cnt`).

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
* **Red Node:** The base attachment tip of the petiole tail (where it is cut from the stem).
* **Magenta Node:** The identified petiole flare entry point into the leaf blade.
* **Orange Ribbon Line:** The dynamically traced center-line path running through the core of the petiole.
* **Cyan Line:** The digital amputation cut-line slicing across the base of the blade (only visible when `--petiole` is active and a petiole is successfully amputated).
* **Thin Grey Frame:** The minimum area enclosing bounding box mapping the main growth orientation axes.
* **Integrated Metadata Panel:** A rendered dashboard painted directly onto the center of the canvas detailing identification hashes, pixel measurements, calibrated metric calculations, and shape ratios.
---

## Relational Database Fields

All numerical calculations are exported cleanly to `leaf_comprehensive_morphometrics.csv` with the following structures:

| CSV Column Identifier | Data Type | Analytical Description |
| :--- | :--- | :--- |
| `Source_File` | String | System name of the input image file. |
| `Scan_DPI` | Integer | Resolution value parsed from metadata header or program default. |
| `Leaf_Hash_ID` | String | Unique 8-character cryptographic hash signature generated from the raw intact physical footprint of the specimen scan. |
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
| `Degree_of_Lobing` | Float | Geometric ratio ($0.0$ to $1.0$) indicating edge complexity and sinus depths. Calculated *exclusively* on the isolated blade contour when `--petiole` is enabled to ensure biological accuracy. |
---
# Safrole Plotter

This documentation provides comprehensive instructions for operators utilizing the packaged, standalone executable version of the Column/Row Mapping Visualizer, `Safrole_Plotter.exe`. This application is designed to ingest raw data from tabular spreadsheets and text files (such as `.xlsx`, `.xls`, `.csv`, or `.tsv`) and project them into structured, publication-quality 2D density heatmaps, 3D topological surfaces, bar/whisker categorical plots, or 2D/3D scatter graphs with polynomial curve fitting. Because the tool operates purely through a Command Line Interface (CLI), you do not need a Python environment or separate code compilers to run it; all required math, interpolation, and rendering engines are completely self-contained within the executable binary.

To execute the application, open your operating system's terminal (Command Prompt or PowerShell on Windows, Terminal on macOS/Linux), navigate to the directory containing your compiled binary, and run the executable by passing your data file path and desired operational configurations as arguments.

---

## Command Line Arguments Reference

The behavior of the application is altered using explicit command switches. These arguments are classified into structural execution blocks:

### Data File Options

* `--file [PATH]` or `--csv [PATH]` *(Required)*: Specifies the relative or absolute system path to your target data file (`.csv`, `.tsv`, `.xlsx`, or `.xls`).
* `--sheet [NAME | INT]` *(Default: 0)*: For Excel files, specifies the target sheet name or 0-indexed sheet index (e.g., `--sheet 0` or `--sheet "Sheet1"`).
* `--delimiter [STR]` *(Default: `,`)*: The character pattern splitting columns in text files (e.g., use `\t` for tab-separated data).

### Variable Selection & Data Slicing

You can extract data from either **columns** or **rows** and slice specific sub-regions:

* `--x-col [STR]` / `--y-col [STR]` / `--z-col [STR]`: Defines columns as data sources. Accepts Excel letters (e.g., `A`, `F`, `AA`) or 0-indexed integer strings (e.g., `0`, `5`). Defaults: X = `A`, Y = `B`, Z = `C`.
* `--x-row [INT]` / `--y-row [INT]` / `--z-row [INT]`: Defines 1-indexed row numbers as data sources (e.g., `--x-row 1` to use Row 1 as X values).
* `--x-range [START] [END]` / `--y-range [START] [END]` / `--z-range [START] [END]`: Defines specific slice boundaries for individual variables:
* **When using `--x-col`:** Range values represent **1-indexed row limits** (e.g., `--x-range 2 60` reads rows 2 through 60).
* **When using `--x-row`:** Range values represent **column limits** using letters or indices (e.g., `--x-range B Z` reads columns B through Z).


* `--rows [START] [END]`: Global fallback row boundary applied to all column selections (1-indexed).
* `--cols [START] [END]`: Global fallback column boundary applied to all row selections (Excel letters or 0-indexed integers).

### Custom Axis Range Bounds

* `--xlim [MIN] [MAX]`: Sets custom numerical boundaries for the X-axis view (e.g., `--xlim 0 50`).
* `--ylim [MIN] [MAX]`: Sets custom numerical boundaries for the Y-axis view.
* `--zlim [MIN] [MAX]`: Sets custom numerical boundaries for the Z-axis view or colorbar limits.

### Curve Fitting & Extrapolation (2D Scatter Mode Only)

* `--fit-degree [1 | 2 | 3 | 4 | 5]`: Fits an algebraic polynomial trendline to your 2D scatter coordinates. Automatically calculates and prints the resulting algebraic equation and $R^2$ correlation metric directly to your terminal console.
* `1` = Linear ($y = mx + b$)
* `2` = Quadratic ($y = ax^2 + bx + c$)


* `--project [FLOAT]` *(Default: 0.0)*: Decimal fraction specifying how far to project/extrapolate the trendline beyond your actual dataset's boundaries (e.g., `--project 0.5` extends the line outward by 50% on both ends).
* `--fit-ci`: Calculates and projects a 95% confidence interval using the covariance matrix. **This uncertainty band is exclusively rendered on the extrapolated portions of the line** to visually represent forecasting margins of error.

### Axis Scaling & Transformations

* `--scale-x`, `--scale-y`, `--scale-z` *(Default: 1.0)*: Decimal multipliers applied directly to raw data prior to rendering (useful for unit conversions, e.g., meters to millimeters).
* `--log-x`, `--log-y`, `--log-z`: Flags that apply a base-10 logarithmic scale to the chosen axis. If target data contains values less than or equal to zero, the application automatically performs a linear offset shift ($+10^{-6}$) to prevent runtime mathematical exceptions.

### Presentation & Aesthetics

* `--mode [scatter | bar | boxplot | whisker | surface | heatmap]` *(Default: scatter)*: Chooses the rendering layout:
* `scatter`: Renders 2D point plots (or 3D spatial plots if `--scatter-3d` is passed).
* `bar`: Renders vertical bar charts for categorical or series data.
* `boxplot` or `whisker`: Groups Y values by X category and renders statistical distribution boxes with whiskers and medians.
* `heatmap`:
* **Without Z Source:** Renders a **2D Density Heatmap (Frequency Distribution)** of X vs Y.
* **With Z Source:** Generates an interpolated 2D top-down grid map of Z values.


* `surface`: Interpolates a 3D perspective landscape geometry requiring X, Y, and Z.


* `--scatter-3d`: Forces `scatter` mode to render an interactive 3-variable spatial plot utilizing X, Y, and Z columns together.
* `--res [INT]` *(Default: 30)*: Sets internal interpolation grid resolution or histogram bin count ($N \times N$). Higher numbers create smoother graphic outputs.
* `--cmap [STR]` *(Default: viridis)*: Applies a Matplotlib colormap profile (e.g., `plasma`, `magma`, `inferno`, `cividis`, `coolwarm`, `seaborne`).
* `--xlabel`, `--ylabel`, `--zlabel` *(Default: Automated)*: Replaces default structural axis descriptions with custom labels.
* `--hide`: Runs data loading, parsing, and diagnostic checks natively in your terminal console without spawning a graphical display window.

---

## Detailed Step-by-Step Usage Examples

### Example 1: 2D Density Heatmap from Sliced Excel Columns

To evaluate the 2D frequency distribution between Column `F` and Column `R` from an Excel spreadsheet, skipping header row 1 and analyzing rows 2 through 60:

```
Safrole_Plotter.exe --file "C:\Data\master.xlsx" --x-col F --y-col R --x-range 2 60 --y-range 2 60 --mode heatmap

```

### Example 2: 3D Surface Interpolation with Individual Variable Ranges

To generate an interpolated 3D surface mesh using Column `A` (X), Column `B` (Y), and Column `H` (Z) across rows 10 to 100:

```
Safrole_Plotter.exe --file data.csv --x-col A --y-col B --z-col H --rows 10 100 --mode surface --res 100 --cmap magma

```

### Example 3: Categorical Boxplot from Row Data Sections

If your dataset is organized horizontally across rows (e.g., Row 1 contains category names across columns `B` through `Z`, and Row 2 contains measured values):

```
Safrole_Plotter.exe --file "samples.xlsx" --x-row 1 --x-range B Z --y-row 2 --y-range B Z --mode boxplot --ylabel "Absorbance (AU)"

```

### Example 4: 2D Scatter Plot with Polynomial Fitting & Extrapolation

To plot a scatter chart from Column `2` vs Column `3`, fit a 2nd-degree quadratic curve, project it 25% beyond the data bounds, and show 95% confidence bands:

```
Safrole_Plotter.exe --file experiment.csv --x-col 2 --y-col 3 --x-range 5 50 --y-range 5 50 --mode scatter --fit-degree 2 --project 0.25 --fit-ci

```
---
# Future Plans

* **Manual Petiole Tracking:** A popup window where you place a series of points to track the petiole manually and the program connects the dots instead of finding the petiole itself.
* **Refine Safrole_Plotter:** 