import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- UPGRADE THE SAVE BUTTON ---
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

# 1. LOAD THE EXCEL DATA
file_path = r"C:\Users\izzyk\Downloads\Cycle 1 data(1).xlsx"
df = pd.read_excel(file_path)

# --- SET YOUR COLUMNS AND TEXT HERE ---
y_col = 'Physical_Edge_Area_Ratio_cm1' 
category_col = 'Shape'
titleText = 'Edge:Area Ratio vs Shape'
yAxisText = 'Edge:Area Ratio'
xAxisText = 'Leaf Shape'

# Drop any blank rows in these specific columns to prevent calculation errors
df_clean = df.dropna(subset=[y_col, category_col])

# 2. CREATE FIGURE
fig, ax = plt.subplots(figsize=(10, 8))

# 3. ORGANIZE DATA AND PLOT BOXPLOT
# --- SET YOUR CATEGORIES AND COLORS HERE ---
# The order of this list determines the order they appear on the X-axis
categories = ['Glove', 'Mitten', 'Oval'] 

color_map = {
    'Glove': '#7570b3',  # Purple
    'Mitten': '#5ab4ac', # Teal
    'Oval': '#a6dba0'    # Green
}

# Extract the data arrays for each category dynamically based on the list above
data_to_plot = [df_clean[df_clean[category_col] == cat][y_col] for cat in categories]

# Plot the box and whisker
bplot = ax.boxplot(data_to_plot, patch_artist=True, labels=categories, 
                   flierprops={'marker': 'o', 'markerfacecolor': 'none', 'markeredgecolor': 'black'})

# 4. CONTROL BOXPLOT APPEARANCE & ADD FLAGS
# Apply the exact colors from your dictionary to the boxes
colors = [color_map[cat] for cat in categories]

for patch, color in zip(bplot['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_edgecolor('blue')      # Box outline color
    patch.set_alpha(0.8)             # Transparency

for whisker in bplot['whiskers']:
    whisker.set(color='blue', linewidth=1.5) # Blue whisker lines

for median in bplot['medians']:
    median.set(color='red', linewidth=2.5)   # Thick red median line
    
    # --- ADD MEDIAN FLAG ---
    y_val = median.get_ydata()[0]            # Get the exact Y value of the line
    x_val = median.get_xdata()[1]            # Get the X coordinate for the right edge of the line
    ax.text(x_val, y_val, f' {y_val:.2f}', va='center', color='red', fontsize=9, fontweight='bold')

for cap in bplot['caps']:
    cap.set(color='blue', linewidth=1.5)     # Blue end caps
    
    # --- ADD WHISKER CAP FLAGS ---
    y_val = cap.get_ydata()[0]               # Get the exact Y value of the cap
    x_val = cap.get_xdata()[1]               # Get the X coordinate for the right edge of the cap
    ax.text(x_val, y_val, f' {y_val:.2f}', va='center', color='blue', fontsize=9, fontweight='bold')

# 5. CUSTOMIZE LABELS & GRID
ax.set_title(titleText, fontsize=14)
ax.set_xlabel(xAxisText, fontsize=10)
ax.set_ylabel(yAxisText, fontsize=10)

# Rotate X-axis labels slightly for better readability
plt.xticks(rotation=45, ha='right')

ax.grid(True, linestyle=':', color='gray', alpha=0.5)

plt.tight_layout()
plt.show()