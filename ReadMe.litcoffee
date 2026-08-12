# Leaf Morphometrics Analyzer & Safrole Plotter

A comprehensive suite for botanical computer vision analysis, automated specimen calibration, and scientific data visualization. This repository contains two core components:

1. **Leaf Analyzer (`leaf_analyzer.py`)**: A multi-pass computer vision pipeline for extracting morphometric metrics, camera lens calibration, drop-out background masking, and automated or manual petiole (stem) tracking.
2. **Safrole Plotter (`Safrole_Plotter.exe`)**: A self-contained command-line data visualization binary for generating publication-quality 2D/3D plots, statistical distributions, heatmaps, and polynomial regression models with confidence intervals.

---

# Part I: Leaf Morphometrics & Advanced Petiole Tracker

An automated, pixel-dominant computer vision pipeline designed for processing high-resolution botanical scans and overhead camera photographs. This program extracts clean geometric data from leaf specimens, establishes repeatable phenotypic profiles via localized data tracking, and uses statistical center-line modeling or manual selection to reliably separate the petiole (stem) from the leaf blade.

---

## Key Features

* **Dual Capture Source Support (Scanners & Cameras):** Processes images captured via flatbed scanners or overhead digital cameras. Includes a two-pass optical distortion correction engine to rectify camera lens warping.
* **Optical Calibration Target Generation (`--generate-targets`):** Generates printable 300 DPI ChArUco calibration boards, 2-axis drop-out background grids, and standalone cut-out scale cards formatted for standard desktop printers (HP LaserJet) or large-format poster printers (Canon imagePROGRAF TA-30).
* **LAB & HSV Drop-Out Background Filtering:** Uses a dual-color-space masking algorithm (LAB Luminance + HSV Value) to filter out printed background grid lines without clipping leaf margins or fine petioles.
* **Metadata & ChArUco Calibration:** Calculates dynamic scale factor ($\text{pixels/cm}$) using ChArUco marker interpolation. If no target is present, it falls back to native image EXIF metadata (DPI).
* **High-Resolution Specimen Management:** Bypasses default image decompression safeguards (`PIL.Image.MAX_IMAGE_PIXELS = None`) to process ultra-high-DPI scans without memory faults.
* **Dynamic UI Adaptability:** Auto-scales visual overlays, contour weights, diagnostic nodes, and typography relative to the input image dimensions.
* **Repeatable Specimen Hashing:** Generates deterministic, 8-character cryptographic MD5 IDs based on absolute contour topologies to prevent duplicate tracking or database collisions.
* **Automated & Manual Petiole Pathing:**
* **Automated (`--petiole`):** Tracks base width, filters biological bumps using localized median tracking, detects the blade flare, and calculates curved petiole length.
* **Manual (`--manual-petiole`):** Provides an interactive point-and-click Matplotlib UI for complex, damaged, or overlapping petioles.


* **Digital Blade Amputation:** Digitally severs the stem contour at the petiole flare point ($p_{\text{flair}}$). Morphometric metrics (Convex Hull, Area, Degree of Lobing) are computed exclusively on the pristine blade, preventing stem length from distorting blade shape profiles.
* **Sessile (Stemless) Safeguard:** Features an automated baseline width check at the leaf base. If a specimen naturally lacks a petiole (sessile) or is broken, the script aborts petiole tracking to prevent accidental clipping of the natural apex.

---

## Directory Structure

Upon execution, the program sets up a standardized workspace:

```text
├── leaf_analyzer.py                      # Main executable script
├── leaf_comprehensive_morphometrics.csv  # Auto-generated relational database
├── Scans/                                # Input directory for raw scans/photos
└── Annotated Scans/                      # Output directory for diagnostic sheets

```

---

## Calibration Target Generation (`--generate-targets`)

Generate printable calibration targets before capturing specimen images.

```bash
python leaf_analyzer.py --generate-targets --paper-size letter

```

| Flag | Description | Options |
| --- | --- | --- |
| `--generate-targets` | Triggers the target generation module and exits. | N/A |
| `--paper-size` | Sets page layout dimensions and unprintable margins. | `letter` (default: 8.5x11 in), `a4` (8.27x11.69 in), `arch_d` (24x36 in for Canon TA-30) |

### Generated Target Assets

1. **ChArUco Calibration Board (`charuco_board_<size>.png`):** A $7 \times 5$ grid with $30\text{ mm}$ squares and $22\text{ mm}$ internal ArUco markers, featuring a $100.0\text{ mm}$ top verification line for caliper accuracy checks.
2. **2-Axis Drop-Out Grid Background (`2_axis_scale_background_<size>.png`):** A $1\text{ mm} / 5\text{ mm} / 10\text{ mm}$ metric grid printed in drop-out cyan/blue (`RGB: 255, 220, 180`).
3. **Standalone Scale Cards (`standalone_scale_strips_<size>.png`):** Sheet containing four $150\text{ mm}$ linear rulers and two $50\text{ mm}$ crosshair targets with dashed cut lines for placement beside specimens on plain surfaces.

*Note: Print all target files at **100% Scale / Actual Size** (do NOT use "Fit to Page").*

---

## Command-Line Execution Flags

| Flag | Mode | Operational Description |
| --- | --- | --- |
| `--petiole` | Automated | Enables automated petiole tracking, flare point detection, blade amputation, and curved path length calculation. |
| `--manual-petiole` | Interactive | Spawns an interactive Matplotlib window allowing point-and-click stem tracing for complex specimens. |
| `--show` | Visual | Displays an annotated preview window for each processed leaf. *(Requires pressing `Q` or closing the window to proceed).* |
| `--new-csv` | Database | Generates a fresh timestamped CSV file (e.g., `leaf_comprehensive_morphometrics_20260812_130000.csv`) to prevent overwriting existing data. |

**Example Usage:**

```bash
# Run automated pipeline with visual previews and a timestamped CSV
python leaf_analyzer.py --petiole --show --new-csv

# Run manual interactive petiole selector
python leaf_analyzer.py --manual-petiole

```

---

## Technical Pipeline: How It Works

```text
[ Raw Input (Scanner or Camera) ] ──> [ ChArUco Lens Calibration / EXIF DPI ] ──> [ LAB & HSV Masking ]
                                                                                         │
                                                                                         ▼
[ Area & Perimeter ] <────── [ Area Filter (<0.5% Canvas) ] <────── [ Morphological Clean-up ]
        │
        ▼
[ Moment Centroid ] ──────> [ Rotated Bounding Box (L/W) ] ──────> [ Stem Terminus Localization ]
                                                                                         │
                                                                                         ▼
[ Physical Metric Output ] <─── [ Stem Flare Detection ] <─────── [ Sliding-Window Pathing ]
        │                       (With Sessile Safety Check)
        ▼
[ Amputated Blade Contour ] ──> [ Convex Hull & Lobing ] ──> [ MD5 Cryptographic Hash ] ──> [ CSV Export ]

```

### 1. Ingestion & Optical Lens Calibration (Pass 1)

* **Camera Capture Workflow:** Place the printed ChArUco board in the frame at the same focal distance as the leaf. Pass 1 detects ArUco markers (`aruco.detectMarkers`) and interpolates corners (`aruco.interpolateCornersCharuco`). `cv.calibrateCameraCharuco` computes camera focal length and lens distortion coefficients (`mtx`, `dist`). `cv.undistort` removes radial and tangential lens distortion.
* **Flatbed Scanner Workflow:** If no ChArUco board is present, the pipeline bypasses optical undistortion and reads native resolution directly from the image header metadata. If missing, it defaults to $1200\text{ DPI}$.
* **Physical Conversion Ratio:**

$$\text{Pixels\_per\_cm} = \frac{\text{DPI}}{2.54}$$



### 2. Dual Color-Space Background Drop-Out Masking

Leaves placed on the printed grid background are segmented by isolating color spaces:

* **LAB Color Space:** Isolates Luminance ($L$). Values $>185$ (bright white paper and grid lines) are thresholded out.
* **HSV Color Space:** Isolates Value ($V$). Values $>190$ are thresholded out.
* **Mask Fusion:** Combines both masks via `cv.bitwise_or`. A $7 \times 7$ elliptical kernel executes morphological opening and closing to remove line artifacts while keeping leaf boundaries intact.

### 3. Global Geometric Metrics

* **Spatial Centroid ($\text{CoM}$):** Center of Mass is resolved using physical image moments:

$$cX = \frac{M_{10}}{M_{00}}, \quad cY = \frac{M_{01}}{M_{00}}$$


* **Rotated Bounding Box:** `cv.minAreaRect` fits a minimum enclosing rectangle. The long axis defines Leaf Length, and the short axis defines Leaf Width.
* **Solidity & Lobing Coefficients:** Calculated on the isolated, amputated blade contour ($\text{Blade}_{\text{Contour}}$):

$$\text{Solidity} = \frac{\text{Area}_{\text{Blade\_Contour}}}{\text{Area}_{\text{Hull}}}$$


$$\text{Degree\_of\_Lobing} = 1.0 - \text{Solidity}$$



---

## Petiole Pathing & Amputation Logic

```text
                     _.-'''''''-._
                   .'             '.
                  /                 \
                 |                   | <--- Leaf Blade
                  \                 /
     Flare Point   '.             .'  
      (p_flair) ====> '._       _.' <----- Sustained Expansion Triggered
                         |     |       [======= Digital Amputation Line =======]
                         |     |     
                         |     |     <---- Moving Median Baseline Measured
                         |     |
     Stem Attachment ===> \___/
       (p_end)

```

1. **Origin Anchoring ($p_{\text{end}}$):** Finds the furthest boundary point from the Centroid ($\text{CoM}$):

$$p_{\text{end}} = \arg\max_{p \in \text{contour}} \Vert{}p - \text{CoM}\Vert{}$$


2. **Sessile (Stemless) Guard:** Measures width near $p_{\text{end}}$. If base width $> 15\%$ of overall leaf width, it flags the specimen as stemless (sessile) and aborts tracking.
3. **Bilateral Contour Walk:** Marches symmetrically outward (clockwise and counter-clockwise) along the boundary coordinates.
4. **Statistical Median Baseline:** Monitors the first $1.5\%$ of steps to establish average stem thickness:

$$\text{Baseline\_Width} = \text{median}(\text{local\_width}_{1 \dots i})$$


5. **Sustained Flare Condition:** Triggers when local width exceeds `flare_sensitivity` ($1.35 \times \text{baseline}$) continuously for `consecutive_triggers_needed` steps.
6. **Digital Amputation:** Steps back along path history to the flare point ($p_{\text{flair}}$), slicing the contour array to isolate the blade-only contour (`blade_cnt`).

### Manual Petiole UI (`--manual-petiole`)

When active, an interactive Matplotlib window opens:

* **Click 1:** Petiole Tip ($p_{\text{end}}$).
* **Intermediate Clicks:** Curved petiole center-line points.
* **Final Click:** Petiole Flare Point ($p_{\text{flair}}$).
* **Controls:** Left-Click (Add Point), Right-Click (Undo Point), Enter (Confirm & Process).

---

## Tuning Parameters

| Parameter Name | Target Purpose | Default Value | Tuning Impact |
| --- | --- | --- | --- |
| `flare_sensitivity` | Width multiplier indicating blade expansion | `1.35` | Lower values capture subtle tapers. Higher values require a sharp flare. |
| `min_petiole_length_px` | Minimum distance required before flare checking opens | `0.1 * leaf_length_px` | Prevents erratic tracking anomalies at a jagged cut petiole base. |
| `baseline_calc_steps` | Initial samples used to define average stem width | `max(15, int(0.015 * N))` | Increase for heavily textured petioles; decrease if petioles are short. |
| `consecutive_triggers_needed` | Step window required to confirm continuous blade flare | `max(3, int(0.005 * N))` | Higher values ignore large petiole bumps; lower values trigger instantly on crisp edges. |

---

## Diagnostic Outputs & Visual Annotations

Annotated images saved to `Annotated Scans/` include:

* **Blue Node:** Center of Mass ($\text{CoM}$ Centroid).
* **Red Node:** Base attachment tip ($p_{\text{end}}$).
* **Magenta Node:** Petiole flare entry point ($p_{\text{flair}}$).
* **Orange Ribbon Line:** Center-line path running through the petiole core.
* **Cyan Line:** Digital amputation line slicing across the base of the blade.
* **Thin Grey Frame:** Minimum area enclosing rotated bounding box.
* **Metadata Overlay Panel:** On-canvas text displaying Leaf Hash ID, pixel metrics, physical measurements ($\text{cm}$, $\text{cm}^2$), ratios, and lobing values.

---

## Comprehensive Relational Database Fields

All output metrics exported to `leaf_comprehensive_morphometrics.csv`:

| CSV Column Identifier | Data Type | Units | Analytical Description |
| --- | --- | --- | --- |
| `Source_File` | String | Filename | System name of the input image file. |
| `Scan_DPI` | Integer | DPI | Resolution parsed from ChArUco target, metadata, or system default. |
| `Leaf_Hash_ID` | String | MD5 Hash | Unique 8-character cryptographic signature generated from physical contour topology. |
| `Area_Pixels` | Integer | $\text{px}^2$ | Count of interior mask pixels defining the intact leaf structure. |
| `Perimeter_Pixels` | Integer | $\text{px}$ | Total boundary pixel count around specimen perimeter. |
| `Leaf_Length_Pixels` | Integer | $\text{px}$ | Length of the long axis of the minimum rotated bounding box. |
| `Leaf_Width_Pixels` | Integer | $\text{px}$ | Width of the short axis of the minimum rotated bounding box. |
| `Petiole_Length_Pixels` | Float | $\text{px}$ | Total distance calculated along the curved petiole core path. |
| `CoM_to_Petiole_End_Pixels` | Float | $\text{px}$ | Direct straight-line distance from Center of Mass ($\text{CoM}$) to stem base. |
| `Area_cm2` | Float | $\text{cm}^2$ | Calibrated physical surface area of the intact specimen. |
| `Perimeter_cm` | Float | $\text{cm}$ | Calibrated physical boundary length of the specimen. |
| `Leaf_Length_cm` | Float | $\text{cm}$ | Calibrated real-world length of the primary growth axis. |
| `Leaf_Width_cm` | Float | $\text{cm}$ | Calibrated real-world width of the secondary growth axis. |
| `Petiole_Length_cm` | Float | $\text{cm}$ | Calibrated anatomical length of the traced petiole path. |
| `CoM_to_Petiole_End_cm` | Float | $\text{cm}$ | Calibrated straight-line distance from Center of Mass ($\text{CoM}$) to stem base. |
| `Length_Width_Ratio` | Float | Ratio | Aspect ratio ($\text{Length} / \text{Width}$) indicating leaf elongation. |
| `Pixel_Edge_Area_Ratio` | Float | $\text{px}^{-1}$ | Raw ratio of perimeter pixels relative to area pixels. |
| `Physical_Edge_Area_Ratio_cm1` | Float | $\text{cm}^{-1}$ | Calibrated boundary-to-surface-area ratio in metric units. |
| `Degree_of_Lobing` | Float | $0.0 - 1.0$ | Geometric shape complexity index ($1.0 - \text{Solidity}$). Calculated *exclusively* on the amputated blade contour when petiole tracking is active. |

---

---

# Part II: Safrole Plotter (`Safrole_Plotter.exe`)

A standalone executable version of the Column/Row Mapping Visualizer. Ingests raw data from tabular spreadsheets (`.xlsx`, `.xls`, `.csv`, `.tsv`) and generates 2D density heatmaps, 3D topological surfaces, bar/whisker categorical plots, or 2D/3D scatter graphs with polynomial curve fitting and confidence intervals. Completely self-contained binary requiring no external Python environment.

---

## Command-Line Execution Reference

### 1. Data File & Input Options

| Switch | Syntax / Value | Default | Operational Description |
| --- | --- | --- | --- |
| `--file`, `--csv` | `[PATH]` | *Required* | System path to target data file (`.csv`, `.tsv`, `.xlsx`, `.xls`). |
| `--sheet` | `[NAME | INT]` | `0` | Excel sheet name or 0-indexed sheet integer. |
| `--delimiter` | `[STR]` | `,` | Separator character pattern for plain text files (e.g., `\t`). |

### 2. Variable Selection & Data Slicing

Data can be extracted from either **columns** or **rows**:

| Switch | Syntax / Value | Default | Operational Description |
| --- | --- | --- | --- |
| `--x-col`, `--y-col`, `--z-col` | `[STR | INT]` | `A`, `B`, `C` | Column data sources using Excel letters (`A`, `F`, `AA`) or 0-indexed integers. |
| `--x-row`, `--y-row`, `--z-row` | `[INT]` | *None* | Row data sources using 1-indexed row numbers. |
| `--x-range`, `--y-range`, `--z-range` | `[START] [END]` | *None* | Explicit range slicing. Limits rows when using `--col` flags; limits columns when using `--row` flags. |
| `--rows` | `[START] [END]` | *None* | Global fallback row range boundary (1-indexed). |
| `--cols` | `[START] [END]` | *None* | Global fallback column range boundary (Excel letters or integers). |

### 3. Axis Transformations & Custom Limits

| Switch | Syntax / Value | Default | Operational Description |
| --- | --- | --- | --- |
| `--xlim`, `--ylim`, `--zlim` | `[MIN] [MAX]` | Automated | Sets fixed visual boundaries for axes or colorbars. |
| `--scale-x`, `--scale-y`, `--scale-z` | `[FLOAT]` | `1.0` | Scalar multipliers applied directly to raw vector data prior to rendering. |
| `--log-x`, `--log-y`, `--log-z` | Flag | Off | Applies base-10 logarithmic scaling. Automatically shifts non-positive data ($+10^{-6}$) to prevent math faults. |

### 4. Presentation & Visualization Modes

| Switch | Syntax / Value | Default | Operational Description |
| --- | --- | --- | --- |
| `--mode` | `scatter | bar | boxplot | whisker | surface | heatmap` | `scatter` | Selects primary rendering topology: <br>

<br>• `scatter`: Points in 2D or 3D. <br>

<br>• `bar`: Categorical vertical bar charts. <br>

<br>• `boxplot`/`whisker`: Statistical box plots with medians and IQRs. <br>

<br>• `heatmap`: 2D density histogram (without Z) or top-down interpolated grid (with Z). <br>

<br>• `surface`: 3D perspective landscape geometry requiring X, Y, Z. |
| `--scatter-3d` | Flag | Off | Forces `scatter` mode to render an interactive 3D spatial plot. |
| `--res` | `[INT]` | `100` | Grid resolution ($N \times N$) for surface/heatmap interpolation or histogram binning. |
| `--cmap` | `[STR]` | `viridis` | Matplotlib colormap palette (e.g., `plasma`, `magma`, `inferno`, `cividis`, `coolwarm`). |
| `--xlabel`, `--ylabel`, `--zlabel` | `[STR]` | Automated | Replaces auto-generated descriptions with custom axis labels. |
| `--hide` | Flag | Off | Runs data parsing, calculations, and diagnostic checks headlessly without opening a plot window. |

### 5. Regression Modeling & Extrapolation (2D Scatter Mode)

| Switch | Syntax / Value | Default | Operational Description |
| --- | --- | --- | --- |
| `--fit-degree` | `1 | 2 | 3 | 4 | 5` | *None* | Fits a polynomial regression curve ($1=\text{linear}, 2=\text{quadratic}$, etc.). Prints formula and $R^2$ to terminal console. |
| `--project` | `[FLOAT]` | `0.0` | Decimal fraction to extrapolate trendlines beyond data bounds (e.g., `0.25` projects $25\%$ outward). |
| `--fit-ci` | Flag | Off | Renders a $95\%$ confidence interval uncertainty band derived from the covariance matrix exclusively on extrapolated line segments. |

---

## Output Variables & Diagnostic Displays

### Terminal Console Diagnostics

When executed, `Safrole_Plotter.exe` outputs diagnostic details to the terminal:

* **Extracted Data Vector Summary:** Prints source file info, loaded sheet, extracted array sizes, and truncated lengths if vector lengths differ.
* **Regression Formula Output:** Prints human-readable algebraic polynomial equations:

$$y = a_n x^n + a_{n-1} x^{n-1} + \dots + a_1 x + a_0$$


* **Goodness-of-Fit Metric ($R^2$):** Outputs the Coefficient of Determination:

$$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$



### Rendered Graphical Outputs

* **Curve Fit Line & Legend:** Displays polynomial curve overlay with degree and $R^2$ formatted directly in the legend.
* **Extrapolation Uncertainty Band (`--fit-ci`):** Displays a shaded $95\%$ confidence region ($y_{\text{line}} \pm 1.96 \times \sigma_{\text{fit}}$) rendered exclusively outside raw data boundaries.
* **Colorbar Axis:** Plots calibrated color scale with explicit labels when Z-axis metrics or heatmaps are active.

---

## Step-by-Step CLI Usage Examples

### Example 1: 2D Density Heatmap from Sliced Excel Columns

Evaluate frequency distribution between Column `F` and Column `R` from an Excel spreadsheet, skipping header row 1 and analyzing rows 2 through 60:

```bash
Safrole_Plotter.exe --file "C:\Data\master.xlsx" --x-col F --y-col R --x-range 2 60 --y-range 2 60 --mode heatmap

```

### Example 2: 3D Surface Interpolation with Individual Variable Ranges

Generate an interpolated 3D surface mesh using Column `A` (X), Column `B` (Y), and Column `H` (Z) across rows 10 to 100:

```bash
Safrole_Plotter.exe --file data.csv --x-col A --y-col B --z-col H --rows 10 100 --mode surface --res 100 --cmap magma

```

### Example 3: Categorical Boxplot from Row Data Sections

Analyze datasets organized horizontally across rows (Row 1 = category names across columns `B` to `Z`, Row 2 = measured values):

```bash
Safrole_Plotter.exe --file "samples.xlsx" --x-row 1 --x-range B Z --y-row 2 --y-range B Z --mode boxplot --ylabel "Absorbance (AU)"

```

### Example 4: 2D Scatter Plot with Polynomial Fitting & Extrapolation

Plot a scatter chart from Column `2` vs Column `3`, fit a 2nd-degree quadratic curve, project it $25\%$ beyond data bounds, and render $95\%$ confidence bands:

```bash
Safrole_Plotter.exe --file experiment.csv --x-col 2 --y-col 3 --x-range 5 50 --y-range 5 50 --mode scatter --fit-degree 2 --project 0.25 --fit-ci

```