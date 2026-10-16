#!/usr/bin/env python3
"""
Wind climatology analysis for a list of cities.

For each city in a text file the script:
  1. geocodes the name (OpenStreetMap Nominatim),
  2. finds the nearest Meteostat station that has wind observations,
  3. computes wind speed / direction statistics (incl. a Weibull fit),
  4. selects representative simulation directions with Latin Hypercube
     Sampling on the empirical direction CDF (for RANS / OpenFOAM cases),
  5. writes a wind rose, monthly statistics, an interannual trend plot and a
     summary CSV.

Usage
-----
    python wind_analysis.py                      # uses cities.txt
    python wind_analysis.py -c my_cities.txt -o results --years 10


    my_cities.txt example:
    # List of cities for wind data analysis
    # Any lines preceding with "#" are ignored
    Salt Lake City
    Phoenix
    London, ON, Canada
    Chicago
    Denver
    San Francisco
    
Wind data come from Meteostat (https://meteostat.net); please respect its
terms of use and cite the data sources it lists. Geocoding uses Nominatim,
whose usage policy requires a descriptive User-Agent and at most 1 request/s.

# Copy the requirements below into requirements.txt and install with pip:
# Install with: pip install -r requirements.txt

meteostat>=2.0.0      # Historical weather station data (v2 API: stations/hourly/daily)
geopy>=2.4.0          # City geocoding via Nominatim (OpenStreetMap)
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
scipy>=1.11.0
"""

import argparse
import re
import sys
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # headless-safe: we only write files
import matplotlib.pyplot as plt  # noqa: E402
from scipy.stats import weibull_min  # noqa: E402
from scipy.stats.qmc import LatinHypercube  # noqa: E402
from meteostat import stations, hourly, daily, Point, config  # noqa: E402
from geopy.geocoders import Nominatim  # noqa: E402
from geopy.exc import GeopyError, GeocoderTimedOut  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration (defaults; most can be overridden on the command line)
# ---------------------------------------------------------------------------
config.block_large_requests = False   # allow multi-year hourly requests

DEFAULT_CITIES_FILE = "cities.txt"             # one city name per line, '#' = comment
DEFAULT_OUTPUT_DIR = "wind_analysis_output"    # plots and CSV are written here
DEFAULT_YEARS = 20                             # length of the requested record
DEFAULT_N_LHS = 12                             # number of simulation directions
DEFAULT_SEED = 42                              # LHS seed (reproducibility)
MIN_DIR_SEPARATION = 5                         # min. angular gap between LHS directions [deg]
N_STATIONS = 5                                 # nearest candidate stations to try
CALM_THRESHOLD_MS = 0.5                        # below this: calm; direction treated as undefined [m/s]
MIN_COVERAGE_FRACTION = 0.5                    # warn if record < this fraction of requested

KMH_TO_MS = 1.0 / 3.6   # Meteostat reports wind speed in km/h

# Wind rose speed classes [m/s]
SPEED_BINS = [0, 2, 4, 6, 10, np.inf]
SPEED_LABELS = ["0–2", "2–4", "4–6", "6–10", ">10"]

COMPASS_16 = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------------------
# Geocoding and data retrieval
# ---------------------------------------------------------------------------
def load_cities(filepath: str) -> list:
    """Return city names from a text file (one per line; '#' starts a comment)."""
    path = Path(filepath)
    if not path.exists():
        sys.exit(f"[ERROR] cities file not found: '{filepath}'")
    cities = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cities.append(line)
    if not cities:
        sys.exit(f"[ERROR] no cities found in '{filepath}'")
    print(f"Loaded {len(cities)} cities from {filepath}")
    return cities


def geocode_city(city: str, geolocator) -> Optional[tuple]:
    """
    Return (lat, lon) for a city name, or None if geocoding fails.
    Retries once after a short pause on timeout.
    """
    for attempt in range(2):
        try:
            loc = geolocator.geocode(city, timeout=10)
        except GeocoderTimedOut:
            if attempt == 0:
                time.sleep(2)
                continue
            print(f"  [WARN] Geocoding timed out for '{city}'")
            return None
        except GeopyError as exc:  # unavailable, rate-limited, quota, ...
            print(f"  [WARN] Geocoding failed for '{city}': {exc}")
            return None
        if loc is None:
            print(f"  [WARN] Could not geocode '{city}'")
            return None
        return loc.latitude, loc.longitude
    return None


def find_nearest_stations(lat: float, lon: float, limit: int = N_STATIONS):
    """Return the *limit* nearest Meteostat stations as a DataFrame, or None."""
    df = stations.nearby(Point(lat, lon), limit=limit)
    return df if df is not None and not df.empty else None


def _has_wind(df) -> bool:
    """True if *df* contains at least one valid wind speed observation."""
    return df is not None and not df.empty and "wspd" in df.columns \
        and df["wspd"].notna().any()


def fetch_wind_data(station_id: str, start: datetime, end: datetime) -> tuple:
    """
    Fetch wind data for *station_id* between *start* and *end*.

    Hourly data are preferred; daily data are used only if the hourly record
    has no wind speed observations. Returns (DataFrame, resolution) where
    resolution is "hourly" or "daily"; the DataFrame is empty if neither
    source has wind data.
    """
    for resolution, getter in (("hourly", hourly), ("daily", daily)):
        try:
            df = getter(station_id, start, end).fetch()
        except Exception as exc:  # network / API errors: try the next source
            print(f"  [WARN] {resolution} fetch failed for {station_id}: {exc}")
            continue
        if _has_wind(df):
            return df.copy(), resolution
    return pd.DataFrame(), None


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def circular_mean(directions_deg: np.ndarray) -> float:
    """Circular (vector-averaged) mean of wind directions in degrees [0, 360)."""
    rad = np.deg2rad(directions_deg)
    mean = np.rad2deg(np.arctan2(np.nanmean(np.sin(rad)), np.nanmean(np.cos(rad))))
    return float(np.round(mean, 9) % 360)  # rounding avoids 360.0 from -1e-15


def resultant_length(directions_deg: np.ndarray) -> float:
    """
    Mean resultant length R̄ ∈ [0, 1].
    0 = isotropic, 1 = perfectly unidirectional.
    """
    rad = np.deg2rad(directions_deg)
    return float(np.hypot(np.nanmean(np.sin(rad)), np.nanmean(np.cos(rad))))


def circular_std(directions_deg: np.ndarray) -> float:
    """Circular standard deviation in degrees, sqrt(-2 ln R̄) (Mardia & Jupp)."""
    R = np.clip(resultant_length(directions_deg), 1e-10, 1.0)
    return float(np.rad2deg(np.sqrt(-2.0 * np.log(R))))


def sector_index(directions_deg: np.ndarray, n: int = 16) -> np.ndarray:
    """
    Index of the compass sector for each direction. Sectors are centred on the
    compass points, e.g. for n=16 "N" spans 348.75°–11.25°.
    """
    size = 360.0 / n
    return (((np.asarray(directions_deg) + size / 2) % 360) // size).astype(int)


def prevailing_sector(directions_deg: np.ndarray, n: int = 16) -> str:
    """Return the most frequent compass sector (16 points only)."""
    if n != len(COMPASS_16):
        raise ValueError(f"only n={len(COMPASS_16)} is supported")
    counts = np.bincount(sector_index(directions_deg, n), minlength=n)
    return COMPASS_16[int(np.argmax(counts))]


def speed_statistics(speeds_ms: np.ndarray) -> dict:
    """Summary statistics for wind speed [m/s]; {} if there are no valid values."""
    v = speeds_ms[~np.isnan(speeds_ms)]
    if len(v) == 0:
        return {}
    # Two-parameter Weibull fit (shape k, scale λ) to the non-zero speeds
    try:
        shape, _, scale = weibull_min.fit(v[v > 0], floc=0)
    except (ValueError, RuntimeError):
        shape, scale = np.nan, np.nan
    return {
        "count":       int(len(v)),
        "mean_ms":     float(np.mean(v)),
        "median_ms":   float(np.median(v)),
        "std_ms":      float(np.std(v)),
        "p25_ms":      float(np.percentile(v, 25)),
        "p75_ms":      float(np.percentile(v, 75)),
        "p95_ms":      float(np.percentile(v, 95)),
        "p99_ms":      float(np.percentile(v, 99)),
        "max_ms":      float(np.max(v)),
        "calm_pct":    float(100 * np.sum(v < CALM_THRESHOLD_MS) / len(v)),
        "weibull_k":   float(shape),
        "weibull_lam": float(scale),
    }


def direction_statistics(directions_deg: np.ndarray) -> dict:
    """Summary statistics for wind direction [°]; {} if there are no valid values."""
    v = directions_deg[~np.isnan(directions_deg)]
    if len(v) == 0:
        return {}
    return {
        "circ_mean_deg":     circular_mean(v),
        "circ_std_deg":      circular_std(v),
        "resultant_length":  resultant_length(v),
        "prevailing_sector": prevailing_sector(v),
    }


# ---------------------------------------------------------------------------
# Latin Hypercube Sampling of simulation directions
# ---------------------------------------------------------------------------
def lhs_simulation_directions(
    directions_deg: np.ndarray,
    n: int = DEFAULT_N_LHS,
    seed: int = DEFAULT_SEED,
) -> np.ndarray:
    """
    Select *n* representative wind directions using Latin Hypercube Sampling
    on the empirical CDF of the observed directions.

    Method
    ------
    1. Build a 1°-resolution empirical CDF of the observed directions.
    2. Divide the probability axis [0, 1] into *n* equal strata.
    3. Draw one uniform sample from each stratum (LHS).
    4. Map each sample through the inverse CDF to obtain a direction.
    5. Round to integer degrees and enforce a minimum angular separation
       (MIN_DIR_SEPARATION, measured circularly, so 359° and 2° are 3° apart)
       by nudging any too-close direction forward.

    Each probability stratum is represented by one direction, giving better
    coverage than random sampling while staying proportional to the observed
    climatology.

    Returns
    -------
    np.ndarray of up to *n* integer degrees in [0, 359], sorted ascending.
    """
    v = directions_deg[~np.isnan(directions_deg)] % 360.0
    if len(v) == 0:
        return np.array([], dtype=int)

    # Empirical CDF on 1° bins → right-edge values are 1, 2, …, 360
    counts, bin_edges = np.histogram(v, bins=np.arange(0, 361, 1))
    cdf_y = np.concatenate([[0.0], np.cumsum(counts) / counts.sum()])
    cdf_x = bin_edges.astype(float)

    # One uniform sample per stratum, reproducible via fixed seed
    u = np.sort(LatinHypercube(d=1, seed=seed).random(n=n)[:, 0])

    # Inverse CDF via linear interpolation
    raw = np.interp(u, cdf_y, cdf_x)
    dirs = np.sort(np.round(raw).astype(int) % 360)

    # Enforce minimum circular separation. The requested separation is capped
    # so that n directions can always fit on the circle.
    sep = min(MIN_DIR_SEPARATION, 360 // n)
    if len(dirs) > 1:
        for _ in range(n * 360):  # safety cap; converges long before this
            dirs = np.sort(dirs % 360)
            gaps = np.diff(np.append(dirs, dirs[0] + 360))  # includes wrap-around
            bad = np.flatnonzero(gaps < sep)
            if bad.size == 0:
                break
            i = bad[0]
            dirs[(i + 1) % len(dirs)] = (dirs[i] + sep) % 360
    return np.sort(dirs % 360)


def met_to_rans(met_dirs: np.ndarray) -> np.ndarray:
    """
    Convert meteorological wind directions (direction the wind blows FROM,
    0° = N, clockwise) to the RANS / OpenFOAM convention used here
    (0° = wind blowing W→E, 90° = S→N, 180° = E→W, 270° = N→S).

        met 0 (from N)  →  270     met 90 (from E)   →  180
        met 180 (from S) →  90     met 270 (from W)  →    0

    Formula: rans = (270 − met) mod 360. The output keeps the order of the
    input, so element i corresponds to met_dirs[i].
    """
    return (270 - np.asarray(met_dirs, dtype=int)) % 360


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def safe_name(city: str) -> str:
    """Filesystem-safe version of a city name (no spaces, commas or slashes)."""
    return re.sub(r"[^\w\-]+", "_", city).strip("_") or "city"


def plot_wind_rose(directions: np.ndarray, speeds: np.ndarray,
                   city: str, station_name: str, out_dir: Path,
                   lhs_dirs: Optional[np.ndarray] = None) -> None:
    """Stacked polar bar chart (wind rose) coloured by speed class."""
    mask = ~np.isnan(directions) & ~np.isnan(speeds)
    dirs = directions[mask] % 360
    spds = speeds[mask]
    if len(dirs) == 0:
        return

    n_sectors = len(COMPASS_16)
    sector_size = 360.0 / n_sectors
    centres = np.arange(n_sectors) * sector_size   # bars are centred on compass points
    bar_width = np.deg2rad(sector_size) * 0.9
    colors = plt.get_cmap("YlOrRd")(np.linspace(0.2, 0.95, len(SPEED_BINS) - 1))

    sectors = sector_index(dirs, n_sectors)
    fractions = np.zeros((len(SPEED_BINS) - 1, n_sectors))
    for i, (lo, hi) in enumerate(zip(SPEED_BINS[:-1], SPEED_BINS[1:])):
        in_class = (spds >= lo) & (spds < hi)
        fractions[i] = np.bincount(sectors[in_class], minlength=n_sectors) \
            / len(dirs) * 100

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 8))
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    bottoms = np.zeros(n_sectors)
    for i in range(len(SPEED_BINS) - 1):
        ax.bar(np.deg2rad(centres), fractions[i], width=bar_width,
               bottom=bottoms, color=colors[i],
               label=f"{SPEED_LABELS[i]} m/s", alpha=0.88)
        bottoms += fractions[i]

    ax.set_xticks(np.deg2rad(np.arange(0, 360, 45)))
    ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
    ax.set_title(f"Wind Rose — {city}\n{station_name}", pad=20, fontsize=13,
                 fontweight="bold")

    if lhs_dirs is not None and len(lhs_dirs) > 0:
        r_max = bottoms.max()
        r_line = r_max * 1.18    # extend lines slightly beyond the bars
        r_label = r_max * 1.30
        for k, deg in enumerate(lhs_dirs):
            theta = np.deg2rad(deg)
            ax.plot([theta, theta], [0, r_line], color="#1A237E", lw=1.6,
                    ls="--", alpha=0.9, zorder=5,
                    label="LHS sim. dirs" if k == 0 else "_nolegend_")
            ax.text(theta, r_label, f"{int(deg)}°", ha="center", va="center",
                    fontsize=7.5, color="#1A237E", fontweight="bold")

    ax.legend(loc="lower right", bbox_to_anchor=(1.35, -0.08),
              title="Speed (m/s)", fontsize=9)

    plt.tight_layout()
    fname = out_dir / f"wind_rose_{safe_name(city)}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {fname.name}")


def plot_monthly_statistics(df: pd.DataFrame, city: str,
                            station_name: str, out_dir: Path) -> None:
    """Monthly mean wind speed ± 1 std, and monthly mean wind direction components."""
    if "wspd" not in df.columns or df["wspd"].dropna().empty:
        return

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df["month"] = df.index.month

    monthly_spd = (df.groupby("month")["wspd"].agg(["mean", "std"])
                   .reindex(range(1, 13)))
    months = np.arange(1, 13)

    fig, axes = plt.subplots(1, 2, figsize=(14, 4))

    ax = axes[0]
    ax.plot(months, monthly_spd["mean"], "o-", color="#1565C0", lw=2,
            label="Monthly mean")
    ax.fill_between(months,
                    monthly_spd["mean"] - monthly_spd["std"],
                    monthly_spd["mean"] + monthly_spd["std"],
                    alpha=0.2, color="#1565C0", label="±1 std")
    ax.set_xticks(months)
    ax.set_xticklabels(MONTH_LABELS)
    ax.set_ylabel("Wind Speed (m/s)")
    ax.set_title(f"Monthly Wind Speed — {city}")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    if "wdir" in df.columns and df["wdir"].notna().any():
        mean_dir = np.array([
            circular_mean(d) if len(d := df.loc[df["month"] == m, "wdir"]
                                    .dropna().values) else np.nan
            for m in months
        ])
        # Components of the unit vector pointing TOWARD the mean wind direction
        # would be (-sin, -cos); we plot the "from" direction (met convention).
        east = np.sin(np.deg2rad(mean_dir))
        north = np.cos(np.deg2rad(mean_dir))
        h = 0.38
        ax2.barh(months - h / 2, east, height=h, color="#E53935", alpha=0.75,
                 label="E–W component (+ = from E)")
        ax2.barh(months + h / 2, north, height=h, color="#43A047", alpha=0.75,
                 label="N–S component (+ = from N)")
        ax2.set_yticks(months)
        ax2.set_yticklabels(MONTH_LABELS)
        ax2.invert_yaxis()
        ax2.axvline(0, color="k", lw=0.8)
        ax2.set_xlabel("Unit-vector component of mean wind direction")
        ax2.set_title(f"Mean Wind Direction (from) — {city}")
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)
    else:
        ax2.axis("off")

    fig.suptitle(station_name, fontsize=9, color="grey")
    plt.tight_layout()
    fname = out_dir / f"monthly_{safe_name(city)}.png"
    plt.savefig(fname, dpi=150)
    plt.close(fig)
    print(f"  Saved: {fname.name}")


def plot_interannual_trend(df: pd.DataFrame, city: str,
                           station_name: str, out_dir: Path) -> None:
    """Annual mean wind speed with a linear trend (poorly covered years excluded)."""
    if "wspd" not in df.columns or df["wspd"].dropna().empty:
        return

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    grouped = df["wspd"].groupby(df.index.year)
    annual, n_obs = grouped.mean(), grouped.count()
    # Partial or gappy years (e.g. the current year) bias the trend: keep only
    # years with at least half as many observations as the best-covered year.
    annual = annual[n_obs >= 0.5 * n_obs.max()].dropna()
    if len(annual) < 3:
        return

    years = annual.index.values.astype(float)
    speeds = annual.values
    slope, intercept = np.polyfit(years, speeds, 1)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(years, speeds, color="#42A5F5", alpha=0.7, label="Annual mean")
    ax.plot(years, slope * years + intercept, "r--", lw=2,
            label=f"Trend: {slope * 10:+.3f} m/s per decade")
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean Wind Speed (m/s)")
    ax.set_title(f"Interannual Wind Speed Trend — {city}\n{station_name}")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fname = out_dir / f"trend_{safe_name(city)}.png"
    plt.savefig(fname, dpi=150)
    plt.close(fig)
    print(f"  Saved: {fname.name}")


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
def analyse_city(city: str, geolocator, out_dir: Path, start: datetime,
                 end: datetime, n_lhs: int, seed: int) -> dict:
    """Run the full pipeline for one city and return a stats dict (or {})."""
    print(f"\n{'─' * 60}")
    print(f"City: {city}")

    coords = geocode_city(city, geolocator)
    if coords is None:
        return {}
    lat, lon = coords
    print(f"  Coordinates : {lat:.4f}°, {lon:.4f}°")

    station_df = find_nearest_stations(lat, lon)
    if station_df is None:
        print(f"  [WARN] No station found for '{city}'")
        return {}

    # Walk through the candidates (nearest first). Stop at the first station
    # whose record covers a sufficient part of the requested period; otherwise
    # fall back to the candidate with the longest record.
    requested_years = (end - start).days / 365.25
    best = None  # (record_years, df, resolution, station_id, name, dist_m)
    print(f"  Fetching data {start.date()} → {end.date()} …")
    for sid, row in station_df.iterrows():
        name = str(row.get("name", sid))
        dist = row.get("distance")
        dist_m = float(dist) if pd.notna(dist) else None
        dist_str = f"{dist_m / 1000:.1f} km" if dist_m is not None else "unknown distance"
        cand, res = fetch_wind_data(sid, start, end)
        if cand.empty:
            print(f"  Trying      : {name} [{sid}], {dist_str} away … no wind data")
            continue
        wind = cand.index[cand["wspd"].notna()]
        yrs = (pd.to_datetime(wind.max()) - pd.to_datetime(wind.min())).days / 365.25
        print(f"  Trying      : {name} [{sid}], {dist_str} away … "
              f"{yrs:.1f} yr of {res} data")
        if best is None or yrs > best[0]:
            best = (yrs, cand, res, sid, name, dist_m)
        if yrs >= MIN_COVERAGE_FRACTION * requested_years:
            break

    if best is None:
        print(f"  [WARN] No wind data in any of the {len(station_df)} nearest "
              f"stations for '{city}'")
        return {}
    _, df, resolution, station_id, station_name, dist_m = best
    print(f"  Station     : {station_name} [{station_id}] ({resolution} data)")

    # Meteostat reports km/h → m/s
    for col in ("wspd", "wpgt"):
        if col in df.columns:
            df[col] = df[col] * KMH_TO_MS

    t0, t1 = pd.to_datetime(df.index.min()), pd.to_datetime(df.index.max())
    date_range = f"{t0.date()} → {t1.date()}"
    record_years = (t1 - t0).days / 365.25
    n_valid_speed = int(df["wspd"].notna().sum())
    n_valid_dir = int(df["wdir"].notna().sum()) if "wdir" in df.columns else 0
    print(f"  Records     : {len(df):,} total  |  "
          f"speed valid: {n_valid_speed:,}  |  dir valid: {n_valid_dir:,}")
    print(f"  Period      : {date_range} ({record_years:.1f} yr)")
    if record_years < MIN_COVERAGE_FRACTION * requested_years:
        print(f"  [WARN] Record covers only {record_years:.1f} of the "
              f"{requested_years:.0f} years requested; statistics, trends and "
              f"LHS directions may not be representative.")
    if resolution == "daily":
        print("  [WARN] Only daily data available: wdir/wspd are daily "
              "averages, so extremes and the direction distribution differ "
              "from hourly data.")

    speeds = df["wspd"].values.astype(float)
    directions = (df["wdir"].values.astype(float) if "wdir" in df.columns
                  else np.array([]))
    # Meteostat reports direction 0° for calm hours, which would create a
    # spurious spike at north. Direction is undefined when calm: mask it.
    directions[speeds < CALM_THRESHOLD_MS] = np.nan

    spd_stats = speed_statistics(speeds)
    dir_stats = direction_statistics(directions) if len(directions) else {}

    if spd_stats:
        print(f"  Speed       : mean={spd_stats['mean_ms']:.2f} m/s, "
              f"median={spd_stats['median_ms']:.2f} m/s, "
              f"p95={spd_stats['p95_ms']:.2f} m/s, "
              f"max={spd_stats['max_ms']:.2f} m/s, "
              f"calm={spd_stats['calm_pct']:.1f}%")
    if dir_stats:
        print(f"  Direction   : mean={dir_stats['circ_mean_deg']:.1f}°, "
              f"std={dir_stats['circ_std_deg']:.1f}°, "
              f"prevailing={dir_stats['prevailing_sector']}, "
              f"consistency={dir_stats['resultant_length']:.3f}")
    if not np.isnan(spd_stats.get("weibull_k", np.nan)):
        print(f"  Weibull     : k={spd_stats['weibull_k']:.3f}, "
              f"λ={spd_stats['weibull_lam']:.3f} m/s")

    lhs_dirs = (lhs_simulation_directions(directions, n=n_lhs, seed=seed)
                if len(directions) else np.array([], dtype=int))
    rans_dirs = met_to_rans(lhs_dirs)
    if len(lhs_dirs):
        print(f"  LHS dirs    : {', '.join(map(str, lhs_dirs))}°  "
              f"(met convention: 0°=N, clockwise, direction wind comes FROM)")
        print(f"  RANS dirs   : {', '.join(map(str, rans_dirs))}°  "
              f"(0°=W→E, 90°=S→N, 180°=E→W, 270°=N→S)")

    if len(directions):
        plot_wind_rose(directions, speeds, city, station_name, out_dir, lhs_dirs)
    plot_monthly_statistics(df, city, station_name, out_dir)
    plot_interannual_trend(df, city, station_name, out_dir)

    return {
        "city":            city,
        "station":         station_name,
        "station_id":      station_id,
        "latitude":        lat,
        "longitude":       lon,
        "distance_km":     round(dist_m / 1000, 1) if dist_m is not None else None,
        "data_resolution": resolution,
        "period":          date_range,
        "record_years":    round(record_years, 2),
        "total_records":   len(df),
        "valid_speed_obs": n_valid_speed,
        "valid_dir_obs":   n_valid_dir,
        **{f"spd_{k}": v for k, v in spd_stats.items()},
        **{f"dir_{k}": v for k, v in dir_stats.items()},
        "lhs_sim_directions_deg":  ",".join(map(str, lhs_dirs)),
        "rans_sim_directions_deg": ",".join(map(str, rans_dirs)),
    }


def print_summary_table(results: list) -> None:
    """Pretty-print a compact summary of all results."""
    if not results:
        print("\nNo results to display.")
        return
    print(f"\n{'=' * 80}")
    print("WIND ANALYSIS SUMMARY")
    print(f"{'=' * 80}")
    header = (f"{'City':<18} {'Station':<30} {'Mean':>7} {'P95':>7} "
              f"{'Max':>7} {'Dir':>6} {'Prev':>5}")
    print(header)
    print("-" * len(header))
    nan = float("nan")
    for r in results:
        dirm = f"{r.get('dir_circ_mean_deg', nan):.0f}°"
        print(f"{r['city'][:17]:<18} {r['station'][:29]:<30} "
              f"{r.get('spd_mean_ms', nan):>7.2f} {r.get('spd_p95_ms', nan):>7.2f} "
              f"{r.get('spd_max_ms', nan):>7.2f} {dirm:>6} "
              f"{r.get('dir_prevailing_sector', '—'):>5}")
    print("\nUnits: wind speed in m/s; Dir = circular mean direction the wind "
          "comes from")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Wind climatology and LHS simulation-direction selection "
                    "for a list of cities.")
    p.add_argument("-c", "--cities", default=DEFAULT_CITIES_FILE,
                   help="text file with one city per line (default: %(default)s)")
    p.add_argument("-o", "--output", default=DEFAULT_OUTPUT_DIR,
                   help="output directory (default: %(default)s)")
    p.add_argument("-y", "--years", type=int, default=DEFAULT_YEARS,
                   help="years of record to request (default: %(default)s)")
    p.add_argument("-n", "--n-directions", type=int, default=DEFAULT_N_LHS,
                   help="number of LHS simulation directions (default: %(default)s)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED,
                   help="LHS random seed (default: %(default)s)")
    p.add_argument("--user-agent", default="wind_analysis_research_v1.0",
                   help="Nominatim User-Agent; set to something identifying you "
                        "(default: %(default)s)")
    args = p.parse_args(argv)
    if args.years < 1 or args.n_directions < 1:
        p.error("--years and --n-directions must be positive")
    return args


def main(argv=None) -> None:
    args = parse_args(argv)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=round(365.25 * args.years))

    cities = load_cities(args.cities)
    geolocator = Nominatim(user_agent=args.user_agent)

    results = []
    for city in cities:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                result = analyse_city(city, geolocator, out_dir, start, end,
                                      args.n_directions, args.seed)
        except Exception as exc:  # one bad city must not abort the batch
            print(f"  [ERROR] '{city}' failed: {type(exc).__name__}: {exc}")
            result = {}
        if result:
            results.append(result)
        time.sleep(1.1)  # Nominatim: max 1 request per second

    print_summary_table(results)

    if results:
        csv_path = out_dir / "wind_statistics.csv"
        pd.DataFrame(results).to_csv(csv_path, index=False, float_format="%.4f")
        print(f"\nFull statistics saved → {csv_path}")
    print(f"\nAll output files are in: {out_dir.resolve()}/")


if __name__ == "__main__":
    main()
