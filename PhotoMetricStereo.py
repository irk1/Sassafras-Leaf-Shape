import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

def frankot_chellappa(p, q):
    """Integrates surface gradients into a 3D height map using Fourier Transform."""
    rows, cols = p.shape
    u = np.fft.fftfreq(cols) * 2 * np.pi
    v = np.fft.fftfreq(rows) * 2 * np.pi
    U, V = np.meshgrid(u, v)
    
    P = np.fft.fft2(p)
    Q = np.fft.fft2(q)
    
    denom = (U**2 + V**2)
    denom[0, 0] = 1.0  # Avoid division by zero
    
    Z = (-1j * U * P - 1j * V * Q) / denom
    Z[0, 0] = 0.0
    
    return np.real(np.fft.ifft2(Z))

def load_tiff(base_name):
    """Searches for the base name with common TIFF extensions and loads as grayscale."""
    for ext in ['.tiff', '.tif', '.TIFF', '.TIF']:
        path = f"{base_name}{ext}"
        if os.path.exists(path):
            return cv.imread(path, cv.IMREAD_GRAYSCALE)
    return None

print("Loading pre-aligned grayscale TIFF images...")
gray0 = load_tiff('uPS')
gray90 = load_tiff('rPS')
gray180 = load_tiff('dPS')
gray270 = load_tiff('lPS')

if any(img is None for img in [gray0, gray90, gray180, gray270]):
    raise FileNotFoundError("Could not find all 4 TIFF images. Ensure 'uPS', 'rPS', 'dPS', and 'lPS' files exist in this folder.")

# Defined light directions relative to the leaf (Top, Right, Bottom, Left)
L = np.array([
    [0.0, 0.7071, 0.7071],   # uPS: Light from Top
    [0.7071, 0.0, 0.7071],   # rPS: Light from Right
    [0.0, -0.7071, 0.7071],  # dPS: Light from Bottom
    [-0.7071, 0.0, 0.7071]   # lPS: Light from Left
])

print("Extracting surface normals...")
h, w = gray0.shape
I = np.stack([gray0, gray90, gray180, gray270], axis=-1).astype(np.float32) / 255.0
I_flat = I.reshape(-1, 4).T

# Solve the linear system: I = L * g using pseudo-inverse
L_pinv = np.linalg.pinv(L)
g = np.dot(L_pinv, I_flat).T.reshape(h, w, 3)

# Separate surface vector into X, Y, Z gradients
gx = g[:, :, 0]
gy = g[:, :, 1]
gz = g[:, :, 2]
gz[gz == 0] = 1.0  # Avoid zero division

p = gx / gz
q = gy / gz

print("Integrating gradients into 3D height map...")
height_map = frankot_chellappa(p, q)

# Normalize height map between 0 and 1 for visualization
height_map = (height_map - np.min(height_map)) / (np.max(height_map) - np.min(height_map))

print("Rendering interactive 3D Plot...")
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')

# Downsample grid resolution slightly for a highly responsive 3D viewport
scale_percent = 25 
sw = int(w * scale_percent / 100)
sh = int(h * scale_percent / 100)
height_resized = cv.resize(height_map, (sw, sh))

X = np.arange(0, sw, 1)
Y = np.arange(0, sh, 1)
X, Y = np.meshgrid(X, Y)

surf = ax.plot_surface(X, Y, height_resized, cmap='plasma', edgecolor='none', rstride=1, cstride=1)
fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Relative Height')
ax.set_title("3D Leaf Height Reconstruction")
plt.show()

# Save out the 2D depth map as a pristine TIFF
cv.imwrite("leaf_height_map.tiff", np.uint8(height_map * 255))
print("Saved final 2D depth map to 'leaf_height_map.tiff'!")