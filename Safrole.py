import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import argparse
import sys
import os

def parse_args():
    parser = argparse.ArgumentParser(
        description="Flexible Column-Mapping Visualizer with Curve Fitting, 3D Scatter, & Range Bounds",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- VISUALIZATION MODE ---
    mode_group = parser.add_argument_group('Visualization Mode')
    mode_group.add_argument('--mode', type=str, default='surface', choices=['surface', 'heatmap', 'scatter'],
                            help="Choose layout: 'surface' (3D surface), 'heatmap' (2D grid), or 'scatter' (Point plot).")
    mode_group.add_argument('--scatter-3d', action='store_true',
                            help="Force 'scatter' mode to render a 3-variable spatial plot using X, Y, and Z columns.")

    # --- DATA SOURCE & COLUMN DEFINITION ---
    data_group = parser.add_argument_group('Data Selection & Columns')
    data_group.add_argument('--csv', type=str, required=True, help="Path to the CSV file.")
    data_group.add_argument('--x-col', type=int, default=0, help="0-indexed column for X axis data.")
    data_group.add_argument('--y-col', type=int, default=1, help="0-indexed column for Y axis data.")
    data_group.add_argument('--z-col', type=int, default=2, help="0-indexed column for Z data (Surface, Heatmap, or 3D Scatter).")
    data_group.add_argument('--delimiter', type=str, default=',', help="CSV field delimiter.")

    # --- CUSTOM AXIS RANGES ---
    range_group = parser.add_argument_group('Custom Axis Range Bounds')
    range_group.add_argument('--xlim', type=float, nargs=2, metavar=('MIN', 'MAX'), help="Set custom X-axis limits (e.g., 0 50)")
    range_group.add_argument('--ylim', type=float, nargs=2, metavar=('MIN', 'MAX'), help="Set custom Y-axis limits")
    range_group.add_argument('--zlim', type=float, nargs=2, metavar=('MIN', 'MAX'), help="Set custom Z-axis limits")

    # --- CURVE FITTING & EXTRAPOLATION (2D SCATTER ONLY) ---
    fit_group = parser.add_argument_group('Curve Fitting & Extrapolation (2D Scatter Mode Only)')
    fit_group.add_argument('--fit-degree', type=int, default=None, choices=[1, 2, 3, 4, 5],
                            help="Fit a polynomial curve to 2D scatter data. 1 = Linear, 2 = Quadratic, etc.")
    fit_group.add_argument('--project', type=float, default=0.0, 
                            help="Decimal fraction to extrapolate the fit line past the data range (e.g., 0.5 for a 50%% extension).")
    fit_group.add_argument('--fit-ci', action='store_true', 
                            help="Plot a 95%% confidence uncertainty band ONLY on the extrapolated (projected) areas of the line.")

    # --- AXIS DATA SCALING ---
    scale_group = parser.add_argument_group('Axis Scaling')
    scale_group.add_argument('--scale-x', type=float, default=1.0, help="Multiplier scalar applied to X axis data.")
    scale_group.add_argument('--scale-y', type=float, default=1.0, help="Multiplier scalar applied to Y axis data.")
    scale_group.add_argument('--scale-z', type=float, default=1.0, help="Multiplier scalar applied to Z axis data.")

    # --- SELECTIVE LOG SCALING ---
    log_group = parser.add_argument_group('Logarithmic Scaling (Base 10)')
    log_group.add_argument('--log-x', action='store_true', help="Apply log10 scale to the X axis.")
    log_group.add_argument('--log-y', action='store_true', help="Apply log10 scale to the Y axis.")
    log_group.add_argument('--log-z', action='store_true', help="Apply log10 scale to the Z data.")

    # --- CUSTOM AXIS LABELS ---
    label_group = parser.add_argument_group('Custom Axis Labels')
    label_group.add_argument('--xlabel', type=str, default=None, help="Custom text label for the X axis.")
    label_group.add_argument('--ylabel', type=str, default=None, help="Custom text label for the Y axis.")
    label_group.add_argument('--zlabel', type=str, default=None, help="Custom text label for the Z axis / Colorbar.")

    # --- GRID PROCESSING ---
    grid_group = parser.add_argument_group('Grid Processing')
    grid_group.add_argument('--res', type=int, default=100, help="Grid resolution for surface/heatmap interpolation.")

    # --- BASIC AESTHETICS ---
    plot_group = parser.add_argument_group('Basic Plotting')
    plot_group.add_argument('--cmap', type=str, default='viridis', help="Colormap selection.")
    plot_group.add_argument('--hide', action='store_true', help="Process data without opening the GUI window.")

    return parser.parse_args()

def handle_log_transform(data, axis_name):
    if np.any(data <= 0):
        print(f"Warning: {axis_name} data contains values <= 0. Automatically shifting for Log10 compatibility.")
        min_val = np.min(data)
        data = data - min_val + 1e-6
    return data

def main():
    args = parse_args()

    if not os.path.exists(args.csv):
        print(f"Error: File '{args.csv}' not found.")
        sys.exit(1)

    # Determine whether we need 2 or 3 columns based on visual parameters
    use_3d = (args.mode != 'scatter' or args.scatter_3d)

    print(f"Parsing '{args.csv}'...")
    try:
        raw_data = np.genfromtxt(args.csv, delimiter=args.delimiter, invalid_raise=False)
        
        max_col_needed = max(args.x_col, args.y_col, args.z_col) if use_3d else max(args.x_col, args.y_col)
        
        if raw_data.ndim < 2 or raw_data.shape[1] <= max_col_needed:
            print(f"Error: CSV file missing required columns.")
            sys.exit(1)
            
        raw_x = raw_data[:, args.x_col]
        raw_y = raw_data[:, args.y_col]
        raw_z = raw_data[:, args.z_col] if use_3d else np.zeros_like(raw_x)
        
        valid_mask = (~np.isnan(raw_x) & ~np.isnan(raw_y) & ~np.isnan(raw_z)) if use_3d else (~np.isnan(raw_x) & ~np.isnan(raw_y))
        raw_x, raw_y, raw_z = raw_x[valid_mask], raw_y[valid_mask], raw_z[valid_mask]
        
    except Exception as e:
        print(f"Failed to process CSV file layout: {e}")
        sys.exit(1)

    # Apply Multiplier Scaling
    scaled_x = raw_x * args.scale_x
    scaled_y = raw_y * args.scale_y
    scaled_z = raw_z * args.scale_z

    if args.hide:
        print("Headless mode active. Data validation pass complete.")
        sys.exit(0)

    # Base setup for standard 2D plots
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Pre-process Log transformations on standard arrays
    if args.log_x:
        scaled_x = handle_log_transform(scaled_x, "X")
        ax.set_xscale('log')
    if args.log_y:
        scaled_y = handle_log_transform(scaled_y, "Y")
        ax.set_yscale('log')

    # Resolve Labels
    x_sfx = " (Log10)" if args.log_x else " (Scaled)"
    y_sfx = " (Log10)" if args.log_y else " (Scaled)"
    z_sfx = " (Log10)" if args.log_z else " (Scaled)"
    
    final_xlabel = args.xlabel if args.xlabel is not None else f"Column {args.x_col}{x_sfx}"
    final_ylabel = args.ylabel if args.ylabel is not None else f"Column {args.y_col}{y_sfx}"
    final_zlabel = args.zlabel if args.zlabel is not None else f"Column {args.z_col}{z_sfx}"

    # -----------------------------------------------------------------
    # VISUALIZATION MODE ROUTER
    # -----------------------------------------------------------------
    if args.mode == 'scatter':
        if args.scatter_3d:
            print(f"Plotting {len(scaled_x)} points in 3D Spatial Scatter Mode...")
            plt.close(fig)  # Discard the 2D plane framework
            
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')
            
            if args.log_z:
                scaled_z = handle_log_transform(scaled_z, "Z")
                # Note: Matplotlib doesn't support a true native zscale('log') on 3D axes,
                # so handle_log_transform will execute log-shifting directly into data space.
            
            # Draw point cluster colored dynamically by their depth elevation
            sc = ax.scatter(scaled_x, scaled_y, scaled_z, c=scaled_z, cmap=args.cmap, alpha=0.8, edgecolors='none')
            cbar = fig.colorbar(sc, shrink=0.6, aspect=12)
            cbar.set_label(final_zlabel)
            
            ax.set_zlabel(final_zlabel)
            if args.zlim:
                ax.set_zlim(args.zlim)
                
            if args.fit_degree is not None:
                print("Warning: Curve fitting functions are restricted to 2D scatter spaces. Skipping trendline.")
        else:
            print(f"Plotting {len(scaled_x)} points in 2D Scatter Mode...")
            ax.scatter(scaled_x, scaled_y, color='darkblue', alpha=0.7, label='Data Points', edgecolors='none', zorder=5)
            
            # Polynomial Curve Matching & Uncertainty Extrapolation
            if args.fit_degree is not None:
                print(f"Calculating polynomial curve fit (Degree={args.fit_degree})...")
                fit_mask = np.isfinite(scaled_x) & np.isfinite(scaled_y)
                
                # Fetch both coefficients and the covariance matrix
                coefficients, covariance = np.polyfit(
                    scaled_x[fit_mask], scaled_y[fit_mask], args.fit_degree, cov=True
                )
                polynomial = np.poly1d(coefficients)
                
                # Calculate the R-squared value on the real data
                y_fit = polynomial(scaled_x[fit_mask])
                y_mean = np.mean(scaled_y[fit_mask])
                ss_res = np.sum((scaled_y[fit_mask] - y_fit)**2)
                ss_tot = np.sum((scaled_y[fit_mask] - y_mean)**2)
                r_squared = 1 - (ss_res / ss_tot)
                
                # Print the algebraic equation and R-squared to the terminal
                print("\n--- FITTED POLYNOMIAL EQUATION ---")
                print(polynomial)
                print(f"R-squared: {r_squared:.4f}")
                print("----------------------------------\n")
                
                # Determine boundaries for Extrapolation
                x_min_data = scaled_x[fit_mask].min()
                x_max_data = scaled_x[fit_mask].max()
                x_span = x_max_data - x_min_data
                
                line_start = x_min_data - (x_span * args.project)
                line_end = x_max_data + (x_span * args.project)
                
                # If explicit axis limits are provided, extend the line to meet the edge of the screen
                if args.xlim:
                    line_start = min(line_start, args.xlim[0])
                    line_end = max(line_end, args.xlim[1])
                
                # Generate the smooth line coordinates across the entire (projected + real) range
                x_line = np.linspace(line_start, line_end, 500)
                y_line = polynomial(x_line)
                
                # Plot the solid trendline
                fit_lbl = f"Fit Line (Degree {args.fit_degree} | R^2={r_squared:.2f})" if args.fit_degree > 1 else f"Linear Fit (R^2={r_squared:.2f})"
                ax.plot(x_line, y_line, color='red', lw=2.5, linestyle='--', label=fit_lbl, zorder=4)
                
                # Calculate and project expanding uncertainty band ONLY on extrapolated tails
                if args.fit_ci:
                    # Construct a design matrix for the polynomial terms
                    TT = np.vstack([x_line**(args.fit_degree - i) for i in range(args.fit_degree + 1)]).T
                    
                    # Calculate variance (TT * Covariance * TT_transpose) and extract standard error
                    y_variance = np.sum((TT @ covariance) * TT, axis=1)
                    y_std_error = np.sqrt(y_variance)
                    
                    # Use 2 standard deviations for an approximate 95% confidence band
                    ci = 2 * y_std_error
                    
                    # Boolean Mask: Only True where the line exists outside the boundaries of the real dataset
                    extrapolated_mask = (x_line < x_min_data) | (x_line > x_max_data)
                    
                    ax.fill_between(x_line, y_line - ci, y_line + ci, where=extrapolated_mask, 
                                    color='red', alpha=0.2, label="Extrapolation Uncertainty (95%)", zorder=3)
                
                ax.legend(loc='best')

    else:
        # Interpolation Mesh Logic (For Heatmap / Surface Modes)
        try:
            from scipy.interpolate import griddata
        except ImportError:
            print("Error: SciPy required for matrix mesh generation. Run: pip install scipy")
            sys.exit(1)

        xi = np.linspace(scaled_x.min(), scaled_x.max(), args.res)
        yi = np.linspace(scaled_y.min(), scaled_y.max(), args.res)
        X, Y = np.meshgrid(xi, yi)

        Z = griddata((scaled_x, scaled_y), scaled_z, (X, Y), method='linear')
        nan_mask = np.isnan(Z)
        if np.any(nan_mask):
            Z[nan_mask] = griddata((scaled_x, scaled_y), scaled_z, (X, Y), method='nearest')[nan_mask]

        norm = None
        if args.log_z:
            Z = handle_log_transform(Z, "Z")
            norm = LogNorm(vmin=max(1e-6, Z.min()), vmax=Z.max())

        if args.mode == 'surface':
            plt.close(fig)
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')
            img_plot = ax.plot_surface(X, Y, Z, cmap=args.cmap, norm=norm, edgecolor='none', antialiased=True)
            ax.set_zlabel(final_zlabel)
            if args.zlim:
                ax.set_zlim(args.zlim)
        else:
            img_plot = ax.pcolormesh(X, Y, Z, cmap=args.cmap, norm=norm, shading='auto')
        
        cbar = fig.colorbar(img_plot, shrink=0.6, aspect=12)
        cbar.set_label(final_zlabel)
        if args.zlim and args.mode == 'heatmap':
            img_plot.set_clim(args.zlim[0], args.zlim[1])

    # Assign Universal Configuration Overrides
    if args.xlim:
        ax.set_xlim(args.xlim)
    if args.ylim:
        ax.set_ylim(args.ylim)

    ax.set_title(f"Data Visualizer [{args.mode.upper()} MODE]")
    ax.set_xlabel(final_xlabel)
    ax.set_ylabel(final_ylabel)
    ax.grid(True, linestyle=':', alpha=0.6)
    
    plt.show()

if __name__ == "__main__":
    main()