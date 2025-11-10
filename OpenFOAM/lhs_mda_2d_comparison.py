import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from pyDOE import lhs

def get_inverse_cdf_1d(cdf, values):
    return interp1d(
        cdf,
        values,
        bounds_error=False,
        fill_value=(values[0], values[-1])
    )

def mda_sampling(n_samples, n_candidates=5000, random_seed=None):
    if random_seed is not None:
        np.random.seed(random_seed)

    candidates = np.random.rand(n_candidates, 2)
    selected = [candidates[np.random.choice(n_candidates)]]

    for _ in range(1, n_samples):
        dists = np.linalg.norm(candidates[:, None, :] - np.array(selected)[None, :, :], axis=2)
        min_dists = np.min(dists, axis=1)
        next_idx = np.argmax(min_dists)
        selected.append(candidates[next_idx])
    
    return np.array(selected)

def get_pdf_value(direction, speed, xcenters, ycenters, pdf):
    dir_bin = np.argmin(np.abs(xcenters - direction))
    spd_bin = np.argmin(np.abs(ycenters - speed))
    return pdf[dir_bin, spd_bin]

# Set global seed for reproducibility
t = 66 #np.random.randint(low=1, high=100)
print(f"Random seed: {t}")
global_seed = t
np.random.seed(global_seed)

speed_bins, direction_bins = 50, 360
n_samples = 12

# Load data
wind_datafilename = 'wind_data_pwc.txt'
data = np.loadtxt(wind_datafilename)
wind_speed = data[:, 0]
wind_direction = data[:, 1]
print(f"Historical Wind Data size: {len(data)}")

# Compute joint PDF
hist, xedges, yedges = np.histogram2d(
    wind_direction, wind_speed,
    bins=[direction_bins, speed_bins],
    density=True
)
pdf = hist / hist.sum()
xcenters = 0.5 * (xedges[:-1] + xedges[1:])
ycenters = 0.5 * (yedges[:-1] + yedges[1:])

# Marginal and conditional CDFs
cdf_direction = np.cumsum(pdf.sum(axis=1))
cdf_direction /= cdf_direction[-1]
eps = 1e-8
for i in range(1, len(cdf_direction)):
    if cdf_direction[i] <= cdf_direction[i - 1]:
        cdf_direction[i] = cdf_direction[i - 1] + eps
cdf_direction /= cdf_direction[-1]

cdf_speed_given_direction = np.zeros_like(pdf)
for i in range(len(xcenters)):
    row = np.cumsum(pdf[i])
    if row[-1] == 0:
        row = np.linspace(0, 1, len(row))
    else:
        row /= row[-1]
    for j in range(1, len(row)):
        if row[j] <= row[j - 1]:
            row[j] = row[j - 1] + eps
    row /= row[-1]
    cdf_speed_given_direction[i] = row

# LHS samples
lhs_samples = lhs(2, samples=n_samples, criterion='c')

# MDA samples
mda_samples = mda_sampling(n_samples, random_seed=global_seed)

# Transform MDA samples
inv_cdf_direction = get_inverse_cdf_1d(cdf_direction, xcenters)
mda_directions = inv_cdf_direction(mda_samples[:, 0])
mda_speeds = np.zeros_like(mda_samples[:, 0])
for k in range(len(mda_samples)):
    dir_bin = np.argmin(np.abs(xcenters - mda_directions[k]))
    inv_cdf_speed = interp1d(
        cdf_speed_given_direction[dir_bin],
        ycenters,
        bounds_error=False,
        fill_value=(ycenters[0], ycenters[-1])
    )
    mda_speeds[k] = inv_cdf_speed(mda_samples[k, 1])

# Transform LHS samples
inv_cdf_direction = interp1d(cdf_direction, xcenters, bounds_error=False, fill_value=(xcenters[0], xcenters[-1]))
sampled_directions = inv_cdf_direction(lhs_samples[:, 0])
sampled_speeds = np.zeros(n_samples)
for k in range(n_samples):
    dir_bin = np.argmin(np.abs(xcenters - sampled_directions[k]))
    inv_cdf_speed = interp1d(
        cdf_speed_given_direction[dir_bin],
        ycenters,
        bounds_error=False,
        fill_value=(ycenters[0], ycenters[-1])
    )
    sampled_speeds[k] = inv_cdf_speed(lhs_samples[k, 1])

# PDF values at sampled points
lhs_pdf_values = np.array([
    get_pdf_value(sampled_directions[i], sampled_speeds[i], xcenters, ycenters, pdf)
    for i in range(n_samples)
])
mda_pdf_values = np.array([
    get_pdf_value(mda_directions[i], mda_speeds[i], xcenters, ycenters, pdf)
    for i in range(n_samples)
])

# Print samples and PDF values
print("\n--- LATIN HYPERCUBE SAMPLES ---")
print("Directions:", ','.join(map(lambda x: f"{x:.2f}", sampled_directions)))
print("Speeds    :", ','.join(map(lambda x: f"{x:.2f}", sampled_speeds)))
print("PDF       :", ','.join(map(lambda x: f"{x:.4f}", lhs_pdf_values)))
delta_speed = (np.max(wind_speed) - np.min(wind_speed))/n_samples
print("PDF SUM   :",np.sum(lhs_pdf_values))
print("\n--- MAXIMUM DISSIMILARITY ALGORITHM SAMPLES ---")
print("Directions:", ','.join(map(lambda x: f"{x:.2f}", mda_directions)))
print("Speeds    :", ','.join(map(lambda x: f"{x:.2f}", mda_speeds)))
print("PDF       :", ','.join(map(lambda x: f"{x:.4f}", mda_pdf_values)))
print("PDF SUM   :",np.sum(mda_pdf_values))
# Plot
plt.figure(2, figsize=(12, 6))
plt.hist2d(wind_direction, wind_speed, bins=[direction_bins, speed_bins], cmap='magma', density=True)
plt.colorbar(label='Probability Density')
plt.scatter(np.round(sampled_directions), sampled_speeds, color='yellow', s=20, alpha=1, label='LHS Samples')
plt.scatter(np.round(mda_directions), mda_speeds, color='white', s=20, alpha=1, label='MDA Samples')
plt.xlabel('Wind Direction (degrees)')
plt.ylabel('Wind Speed (m/s)')
plt.title('LHS and MDA Sampling from 2D Joint PDF')
plt.legend()
plt.tight_layout()
plt.show()
