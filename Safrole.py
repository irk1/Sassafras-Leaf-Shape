import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import argparse
import sys
import os

def parse_col_idx(val):
    """
    Converts Excel column letters ('A', 'B', 'AA') or 0-indexed integers ('0', '1') 
    into a 0-indexed column integer index.
    """
    val_str = str(val).strip()
    if val_str.isdigit():
        return int(val_str)
    
    num = 0
    for char in val_str.upper():
        if 'A' <= char <= 'Z':
            num = num * 26 + (ord(char) - ord('A') + 1)
        else:
            raise ValueError(f"Invalid column identifier: '{val}'. Use integers (0, 1...) or Excel letters ('A', 'B', 'AA').")
    return num - 1

def parse_row_idx(val):
    """
    Converts 1-indexed Excel row numbers (1, 2, 100...) to 0-indexed integers.
    """
    val_str = str(val).strip()
    if val_str.isdigit():
        idx = int(val_str) - 1
        if idx < 0:
            raise ValueError(f"Row numbers must be 1-indexed (>= 1). Got '{val}'.")
        return idx
    raise ValueError(f"Invalid row number: '{val}'. Expected a positive integer (e.g., 1, 2, 10).")

def extract_vector(df, var_name, col_arg, row_arg, range_arg, global_rows, global_cols, default_col):
    """
    Extracts a 1D vector (Series) from either a row or a column based on user flags,
    applying individual range boundaries.
    """
    if row_arg is not None:
        # --- ROW MODE ---
        row_idx = parse_row_idx(row_arg)
        if row_idx >= df.shape[0]:
            raise ValueError(f"Row {row_arg} is out of bounds for file with {df.shape[0]} rows.")

        if range_arg:
            col_start = parse_col_idx(range_arg[0])
            col_end = parse_col_idx(range_arg[1])
        elif global_cols:
            col_start = parse_col_idx(global_cols[0])
            col_end = parse_col_idx(global_cols[1])
        else:
            col_start = 0
            col_end = df.shape[1] - 1

        col_start = max(0, col_start)
        col_end = min(df.shape[1] - 1, col_end)

        series = df.iloc[row_idx, col_start : col_end + 1]
        desc = f"Row {row_arg} (Cols {range_arg[0] if range_arg else col_start}..{range_arg[1] if range_arg else col_end})"
    else:
        # --- COLUMN MODE ---
        col_target = col_arg if col_arg is not None else default_col
        col_idx = parse_col_idx(col_target)
        if col_idx >= df.shape[1]:
            raise ValueError(f"Column '{col_target}' is out of bounds for file with {df.shape[1]} columns.")

        if range_arg:
            row_start = parse_row_idx(range_arg[0])
            row_end = parse_row_idx(range_arg[1])
        elif global_rows:
            row_start = parse_row_idx(global_rows[0])
            row_end = parse_row_idx(global_rows[1])
        else:
            row_start = 0
            row_end = df.shape[0] - 1

        row_start = max(0, row_start)
        row_end = min(df.shape[0] - 1, row_end)

        series = df.iloc[row_start : row_end + 1, col_idx]
        desc = f"Col {col_target} (Rows {row_start + 1}..{row_end + 1})"

    return series, desc

def parse_args():
    parser = argparse.ArgumentParser(
        description="Flexible Visualizer supporting Excel (.xlsx) & CSV, Column/Row Data Sources, and Bar/Whisker Charts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- VISUALIZATION MODE ---
    mode_group = parser.add_argument_group('Visualization Mode')
    mode_group.add_argument('--mode', type=str, default='scatter', 
                            choices=['scatter', 'bar', 'boxplot', 'whisker', 'surface', 'heatmap'],
                            help="Choose layout: 'scatter', 'bar', 'boxplot'/'whisker', 'surface', or 'heatmap'.")
    mode_group.add_argument('--scatter-3d', action='store_true',
                            help="Force 'scatter' mode to render a 3D spatial plot using X, Y, and Z sources.")

    # --- DATA SOURCE FILE ---
    data_group = parser.add_argument_group('Data File Options')
    data_group.add_argument('--file', '--csv', type=str, required=True, dest='file',
                            help="Path to the input file (.csv, .xlsx, .xls).")
    data_group.add_argument('--sheet', type=str, default='0',
                            help="Sheet name or index for Excel files (default: 0 for first sheet).")
    data_group.add_argument('--delimiter', type=str, default=',', help="CSV field delimiter.")

    # --- X VARIABLE SELECTION ---
    x_group = parser.add_argument_group('X Variable Definition')
    x_group.add_argument('--x-col', type=str, default=None, help="Column for X data (e.g., 'A', 'B', '0').")
    x_group.add_argument('--x-row', type=int, default=None, help="Row for X data (1-indexed row number, e.g., 1, 2).")
    x_group.add_argument('--x-range', type=str, nargs=2, metavar=('START', 'END'),
                         help="Range for X data. Rows if using --x-col (e.g., 2 100), or Cols if using --x-row (e.g., A Z).")

    # --- Y VARIABLE SELECTION ---
    y_group = parser.add_argument_group('Y Variable Definition')
    y_group.add_argument('--y-col', type=str, default=None, help="Column for Y data.")
    y_group.add_argument('--y-row', type=int, default=None, help="Row for Y data.")
    y_group.add_argument('--y-range', type=str, nargs=2, metavar=('START', 'END'), help="Range for Y data.")

    # --- Z VARIABLE SELECTION ---
    z_group = parser.add_argument_group('Z Variable Definition')
    z_group.add_argument('--z-col', type=str, default=None, help="Column for Z data.")
    z_group.add_argument('--z-row', type=int, default=None, help="Row for Z data.")
    z_group.add_argument('--z-range', type=str, nargs=2, metavar=('START', 'END'), help="Range for Z data.")

    # --- GLOBAL RANGE FALLBACKS ---
    fallback_group = parser.add_argument_group('Global Range Fallbacks')
    fallback_group.add_argument('--rows', type=int, nargs=2, metavar=('START', 'END'), help="Global 1-indexed row range fallback.")
    fallback_group.add_argument('--cols', type=str, nargs=2, metavar=('START', 'END'), help="Global column range fallback.")

    # --- CUSTOM AXIS RANGES ---
    range_group = parser.add_argument_group('Custom Axis Limits')
    range_group.add_argument('--xlim', type=float, nargs=2, metavar=('MIN', 'MAX'), help="Set custom X-axis limits")
    range_group.add_argument('--ylim', type=float, nargs=2, metavar=('MIN', 'MAX'), help="Set custom Y-axis limits")
    range_group.add_argument('--zlim', type=float, nargs=2, metavar=('MIN', 'MAX'), help="Set custom Z-axis limits")

    # --- CURVE FITTING & EXTRAPOLATION ---
    fit_group = parser.add_argument_group('Curve Fitting & Extrapolation (2D Scatter Mode Only)')
    fit_group.add_argument('--fit-degree', type=int, default=None, choices=[1, 2, 3, 4, 5],
                            help="Fit polynomial curve to 2D scatter data.")
    fit_group.add_argument('--project', type=float, default=0.0, 
                            help="Decimal fraction to extrapolate fit line past range.")
    fit_group.add_argument('--fit-ci', action='store_true', 
                            help="Plot a 95%% confidence uncertainty band on extrapolated regions.")

    # --- SCALING & LOG TRANSFORMS ---
    scale_group = parser.add_argument_group('Scaling & Log Transformations')
    scale_group.add_argument('--scale-x', type=float, default=1.0, help="Multiplier scalar applied to X data.")
    scale_group.add_argument('--scale-y', type=float, default=1.0, help="Multiplier scalar applied to Y data.")
    scale_group.add_argument('--scale-z', type=float, default=1.0, help="Multiplier scalar applied to Z data.")
    scale_group.add_argument('--log-x', action='store_true', help="Apply log10 scale to X axis.")
    scale_group.add_argument('--log-y', action='store_true', help="Apply log10 scale to Y axis.")
    scale_group.add_argument('--log-z', action='store_true', help="Apply log10 scale to Z axis.")

    # --- CUSTOM LABELS & AESTHETICS ---
    label_group = parser.add_argument_group('Labels & Aesthetics')
    label_group.add_argument('--xlabel', type=str, default=None, help="Custom X axis label.")
    label_group.add_argument('--ylabel', type=str, default=None, help="Custom Y axis label.")
    label_group.add_argument('--zlabel', type=str, default=None, help="Custom Z axis label.")
    label_group.add_argument('--cmap', type=str, default='viridis', help="Colormap selection.")
    label_group.add_argument('--res', type=int, default=100, help="Grid resolution for surface/heatmap interpolation.")
    label_group.add_argument('--hide', action='store_true', help="Run without displaying figure window.")

    return parser.parse_args()

def handle_log_transform(data, axis_name):
    if np.any(data <= 0):
        print(f"Warning: {axis_name} data contains values <= 0. Automatically shifting for Log10 compatibility.")
        min_val = np.min(data)
        data = data - min_val + 1e-6
    return data

def main():
    args = parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)

    chart_mode = 'boxplot' if args.mode in ['boxplot', 'whisker'] else args.mode
    use_3d = (chart_mode != 'scatter' or args.scatter_3d) and chart_mode not in ['bar', 'boxplot']

    print(f"Loading '{args.file}'...")
    ext = os.path.splitext(args.file)[1].lower()

    try:
        if ext in ['.xlsx', '.xls']:
            try:
                sheet_arg = int(args.sheet) if str(args.sheet).isdigit() else args.sheet
            except ValueError:
                sheet_arg = args.sheet
            df = pd.read_excel(args.file, header=None, sheet_name=sheet_arg)
        else:
            df = pd.read_csv(args.file, header=None, delimiter=args.delimiter, low_memory=False)
    except Exception as e:
        print(f"Failed to read file: {e}")
        sys.exit(1)

    # Extract X, Y, Z Data Vectors
    try:
        raw_x, x_desc = extract_vector(df, 'X', args.x_col, args.x_row, args.x_range, args.rows, args.cols, default_col='A')
        raw_y, y_desc = extract_vector(df, 'Y', args.y_col, args.y_row, args.y_range, args.rows, args.cols, default_col='B')
        
        if use_3d:
            raw_z, z_desc = extract_vector(df, 'Z', args.z_col, args.z_row, args.z_range, args.rows, args.cols, default_col='C')
        else:
            raw_z, z_desc = None, ""
    except Exception as err:
        print(f"Data extraction error: {err}")
        sys.exit(1)

    # Convert to numeric arrays where applicable
    num_x = pd.to_numeric(raw_x, errors='coerce')
    num_y = pd.to_numeric(raw_y, errors='coerce')
    num_z = pd.to_numeric(raw_z, errors='coerce') if use_3d else None

    is_x_numeric = num_x.notna().sum() > (len(raw_x) * 0.5)

    if is_x_numeric:
        x_vals = num_x.to_numpy() * args.scale_x
    else:
        x_vals = raw_x.astype(str).to_numpy()

    y_vals = num_y.to_numpy() * args.scale_y
    z_vals = num_z.to_numpy() * args.scale_z if use_3d else np.zeros_like(y_vals)

    # Align vector lengths if sources differ in length
    min_len = min(len(x_vals), len(y_vals))
    if use_3d:
        min_len = min(min_len, len(z_vals))

    if len(x_vals) != min_len or len(y_vals) != min_len or (use_3d and len(z_vals) != min_len):
        print(f"Warning: Vector length mismatch (X:{len(x_vals)}, Y:{len(y_vals)}" +
              (f", Z:{len(z_vals)})" if use_3d else ")") +
              f". Truncating all to shortest vector length ({min_len}).")
        x_vals = x_vals[:min_len]
        y_vals = y_vals[:min_len]
        if use_3d:
            z_vals = z_vals[:min_len]

    # Filter invalid/NaN entries
    if is_x_numeric:
        valid_mask = ~np.isnan(x_vals) & ~np.isnan(y_vals)
    else:
        valid_mask = (x_vals != '') & ~np.isnan(y_vals)

    if use_3d:
        valid_mask &= ~np.isnan(z_vals)

    x_vals, y_vals = x_vals[valid_mask], y_vals[valid_mask]
    if use_3d:
        z_vals = z_vals[valid_mask]

    # --- ERROR DIAGNOSTICS & CHECKS ---
    if len(x_vals) == 0:
        print("\n[ERROR] No valid numeric data points remain after filtering!")
        print("Diagnostic Details:")
        print(f" - X Source ({x_desc}): Extracted {len(raw_x)} items")
        print(f" - Y Source ({y_desc}): Extracted {len(raw_y)} items")
        if use_3d:
            print(f" - Z Source ({z_desc}): Extracted {len(raw_z)} items")
        print("\nPossible Causes:")
        print(" 1. The selected Y or Z column contains text or headers that got turned to NaN.")
        print(" 2. The row/column range boundaries skipped your actual numeric values.")
        print(" 3. Check if your spreadsheet has header rows you need to skip using --x-range / --y-range.")
        sys.exit(1)

    # If user selected Surface/Heatmap mode but X contains text labels, convert to numeric indices for 3D meshing
    x_ticks_labels = None
    if chart_mode in ['surface', 'heatmap'] and not is_x_numeric:
        print("Notice: X-axis contains categorical text labels. Converting to numeric positional index for Mesh Grid generation.")
        unique_labels = list(dict.fromkeys(x_vals))
        label_map = {lbl: i for i, lbl in enumerate(unique_labels)}
        x_ticks_labels = unique_labels
        x_vals = np.array([label_map[item] for item in x_vals], dtype=float)
        is_x_numeric = True

    if args.hide:
        print("Headless validation check completed successfully.")
        sys.exit(0)

    # Setup Plot
    fig, ax = plt.subplots(figsize=(10, 8))

    if args.log_x and is_x_numeric:
        x_vals = handle_log_transform(x_vals, "X")
        ax.set_xscale('log')
    if args.log_y:
        y_vals = handle_log_transform(y_vals, "Y")
        ax.set_yscale('log')

    final_xlabel = args.xlabel if args.xlabel is not None else x_desc
    final_ylabel = args.ylabel if args.ylabel is not None else y_desc
    final_zlabel = args.zlabel if args.zlabel is not None else z_desc

    # -----------------------------------------------------------------
    # VISUALIZATION MODES
    # -----------------------------------------------------------------
    if chart_mode == 'bar':
        print(f"Rendering Bar Chart for {len(x_vals)} entries...")
        cmap = plt.get_cmap(args.cmap)
        colors = cmap(np.linspace(0.2, 0.8, len(x_vals)))
        ax.bar(x_vals, y_vals, color=colors, edgecolor='black', alpha=0.85)
        if not is_x_numeric:
            plt.xticks(rotation=45, ha='right')

    elif chart_mode == 'boxplot':
        print(f"Rendering Box & Whisker Chart grouped by X categories...")
        groups = {}
        for x_item, y_item in zip(x_vals, y_vals):
            groups.setdefault(x_item, []).append(y_item)

        categories = list(groups.keys())
        box_data = [groups[cat] for cat in categories]

        bp = ax.boxplot(box_data, labels=categories, patch_artist=True,
                        boxprops=dict(facecolor='lightblue', color='blue'),
                        whiskerprops=dict(color='blue', linewidth=1.5),
                        capprops=dict(color='blue', linewidth=1.5),
                        medianprops=dict(color='red', linewidth=2))

        cmap = plt.get_cmap(args.cmap)
        colors = cmap(np.linspace(0.2, 0.8, len(categories)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        if not is_x_numeric:
            plt.xticks(rotation=45, ha='right')

    elif chart_mode == 'scatter':
        if args.scatter_3d:
            print(f"Rendering 3D Spatial Scatter Plot ({len(x_vals)} points)...")
            plt.close(fig)
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')

            if args.log_z:
                z_vals = handle_log_transform(z_vals, "Z")

            sc = ax.scatter(x_vals, y_vals, z_vals, c=z_vals, cmap=args.cmap, alpha=0.8, edgecolors='none')
            cbar = fig.colorbar(sc, shrink=0.6, aspect=12)
            cbar.set_label(final_zlabel)
            ax.set_zlabel(final_zlabel)
            if args.zlim:
                ax.set_zlim(args.zlim)
        else:
            print(f"Rendering 2D Scatter Plot ({len(x_vals)} points)...")
            ax.scatter(x_vals, y_vals, color='darkblue', alpha=0.7, label='Data Points', edgecolors='none', zorder=5)

            if args.fit_degree is not None and is_x_numeric:
                print(f"Calculating polynomial curve fit (Degree={args.fit_degree})...")
                coefficients, covariance = np.polyfit(x_vals, y_vals, args.fit_degree, cov=True)
                polynomial = np.poly1d(coefficients)

                y_fit = polynomial(x_vals)
                ss_res = np.sum((y_vals - y_fit)**2)
                ss_tot = np.sum((y_vals - np.mean(y_vals))**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

                print("\n--- FITTED POLYNOMIAL EQUATION ---")
                print(polynomial)
                print(f"R-squared: {r_squared:.4f}\n----------------------------------\n")

                x_min_data, x_max_data = x_vals.min(), x_vals.max()
                x_span = x_max_data - x_min_data
                line_start = x_min_data - (x_span * args.project)
                line_end = x_max_data + (x_span * args.project)

                if args.xlim:
                    line_start = min(line_start, args.xlim[0])
                    line_end = max(line_end, args.xlim[1])

                x_line = np.linspace(line_start, line_end, 500)
                y_line = polynomial(x_line)

                fit_lbl = f"Fit Line (Degree {args.fit_degree} | R^2={r_squared:.2f})"
                ax.plot(x_line, y_line, color='red', lw=2.5, linestyle='--', label=fit_lbl, zorder=4)

                if args.fit_ci:
                    TT = np.vstack([x_line**(args.fit_degree - i) for i in range(args.fit_degree + 1)]).T
                    y_variance = np.sum((TT @ covariance) * TT, axis=1)
                    ci = 2 * np.sqrt(y_variance)
                    extrapolated_mask = (x_line < x_min_data) | (x_line > x_max_data)
                    ax.fill_between(x_line, y_line - ci, y_line + ci, where=extrapolated_mask,
                                    color='red', alpha=0.2, label="Extrapolation Uncertainty (95%)", zorder=3)

                ax.legend(loc='best')

    else:
        # Mesh Interpolation (Surface / Heatmap)
        try:
            from scipy.interpolate import griddata
        except ImportError:
            print("Error: SciPy required for matrix mesh generation. Run: pip install scipy")
            sys.exit(1)

        xi = np.linspace(x_vals.min(), x_vals.max(), args.res)
        yi = np.linspace(y_vals.min(), y_vals.max(), args.res)
        X, Y = np.meshgrid(xi, yi)

        Z = griddata((x_vals, y_vals), z_vals, (X, Y), method='linear')
        nan_mask = np.isnan(Z)
        if np.any(nan_mask):
            Z[nan_mask] = griddata((x_vals, y_vals), z_vals, (X, Y), method='nearest')[nan_mask]

        norm = None
        if args.log_z:
            Z = handle_log_transform(Z, "Z")
            norm = LogNorm(vmin=max(1e-6, Z.min()), vmax=Z.max())

        if chart_mode == 'surface':
            plt.close(fig)
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')
            img_plot = ax.plot_surface(X, Y, Z, cmap=args.cmap, norm=norm, edgecolor='none', antialiased=True)
            ax.set_zlabel(final_zlabel)
            if args.zlim:
                ax.set_zlim(args.zlim)
            if x_ticks_labels:
                ax.set_xticks(range(len(x_ticks_labels)))
                ax.set_xticklabels(x_ticks_labels, rotation=45, ha='right')
        else:
            img_plot = ax.pcolormesh(X, Y, Z, cmap=args.cmap, norm=norm, shading='auto')
            if x_ticks_labels:
                ax.set_xticks(range(len(x_ticks_labels)))
                ax.set_xticklabels(x_ticks_labels, rotation=45, ha='right')

        cbar = fig.colorbar(img_plot, shrink=0.6, aspect=12)
        cbar.set_label(final_zlabel)
        if args.zlim and chart_mode == 'heatmap':
            img_plot.set_clim(args.zlim[0], args.zlim[1])

    # Assign Axis Limits & Labels
    if args.xlim:
        ax.set_xlim(args.xlim)
    if args.ylim:
        ax.set_ylim(args.ylim)

    ax.set_title(f"Data Visualizer [{chart_mode.upper()} MODE]")
    ax.set_xlabel(final_xlabel)
    ax.set_ylabel(final_ylabel)
    ax.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()