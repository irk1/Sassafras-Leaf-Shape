import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- UPGRADE THE SAVE BUTTON ---
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

# 1. LOAD THE EXCEL DATA
file_path = r"C:\Users\izzyk\Downloads\Cycle 1 data(1).xlsx"
df = pd.read_excel(file_path)

# --- SET YOUR COLUMNS AND DECIMALS HERE ---
x_col = 'Physical_Edge_Area_Ratio_cm1'
y_col = 'Qamb'
category_col = 'Shape'
maxFit = 2
titleText = 'Calibrated Edge Area Ratio vs Light Intensity'
xAxisText = 'Edge Area Ratio'
yAxisText = 'Light Quanta (qAmb) umol^-2*s^-1'
legendLoc = 'best' #'best', 'upper right', 'upper left', 'lower left', 'lower right', 'right', 'center left', 'center right', 'lower center', 'upper center', 'center'

# Change this number to set exactly how many decimal places you want for R^2 and the Equation
r2_decimals = 4 

# Drop any blank rows in these specific columns to prevent calculation errors
df_clean = df.dropna(subset=[x_col, y_col, category_col])

# 2. CREATE FIGURE
fig, ax = plt.subplots(figsize=(10, 8))

# 3. PLOT SCATTER POINTS BY CATEGORY
# --- SET YOUR CATEGORIES AND COLORS HERE ---
color_map = {
    'Glove': '#7570b3',  # Purple
    'Mitten': '#5ab4ac', # Teal
    'Oval': '#a6dba0'    # Green
}

# Group the data by your third column and plot each group
for category, group_data in df_clean.groupby(category_col):
    dot_color = color_map.get(category, 'gray') # Defaults to gray if not in color_map
    
    ax.scatter(group_data[x_col], group_data[y_col], 
               color=dot_color, alpha=0.8, s=40, 
               label=f'{category}')

# 4. CALCULATE BEST FIT LINE BY CYCLING THROUGH DEGREES
x_all = df_clean[x_col]
y_all = df_clean[y_col]

best_r2 = -float('inf')
best_deg = 1
best_p = None

# Cycle through degrees 1 through maxFit
for deg in range(1, maxFit):
    z = np.polyfit(x_all, y_all, deg)
    p = np.poly1d(z)
    
    # Calculate R-squared for the current polynomial degree
    y_pred = p(x_all)
    ss_res = np.sum((y_all - y_pred)**2)
    ss_tot = np.sum((y_all - np.mean(y_all))**2)
    current_r2 = 1 - (ss_res / ss_tot)
    
    # Update if this is the best R-squared so far
    if current_r2 > best_r2:
        best_r2 = current_r2
        best_deg = deg
        best_p = p

# --- FORMAT THE EQUATION STRING ---
eq_terms = []
for i, coeff in enumerate(best_p.coefficients):
    power = best_deg - i
    # Format the coefficient with the specified decimal places
    coeff_str = f"{coeff:.{r2_decimals}f}" 
    
    if power == 0:
        eq_terms.append(coeff_str)
    elif power == 1:
        eq_terms.append(f"{coeff_str}x")
    else:
        eq_terms.append(f"{coeff_str}x^{power}")

# Combine the terms and cleanly format negative numbers (fixing "+ -" into "- ")
equation_str = "y = " + " + ".join(eq_terms).replace("+ -", "- ")

# Calculate a 5% buffer based on the actual data spread
x_buffer = (x_all.max() - x_all.min()) * 0.05
y_buffer = (y_all.max() - y_all.min()) * 0.05

# Generate line points strictly within the buffered data range
x_line = np.linspace(x_all.min() - x_buffer, x_all.max() + x_buffer, 200)

# Plot the red trendline and add the equation to the label via \n (new line)
ax.plot(x_line, best_p(x_line), color='red', linestyle='--', linewidth=2.5, 
        label=f'Fit Line (Degree {best_deg} | R^2={best_r2:.{r2_decimals}f})\n{equation_str}')

# 5. CUSTOMIZE LABELS, GRID, AND ZOOM
ax.set_title(titleText, fontsize=14)
ax.set_xlabel(xAxisText, fontsize=10)
ax.set_ylabel(yAxisText, fontsize=10)

# --- LOCK THE ZOOM TO THE DATA + BUFFER ---
ax.set_xlim(x_all.min() - x_buffer, x_all.max() + x_buffer)
ax.set_ylim(y_all.min() - y_buffer, y_all.max() + y_buffer)

ax.grid(True, linestyle=':', color='gray', alpha=0.5)
ax.legend(loc=legendLoc)

plt.tight_layout()
plt.show()