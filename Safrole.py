import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import argparse
import sys
import os

def parse_args():
    parser = argparse.ArgumentParser(
        description="Flexible Column-Mapping Visualizer with Custom Labels",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- VISUALIZATION MODE ---
    mode_group = parser.add_argument_group('Visualization Mode')
    mode_group.add_argument('--mode', type=str, default='surface', choices=['surface', 'heatmap'],
                            help="Choose the visual layout: 'surface' (3D plot) or 'heatmap' (2D intensity grid).")

    # --- DATA SOURCE & COLUMN DEFINITION ---
    data_group = parser.add_argument_group('Data Selection & Columns')
    data_group.add_argument('--csv', type=str, required=True, 
                            help="Path to the CSV file containing the data columns.")
    data_group.add_argument('--x-col', type=int, default=0, help="0-indexed column number for X axis data.")
    data_group.add_argument('--y-col', type=int, default=1, help="0-indexed column number for Y axis data.")
    data_group.add_argument('--z-col', type=int, default=2, help="0-indexed column number for Z (intensity) data.")
    data_group.add_argument('--delimiter', type=str, default=',', help="CSV field delimiter.")

    # --- AXIS DATA SCALING ---
    scale_group = parser.add_argument_group('Axis Scaling')
    scale_group.add_argument('--scale-x', type=float, default=1.0, help="Multiplier scalar applied to X axis data.")
    scale_group.add_argument('--scale-y', type=float, default=1.0, help="Multiplier scalar applied to Y axis data.")
    scale_group.add_argument('--scale-z', type=float, default=1.0, help="Multiplier scalar applied to Z axis data.")

    # --- SELECTIVE LOG SCALING ---
    log_group = parser.add_argument_group('Logarithmic Scaling (Base 10)')
    log_group.add_argument('--log-x', action='store_true', help="Apply log10 scale to the X axis.")
    log_group.add_argument('--log-y', action='store_true', help="Apply log10 scale to the Y axis.")
    log_group.add_argument('--log-z', action='store_true', help="Apply log10 scale to the Z (intensity) data.")

    # --- CUSTOM AXIS LABELS ---
    label_group = parser.add_argument_group('Custom Axis Labels')
    label_group.add_argument('--xlabel', type=str, default=None, help="Custom text label for the X axis.")
    label_group.add_argument('--ylabel', type=str, default=None, help="Custom text label for the Y axis.")
    label_group.add_argument('--zlabel', type=str, default=None, help="Custom text label for the Z axis / Colorbar.")

    # --- GRID PROCESSING ---
    grid_group = parser.add_argument_group('Grid Processing')
    grid_group.add_argument('--res', type=int, default=100, 
                            help="Interpolation grid resolution (NxN) to convert point data into a mesh array.")

    # --- BASIC AESTHETICS ---
    plot_group = parser.add_argument_group('Basic Plotting')
    plot_group.add_argument('--cmap', type=str, default='viridis', help="Colormap selection.")
    plot_group.add_argument('--hide', action='store_true', help="Process and scale data without opening the GUI window.")

    return parser.parse_args()

def handle_log_transform(data, axis_name):
    """Safely checks data constraints for log scaling."""
    if np.any(data <= 0):
        print(f"Warning: {axis_name} data contains values <= 0. Log transformation requires strictly positive numbers.")
        print(f"Automatically shifting {axis_name} data to be strictly positive.")
        min_val = np.min(data)
        data = data - min_val + 1e-6
    return data

def main():
    args = parse_args()

    if not os.path.exists(args.csv):
        print(f"Error: File '{args.csv}' not found.")
        sys.exit(1)

    # --- 1. LOAD TARGET COLUMNS ---
    print(f"Parsing '{args.csv}'...")
    try:
        raw_data = np.genfromtxt(args.csv, delimiter=args.delimiter, invalid_raise=False)
        
        max_col_needed = max(args.x_col, args.y_col, args.z_col)
        if raw_data.ndim < 2 or raw_data.shape[1] <= max_col_needed:
            print(f"Error: CSV does not have enough columns to satisfy indices: X={args.x_col}, Y={args.y_col}, Z={args.z_col}")
            sys.exit(1)
            
        raw_x = raw_data[:, args.x_col]
        raw_y = raw_data[:, args.y_col]
        raw_z = raw_data[:, args.z_col]
        
        valid_mask = ~np.isnan(raw_x) & ~np.isnan(raw_y) & ~np.isnan(raw_z)
        raw_x, raw_y, raw_z = raw_x[valid_mask], raw_y[valid_mask], raw_z[valid_mask]
        
    except Exception as e:
        print(f"Failed to process CSV file layout: {e}")
        sys.exit(1)

    # --- 2. APPLY AXIS SCALING ---
    scaled_x = raw_x * args.scale_x
    scaled_y = raw_y * args.scale_y
    scaled_z = raw_z * args.scale_z

    # --- 3. MESHGRID INTERPOLATION ---
    print(f"Interpolating {len(scaled_z)} points into a structured grid...")
    try:
        from scipy.interpolate import griddata
    except ImportError:
        print("Error: SciPy is required for interpolation. Run: pip install scipy")
        sys.exit(1)

    xi = np.linspace(scaled_x.min(), scaled_x.max(), args.res)
    yi = np.linspace(scaled_y.min(), scaled_y.max(), args.res)
    X, Y = np.meshgrid(xi, yi)

    Z = griddata((scaled_x, scaled_y), scaled_z, (X, Y), method='linear')
    nan_mask = np.isnan(Z)
    if np.any(nan_mask):
        Z[nan_mask] = griddata((scaled_x, scaled_y), scaled_z, (X, Y), method='nearest')[nan_mask]

    # --- 4. RENDER DATA LAYOUT ---
    if not args.hide:
        print(f"Rendering visualization mode: '{args.mode}'...")
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Configure log-scaling settings on axes based on flags
        if args.log_x:
            X = handle_log_transform(X, "X")
            ax.set_xscale('log')
        if args.log_y:
            Y = handle_log_transform(Y, "Y")
            ax.set_yscale('log')
            
        norm = None
        if args.log_z:
            Z = handle_log_transform(Z, "Z")
            norm = LogNorm(vmin=max(1e-6, Z.min()), vmax=Z.max())

        # Resolve Labels (Use user custom input, fallback to programmatic defaults)
        x_suffix = " (Log10)" if args.log_x else " (Scaled)"
        y_suffix = " (Log10)" if args.log_y else " (Scaled)"
        z_suffix = " (Log10)" if args.log_z else " (Scaled)"
        
        final_xlabel = args.xlabel if args.xlabel is not None else f"Column {args.x_col}{x_suffix}"
        final_ylabel = args.ylabel if args.ylabel is not None else f"Column {args.y_col}{y_suffix}"
        final_zlabel = args.zlabel if args.zlabel is not None else f"Column {args.z_col}{z_suffix}"

        # Handle Plot Types
        if args.mode == 'surface':
            plt.close(fig)
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')
            img_plot = ax.plot_surface(X, Y, Z, cmap=args.cmap, norm=norm, edgecolor='none', antialiased=True)
            ax.set_zlabel(final_zlabel)
        else:
            img_plot = ax.pcolormesh(X, Y, Z, cmap=args.cmap, norm=norm, shading='auto')
            
        # Add colorbar and apply custom Z/Intensity label
        cbar = fig.colorbar(img_plot, shrink=0.6, aspect=12)
        cbar.set_label(final_zlabel)
        
        # Apply standard labels
        ax.set_title(f"Data Visualizer [{args.mode.upper()} MODE]")
        ax.set_xlabel(final_xlabel)
        ax.set_ylabel(final_ylabel)
        
        plt.show()

if __name__ == "__main__":
    main()