
## Leaf Morphometrics & Advanced Petiole Tracker

**Core Engine:** OpenCV (`cv2`), OpenCV Aruco (`cv2.aruco`), NumPy (`numpy`), Hashlib (`hashlib`), Pillow (`PIL`), Matplotlib (`pyplot`), `argparse`, `csv`.

This application is a highly advanced, two-pass computer vision pipeline designed for botanical phenotyping. It features built-in printable calibration target generation, optical lens distortion correction via ChArUco boards, advanced background dropping algorithms, and both automated and manual biometric tracking.

### 1. Command-Line Arguments & Configuration

The script utilizes `argparse` to route execution logic based on user flags.

* **Target Generation:** `--generate-targets` (triggers PDF/PNG generation mode), `--paper-size` (routes dimensions to `letter`, `a4`, or `arch_d`).
* **Petiole Modes:** `--petiole` (auto-tracking), `--manual-petiole` (user-guided UI).
* **Data Flow:** `--show` (visualize results), `--new-csv` (timestamped database).
* **Memory Protection:** Overrides `PIL.Image.MAX_IMAGE_PIXELS = None` to bypass decompression bombs when loading ultra-high-resolution botanical TIFFs.

### 2. Target & Scale Generator Module (`--generate-targets`)

If this flag is passed, the script bypasses image processing and acts as a localized CAD engine. It renders mathematically perfect 300 DPI PNGs for printing physical calibration tools.

* **ChArUco Board:** Generates a standard 7x5 checkerboard (`aruco.DICT_6X6_250`) with 30mm squares and 22mm internal ArUco markers.
* **2-Axis Drop-Out Grid Background:** Draws a custom metric grid (minor, major, and text lines) utilizing specific pale orange/cyan RGB values (255, 220, 180). This color profile is explicitly designed to drop out of the background during the application's LAB/HSV masking phase.
* **Standalone Scale Cards:** Tiles four 150mm linear rulers and two 50mm multi-axis crosshair targets onto a single sheet. Includes dashed cutting lines and 100mm caliper verification lines.

*(The script exits `exit(0)` immediately after generation.)*

### 3. Pass 1: Lens Calibration & Dynamic Scaling

The pipeline begins by scanning the `Scans/` directory and categorizing images into `calib_files` (contains a ChArUco board) and `leaf_files` (the actual specimens).

1. **ChArUco Detection:**
Converts the image to grayscale and uses `detector.detectMarkers` to find ArUco tags. It then interpolates these to find the inner checkerboard corners (`aruco.interpolateCornersCharuco`).


2. **Camera Matrix Generation:**
If targets are found, `aruco.calibrateCameraCharuco` calculates the focal lengths, optical centers, and a matrix of distortion coefficients (radial and tangential lens warping).


3. **Physical Pixel Density Check:**
The script takes the distance between two detected corners on the undistorted grid and compares it to the hardcoded 30.0mm square length to establish a hyper-accurate float for dynamic pixels per centimeter.


### 4. Pass 2: Specimen Processing & Advanced Masking

Iterates through all identified `leaf_files`.

* **Optical Undistortion:** If a camera matrix was generated in Pass 1, `cv.undistort` is applied to flatten out barrel/pincushion lens distortion using `cv.getOptimalNewCameraMatrix`.
* **Fallback DPI Check:** If no physical target was in the scan, it attempts to parse Pillow's `info.get('dpi')`. If that fails, it defaults to 1200 DPI.
* **LAB & HSV Drop-Out Masking:** Instead of simple grayscale thresholds, the script isolates the leaf by aggressively filtering out background grids:
* **LAB Color Space:** Isolates the Luminance channel, creating a binary mask dropping values greater than 185.
* **HSV Color Space:** Isolates the Value channel, dropping values greater than 190.
* **Bitwise Combination:** `cv.bitwise_or` fuses the masks. `cv.morphologyEx` using a 7x7 elliptical kernel performs an Open then Close sequence to eliminate noise and seal holes inside the leaf body.



### 5. Global Morphometrics

* **Contour Extraction:** Extracts external boundaries, rejecting anything smaller than 0.5% of the total image canvas.
* **Center of Mass (CoM):** Calculated using `cv.moments` ($M_{10}/M_{00}$).
* **Axes:** `cv.minAreaRect` calculates the absolute structural Leaf Length and Leaf Width regardless of angular rotation on the scanner bed.

### 6. Petiole Tracking Algorithms

The script routes to one of two tracking pipelines based on CLI arguments.

**Pipeline A: Manual Tracking (`--manual-petiole`)**

* Spawns a Matplotlib `ginput` window displaying a padded bounding-box crop of the leaf.
* The user clicks points along the stem.
* The script translates these relative cropped clicks back into absolute image coordinates.
* The first click becomes `p_end` (stem base), and the last becomes `p_flair` (blade transition). It calculates curved length by summing Euclidean distances between all clicks.

**Pipeline B: Automated Tracking (`--petiole`)**

* **Anchoring:** Finds the furthest contour point from the CoM (`p_end`).
* **Sessile Guard:** Measures contour width 1.5% of the way in. If greater than 15% of the overall leaf width, it aborts (flags as stemless).
* **The Bi-Directional Walk:** Marches along the contour boundary simultaneously clockwise and counter-clockwise.
* **Dynamic Baseline:** Records the thickness for the first 1.5% of steps (`baseline_calc_steps`) to establish a median baseline.
* **Flare Detection:** When the local thickness is greater than 1.35x the baseline for a sustained duration (`consecutive_triggers_needed`), it triggers.
* **Rollback:** Rolls back to the exact trigger start index to drop the `p_flair` dot.

**Blade Amputation (Both Pipelines)**
Once `p_flair` is known, the script slices the raw NumPy contour array. It drops all indices representing the stem, assigning the remainder to `blade_cnt`. Advanced shape metrics (Convex Hull, Degree of Lobing) are strictly calculated on this amputated blade.

### 7. Diagnostics & Export

* **Dynamic Typography:** Calculates a scale factor (`sf`) based on native image resolution to dynamically resize font size, line thickness, and dot radii so annotations are visible on both 72 DPI and 2400 DPI images.
* **Cryptographic Hashing:** Serializes the raw physical points of the contour and hashes them using `hashlib.md5().hexdigest()[:8]`. Ensures tracking uniqueness and implements a collision counter (`-1`, `-2`) if identical shapes occur.
* **CSV Export:** Converts pixel measurements to metric standard (cm and cm²), applies rounding, and maps the data to a `csv.DictWriter` payload.

Here is an extensively expanded, deep-dive architectural specification for the **Safrole Plotter**, detailing the underlying logic, error handling, and mathematical operations of the engine.

## Safrole Plotter (`Safrole_Plotter.exe`)

**Core Dependencies:** Pandas (`pandas`), Matplotlib (`matplotlib`), SciPy (`scipy`), NumPy (`numpy`), PyInstaller (for binary freezing).
**Architecture Overview:** The Safrole Plotter is a headless, frozen Python binary engineered for high-throughput scientific data visualization. It operates entirely via the Command Line Interface (CLI), allowing it to be chained into automated CI/CD pipelines, bash scripts, or batch processing workflows without requiring a localized Python environment or dependency management.

---

### 1. Advanced Data Ingestion & Parsing Engine

The ingestion module acts as the gatekeeper, normalizing messy, real-world tabular data into clean NumPy arrays ready for mathematical transformation.

* **Format Routing & Memory Management:**
* **CSV/TSV (`pandas.read_csv`):** Utilizes a dynamic regex-capable `--delimiter` flag to handle inconsistently delimited files. For massive datasets, it utilizes the `chunksize` parameter to yield data in memory-safe blocks, preventing out-of-memory (OOM) fatal errors on heavily populated arrays.
* **Excel (`pandas.read_excel`):** Hooks into the `openpyxl` engine. The `--sheet` flag accepts either the string literal of the sheet name or a 0-indexed integer.


* **Coordinate Resolution (Base-26 ASCII Math):**
* To allow human-readable inputs, the CLI accepts Excel-style column references (e.g., `--x-col AA`). The engine mathematically parses this string into a 0-indexed integer for `iloc` slicing:
* Algorithm: Iterates through characters, converting them via `ord(char) - 64`, and multiplies by powers of 26 ($Value = \sum (CharValue \times 26^{position})$).




* **Data Sanitization Cascade:**
* **Coercion:** Applies `pd.to_numeric(errors='coerce')` across the extracted slice. Any string literals (e.g., "N/A", "Error", "Null") are converted to `np.nan`.
* **Alignment:** Uses a boolean mask to execute a synchronized `.dropna()`. If a row has a valid X value but a missing Y value, the *entire row* is dropped across all axes to prevent dimension mismatch errors during plotting (`ValueError: x and y must be the same size`).



### 2. Mathematical Array Transformations

Before rendering, the raw NumPy arrays pass through a transformation matrix based on user-defined CLI flags. Operations are vectorized for speed.

* **Linear Scaling & Offsets:**
* Arrays are directly broadcasted against float arguments: `(array * --scale-axis) + --offset-axis`. This allows on-the-fly unit conversions (e.g., scaling millimeters to centimeters using `--scale-x 0.1`).


* **Logarithmic Base-10 Shifts (`--log-x/y/z`):**
* Because $\log_{10}(x)$ is mathematically undefined for $x \le 0$, blindly applying `np.log10()` to raw data causes `RuntimeWarning` exceptions and breaks plotting.
* **The Shift Mask:** The engine evaluates the array's absolute minimum (`np.min(arr)`). If $min \le 0$, the engine calculates a shift value $S = \vert{}min\vert{} + 10^{-6}$. It then applies $np.log10(arr + S)$, ensuring all values are strictly positive while preserving the relative logarithmic distribution.


* **Normalization (`--normalize-z`):**
* Optional Z-score normalization scaling: $Z = \frac{x - \mu}{\sigma}$. Useful when utilizing the Z-axis as a colormap scalar for data with extreme outliers.



### 3. Matplotlib Rendering Pipelines (`--mode`)

The plotter dynamically instantiates one of several `matplotlib.axes.Axes` objects based on the chosen topology.

* **Scatter Rendering (`mode=scatter`):**
* **2D Projection:** Standard planar mapping. Uses `--alpha` for transparency blending to reveal density in overlapping clusters.
* **3D Projection (`--scatter-3d`):** Replaces the standard axis with `projection='3d'`. Allows interactive rotation if the `--show` flag is passed before saving to disk.
* **Cmapped Z-Scalars:** If a Z-array is provided, it is routed through `matplotlib.cm.ScalarMappable`. The engine dynamically scales the colormap bounds (`--vmin`, `--vmax`) to the 5th and 95th percentiles of the Z-data by default to prevent extreme outliers from washing out the color gradient.


* **Spatial Density Heatmaps (`mode=heatmap`, no Z-data):**
* Bypasses scatter points entirely. Calculates a 2D histogram (`ax.hist2d`) based on the `--res` (resolution) parameter, generating an $N \times N$ bin matrix.
* For sparse datasets, the user can invoke `--kde` (Kernel Density Estimation), triggering `scipy.stats.gaussian_kde` to render a smooth, continuous probability density function over the coordinates instead of rigid bins.


* **Topological Surface Maps (`mode=surface` or Z-heatmap):**
* Raw scatter data is rarely perfectly gridded. To render a continuous surface, the engine must "guess" the spaces between points.
* **Meshgrid Generation:** Creates a perfect bounding box using `np.linspace` between $X_{min} \to X_{max}$ and $Y_{min} \to Y_{max}$.
* **SciPy Interpolation:** Passes the unstructured $X, Y, Z$ data into `scipy.interpolate.griddata()`. The user can dictate the topological method via `--interp`:
* `nearest`: Fast, stepped rendering (Voronoi-style).
* `linear`: Triangulates points and creates flat planes between them.
* `cubic`: Generates a hyper-smooth, differentiable surface (can produce artifacts if data points are collinear/coplanar).


* **Qhull Error Guard:** If points are perfectly collinear, `griddata` will throw a Qhull tessellation error. The plotter catches this and injects a micro-jitter ($10^{-8}$) to the coordinates to force successful triangulation.


* **Categorical Logic (`mode=boxplot`, `mode=violin`):**
* If the X-axis is string/categorical and Y is numeric, the Pandas `groupby()` function splits the Y-array into sub-arrays.
* Calculates medians, interquartile ranges (IQR), and positions outliers outside $1.5 \times IQR$.



### 4. Polynomial Algebraic Modeling & Extrapolation (`--fit-degree`)

A built-in regression engine for 2D data, leveraging NumPy's linear algebra core.

* **Least-Squares Optimization (`np.polyfit`):**
* Accepts integer degrees $1 \le d \le 5$. It returns a vector of coefficients $p$ that minimizes the squared error to the equation $y = p_0x^d + p_1x^{d-1} + \dots + p_d$.


* **Correlation & Equation Generation:**
* The engine calculates the residuals and variance to return the $R^2$ value (Coefficient of Determination), printing it directly to the console or embedding it in the plot legend.
* String formatting generates the human-readable formula: e.g., $y = 3.24x^3 - 1.1x + 4.2$.


* **Forward/Backward Extrapolation (`--project`):**
* Calculates the total X-axis domain ($\Delta = X_{max} - X_{min}$). If passed `--project 0.5`, the engine extends the model's line plotting $0.5\Delta$ into the future (right) and past (left) of the raw data.


* **Statistical Confidence Intervals (`--fit-ci`):**
* Extracts the covariance matrix ($V$) from `polyfit`.
* Calculates standard error curves across the X domain.
* Multiplies by a Z-score of $1.96$ to construct a strict 95% confidence interval.
* Uses `ax.fill_between()` to paint a transparent margin of error band behind the regression line, which mathematically widens as it extrapolates further from the known data cluster.