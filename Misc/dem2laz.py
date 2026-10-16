"""
dem2laz: fetch a DEM from OpenTopography and write it as a LAZ point cloud.

Typical use from another script::

    from dem2laz import dem_to_pointcloud

    # Bounding box (WGS84), default DEM = Copernicus GLO-30, local UTM output
    dem_to_pointcloud("exeter.laz", bbox=(-3.56, 50.70, -3.48, 50.75))

    # Centre + radius, explicit output CRS
    dem_to_pointcloud("exeter.laz", center=(50.7236, -3.5275), radius_m=2000,
                      target_crs="EPSG:27700")

    # Place name (geocoded with OSM Nominatim)
    dem_to_pointcloud("exeter.laz", place="Exeter, UK", radius_m=2000)

    # Already have a GeoTIFF?
    raster_to_pointcloud("merged.tif", "merged.laz", target_crs=27700)

The OpenTopography API key is taken from the ``api_key`` argument or the
``OPENTOPOGRAPHY_API_KEY`` environment variable (free key:
https://portal.opentopography.org/myopentopo).

When ``target_crs`` is None the output uses the UTM zone of the raster centre.
Only x/y are reprojected; z is written unchanged (no vertical datum shift).

Separate terrain / building clouds and building heights from a DSM and DTM::

    from dem2laz import split_pointclouds, assign_building_heights

    out = split_pointclouds("dsm.tif", "dtm.tif", "ground.laz", "buildings.laz",
                            footprints=osm_gdf, target_crs=27700)
    osm_gdf = assign_building_heights(osm_gdf, out["ndsm"], "buildings_h.geojson")

Requires: numpy, rasterio, pyproj, laspy[lazrs], requests (+ geopandas for footprints).
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import math
import os
import re
from pathlib import Path
from typing import Iterator, Optional, Sequence, Tuple, Union

import numpy as np
import requests

log = logging.getLogger(__name__)

OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
API_KEY_ENV = "OPENTOPOGRAPHY_API_KEY"
DEFAULT_DEMTYPE = "COP30"
USER_AGENT = "dem2laz/1.0"

# DEM datasets served by the OpenTopography global DEM API.
DEMTYPES = (
    "SRTMGL3", "SRTMGL1", "SRTMGL1_E", "AW3D30", "AW3D30_E", "SRTM15Plus",
    "NASADEM", "COP30", "COP90", "EU_DTM", "GEDI_L3", "GEBCO", "CA_MRDEM_DSM",
    "CA_MRDEM_DTM",
)

BBox = Tuple[float, float, float, float]  # west, south, east, north (WGS84)
CRSLike = Union[str, int, "pyproj.CRS", None]  # noqa: F821

_TIFF_MAGIC = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")
_CHUNK_PIXELS = 2_000_000


class DEMError(RuntimeError):
    """Raised for fetch or conversion failures with a user-readable message."""


# --------------------------------------------------------------------------- #
# Area of interest
# --------------------------------------------------------------------------- #
def geocode(place: str, timeout: float = 30) -> Tuple[float, float]:
    """Return (lat, lon) for a place name using OSM Nominatim."""
    r = requests.get(
        NOMINATIM_URL,
        params={"q": place, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    r.raise_for_status()
    hits = r.json()
    if not hits:
        raise DEMError(f"Could not geocode place: {place!r}")
    return float(hits[0]["lat"]), float(hits[0]["lon"])


def bbox_from_center(lat: float, lon: float, radius_m: float) -> BBox:
    """Square WGS84 bbox (west, south, east, north) of half-width ``radius_m``."""
    dlat = radius_m / 111_320.0
    dlon = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 1e-6))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def _resolve_bbox(bbox, center, place, radius_m) -> BBox:
    given = [bbox is not None, center is not None, place is not None]
    if sum(given) != 1:
        raise ValueError("Specify exactly one of bbox, center or place.")
    if bbox is not None:
        west, south, east, north = map(float, bbox)
    else:
        if radius_m is None:
            raise ValueError("radius_m is required with center or place.")
        lat, lon = center if center is not None else geocode(place)
        west, south, east, north = bbox_from_center(float(lat), float(lon), radius_m)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError(
            f"Invalid bbox (west={west}, south={south}, east={east}, north={north}); "
            "expected lon/lat in degrees with west<east and south<north."
        )
    return west, south, east, north


# --------------------------------------------------------------------------- #
# OpenTopography download
# --------------------------------------------------------------------------- #
def fetch_dem(
    bbox: Optional[BBox] = None,
    *,
    center: Optional[Tuple[float, float]] = None,
    place: Optional[str] = None,
    radius_m: Optional[float] = None,
    demtype: str = DEFAULT_DEMTYPE,
    api_key: Optional[str] = None,
    cache_dir: Union[str, Path] = "dem_cache",
    force: bool = False,
    timeout: float = 600,
) -> Path:
    """
    Download a GeoTIFF DEM from OpenTopography and return its path.

    The area is given as exactly one of ``bbox`` (west, south, east, north),
    ``center`` (lat, lon) + ``radius_m``, or ``place`` + ``radius_m``.
    Downloads are cached in ``cache_dir`` by (demtype, bbox).
    """
    if demtype not in DEMTYPES:
        raise ValueError(f"Unknown demtype {demtype!r}. Options: {', '.join(DEMTYPES)}")
    api_key = api_key or os.environ.get(API_KEY_ENV)
    if not api_key:
        raise DEMError(f"No API key: pass api_key= or set ${API_KEY_ENV}.")

    west, south, east, north = _resolve_bbox(bbox, center, place, radius_m)

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha1(f"{demtype}{west:.6f}{south:.6f}{east:.6f}{north:.6f}".encode()).hexdigest()[:10]
    path = cache_dir / f"{demtype}_{tag}.tif"
    if path.exists() and not force:
        log.info("Using cached DEM %s", path)
        return path

    params = {
        "demtype": demtype, "south": south, "north": north,
        "west": west, "east": east, "outputFormat": "GTiff", "API_Key": api_key,
    }
    log.info("Requesting %s for W%.5f S%.5f E%.5f N%.5f", demtype, west, south, east, north)
    tmp = path.with_suffix(".part")
    try:
        with requests.get(OPENTOPO_URL, params=params, stream=True, timeout=timeout,
                          headers={"User-Agent": USER_AGENT}) as r:
            if r.status_code != 200:
                raise DEMError(f"OpenTopography returned HTTP {r.status_code}: {r.text[:300].strip()}")
            with open(tmp, "wb") as fh:
                for block in r.iter_content(1 << 20):
                    fh.write(block)
        with open(tmp, "rb") as fh:
            head = fh.read(4)
        if head not in _TIFF_MAGIC:
            # API reports some errors (bad key, area too large) as text with HTTP 200.
            msg = tmp.read_text(errors="replace")[:300].strip()
            raise DEMError(f"OpenTopography did not return a GeoTIFF: {msg}")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    log.info("Saved DEM to %s", path)
    return path


# --------------------------------------------------------------------------- #
# CRS helpers
# --------------------------------------------------------------------------- #
def utm_crs_for(lon: float, lat: float):
    """UTM (or UPS at the poles) CRS covering a WGS84 lon/lat."""
    import pyproj

    if lat >= 84:
        return pyproj.CRS.from_epsg(32661)
    if lat <= -80:
        return pyproj.CRS.from_epsg(32761)
    zone = min(int((lon + 180) // 6) + 1, 60)
    return pyproj.CRS.from_epsg((32600 if lat >= 0 else 32700) + zone)


def _to_crs(value: CRSLike):
    import pyproj

    if value is None:
        return None
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return pyproj.CRS.from_epsg(int(value))
    return pyproj.CRS.from_user_input(value)


# --------------------------------------------------------------------------- #
# Raster -> point cloud
# --------------------------------------------------------------------------- #
def _local_crs(src_crs, bounds):
    """UTM CRS at the centre of ``bounds`` given in ``src_crs``."""
    from pyproj import Transformer

    w, s, e, n = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True).transform_bounds(
        *bounds, densify_pts=21)
    return utm_crs_for((w + e) / 2, (s + n) / 2)


def _iter_points(
    src, band: int, subsample: int, height_src=None, min_height: float = 0.0, geoms=None,
) -> Iterator[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """
    Yield valid (x, y, z) arrays in the raster CRS, one row-chunk at a time.

    Optional filters: ``height_src`` (same grid as ``src``; keep pixels >= min_height)
    and ``geoms`` (shapely geometries in the raster CRS; keep pixels inside them).
    """
    from rasterio.features import geometry_mask
    from rasterio.windows import Window

    t = src.transform
    nodata = src.nodata
    rows_per_chunk = max(subsample, (_CHUNK_PIXELS // max(src.width, 1)) // subsample * subsample)
    cols = np.arange(0, src.width, subsample)

    for r0 in range(0, src.height, rows_per_chunk):
        h = min(rows_per_chunk, src.height - r0)
        window = Window(0, r0, src.width, h)
        data = src.read(band, window=window).astype(np.float64)
        data = data[::subsample, ::subsample]
        rows = np.arange(r0, r0 + h, subsample)
        valid = np.isfinite(data)
        if nodata is not None and np.isfinite(nodata):
            valid &= ~np.isclose(data, nodata)
        if height_src is not None:
            hgt = height_src.read(1, window=window).astype(np.float64)[::subsample, ::subsample]
            with np.errstate(invalid="ignore"):
                valid &= np.isfinite(hgt) & (hgt >= min_height)
        if geoms is not None and valid.any():
            inside = geometry_mask(geoms, out_shape=(h, src.width),
                                   transform=src.window_transform(window), invert=True)
            valid &= inside[::subsample, ::subsample]
        ri, ci = np.nonzero(valid)
        if ri.size == 0:
            continue
        pc = cols[ci] + 0.5
        pr = rows[ri] + 0.5
        x = t.a * pc + t.b * pr + t.c
        y = t.d * pc + t.e * pr + t.f
        yield x, y, data[ri, ci]


def raster_to_pointcloud(
    tif_path: Union[str, Path],
    out_path: Union[str, Path],
    *,
    target_crs: CRSLike = None,
    source_crs: CRSLike = None,
    band: int = 1,
    subsample: int = 1,
    classification: int = 0,
    height_raster: Union[str, Path, None] = None,
    min_height: float = 0.0,
    mask_geoms: Optional[Sequence] = None,
) -> Path:
    """
    Convert a single-band raster to a LAS/LAZ point cloud (one point per pixel).

    target_crs  : output CRS (EPSG int, "EPSG:xxxx", WKT, ...). None = UTM zone
                  of the raster centre.
    source_crs  : only needed if the raster has no embedded CRS.
    subsample   : keep every Nth pixel in both directions.
    classification : ASPRS class written to every point (2 = ground, 6 = building, ...).
    height_raster, min_height : keep only pixels where this raster (same grid, e.g.
                  an nDSM from compute_ndsm) is >= min_height.
    mask_geoms  : keep only pixels inside these shapely geometries (raster CRS).

    Returns the path actually written (.laz unless ``out_path`` ends in .las).
    """
    import laspy
    import pyproj
    import rasterio
    from pyproj import Transformer

    if subsample < 1:
        raise ValueError("subsample must be >= 1")
    out_path = Path(out_path)
    if out_path.suffix.lower() not in (".las", ".laz"):
        out_path = out_path.with_suffix(".laz")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(tif_path) as src:
        src_crs = _to_crs(source_crs) or (pyproj.CRS.from_wkt(src.crs.to_wkt()) if src.crs else None)
        if src_crs is None:
            raise DEMError(f"{tif_path} has no CRS; pass source_crs=.")
        if band < 1 or band > src.count:
            raise ValueError(f"band must be in 1..{src.count}")

        dst_crs = _to_crs(target_crs) or _local_crs(src_crs, src.bounds)
        log.info("Source %s (%dx%d, res %s) -> target %s",
                 src_crs.to_string(), src.width, src.height, src.res, dst_crs.to_string())

        same = src_crs == dst_crs
        tf = None if same else Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        xmin, ymin, xmax, ymax = (src.bounds if same else
                                  tf.transform_bounds(*src.bounds, densify_pts=21))

        header = laspy.LasHeader(point_format=6, version="1.4")
        header.offsets = [math.floor(xmin), math.floor(ymin), 0.0]
        xy_scale = 1e-8 if dst_crs.is_geographic else 0.001
        header.scales = [xy_scale, xy_scale, 0.001]
        header.add_crs(dst_crs)

        height_src = rasterio.open(height_raster) if height_raster else None
        if height_src is not None and (height_src.shape != src.shape or height_src.transform != src.transform):
            height_src.close()
            raise DEMError("height_raster must be on the same grid as the input raster.")

        total = 0
        zmin, zmax = math.inf, -math.inf
        with laspy.open(str(out_path), mode="w", header=header) as writer:
            for x, y, z in _iter_points(src, band, subsample, height_src, min_height, mask_geoms):
                if tf is not None:
                    x, y = tf.transform(x, y)
                    ok = np.isfinite(x) & np.isfinite(y)
                    x, y, z = x[ok], y[ok], z[ok]
                pts = laspy.ScaleAwarePointRecord.zeros(len(x), header=header)
                pts.x, pts.y, pts.z = x, y, z
                pts.classification = np.full(len(x), classification, dtype=np.uint8)
                writer.write_points(pts)
                total += len(x)
                zmin, zmax = min(zmin, z.min()), max(zmax, z.max())
        if height_src is not None:
            height_src.close()

    if total == 0:
        out_path.unlink(missing_ok=True)
        raise DEMError("No points left: raster has no valid pixels passing the height/footprint filters.")
    log.info("Wrote %s: %s points, z in [%.2f, %.2f], CRS %s",
             out_path, f"{total:,}", zmin, zmax, dst_crs.to_string())
    return out_path


# --------------------------------------------------------------------------- #
# DSM - DTM: terrain / building split and building heights
# --------------------------------------------------------------------------- #
def fetch_dsm_dtm(
    bbox: Optional[BBox] = None,
    *,
    dsm_demtype: str = "COP30",
    dtm_demtype: str = "EU_DTM",
    **fetch_kwargs,
) -> Tuple[Path, Path]:
    """
    Download a DSM and a DTM for the same area; returns (dsm_path, dtm_path).

    Accepts the same area/api_key/cache_dir arguments as fetch_dem. The defaults are
    30 m products (EU_DTM covers Europe only), which are too coarse to resolve
    individual buildings; for that, pass local 1 m lidar rasters instead.
    """
    return (fetch_dem(bbox, demtype=dsm_demtype, **fetch_kwargs),
            fetch_dem(bbox, demtype=dtm_demtype, **fetch_kwargs))


def compute_ndsm(
    dsm_path: Union[str, Path],
    dtm_path: Union[str, Path],
    out_path: Union[str, Path],
    *,
    clip_negative: bool = True,
) -> Path:
    """
    Write the normalised DSM (DSM - DTM = height above ground) on the DSM grid.

    The DTM is bilinearly resampled onto the DSM grid (any CRS/resolution), so the
    two inputs need not match. Pixels invalid in either input are NaN. Negative
    differences (noise) are set to 0 when ``clip_negative``.
    """
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    from rasterio.windows import Window

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(dsm_path) as dsm, rasterio.open(dtm_path) as dtm:
        if dsm.crs is None or dtm.crs is None:
            raise DEMError("DSM and DTM must both have a CRS.")
        if dtm.res[0] > 2 * dsm.res[0] and dtm.crs == dsm.crs:
            log.warning("DTM (%.3g) is much coarser than DSM (%.3g): building heights will be smoothed.",
                        dtm.res[0], dsm.res[0])
        profile = dict(driver="GTiff", dtype="float32", count=1, nodata=float("nan"),
                       width=dsm.width, height=dsm.height, crs=dsm.crs,
                       transform=dsm.transform, compress="deflate")
        with WarpedVRT(dtm, crs=dsm.crs, transform=dsm.transform, width=dsm.width,
                       height=dsm.height, resampling=Resampling.bilinear) as dtm_grid, \
                rasterio.open(out_path, "w", **profile) as dst:
            step = max(1, _CHUNK_PIXELS // max(dsm.width, 1))
            for r0 in range(0, dsm.height, step):
                w = Window(0, r0, dsm.width, min(step, dsm.height - r0))
                s = dsm.read(1, window=w, masked=True).astype(np.float64).filled(np.nan)
                g = dtm_grid.read(1, window=w, masked=True).astype(np.float64).filled(np.nan)
                n = s - g
                if clip_negative:
                    n = np.where(n < 0, 0.0, n)
                dst.write(n.astype(np.float32), 1, window=w)
    log.info("Wrote nDSM %s", out_path)
    return out_path


def _load_footprints(footprints):
    import geopandas as gpd

    gdf = gpd.read_file(footprints) if isinstance(footprints, (str, Path)) else footprints.copy()
    if gdf.crs is None:
        raise DEMError("Footprints have no CRS.")
    return gdf


def split_pointclouds(
    dsm_path: Union[str, Path],
    dtm_path: Union[str, Path],
    ground_out: Union[str, Path],
    buildings_out: Union[str, Path],
    *,
    footprints=None,
    min_height: float = 2.0,
    target_crs: CRSLike = None,
    subsample: int = 1,
    ndsm_path: Union[str, Path, None] = None,
) -> dict:
    """
    Write separate terrain and building point clouds from a DSM and a DTM.

    ground    : every DTM pixel, classification 2.
    buildings : DSM pixels at least ``min_height`` m above the DTM, classification 6,
                z = DSM elevation. If ``footprints`` (path or GeoDataFrame, e.g. OSM
                buildings) is given, only pixels inside a footprint are kept, which
                removes trees and other non-building objects.

    Both clouds share one CRS (``target_crs`` or the local UTM zone). Returns a dict
    with the ``ground``, ``buildings`` and ``ndsm`` paths.
    """
    import rasterio

    ground_out = Path(ground_out)
    ndsm_path = Path(ndsm_path) if ndsm_path else ground_out.with_name("ndsm.tif")
    compute_ndsm(dsm_path, dtm_path, ndsm_path)

    with rasterio.open(dsm_path) as dsm:
        crs = _to_crs(target_crs) or _local_crs(_to_crs(dsm.crs.to_wkt()), dsm.bounds)
        geoms = None
        if footprints is not None:
            gdf = _load_footprints(footprints).to_crs(dsm.crs)
            geoms = [g for g in gdf.geometry if g is not None and not g.is_empty]

    ground = raster_to_pointcloud(dtm_path, ground_out, target_crs=crs,
                                  subsample=subsample, classification=2)
    buildings = raster_to_pointcloud(dsm_path, buildings_out, target_crs=crs, subsample=subsample,
                                     classification=6, height_raster=ndsm_path,
                                     min_height=min_height, mask_geoms=geoms)
    return {"ground": ground, "buildings": buildings, "ndsm": ndsm_path}


_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _parse_osm_number(value, *, to_metres: bool) -> float:
    """Parse an OSM numeric tag ('12', '12.5 m', "40'", '5;6'); NaN if absent/invalid."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return math.nan
    s = str(value).strip().lower()
    m = _NUM.search(s)
    if not m:
        return math.nan
    v = float(m.group().replace(",", "."))
    if to_metres and (s[m.end():].strip().startswith(("ft", "feet", "'"))):
        v *= 0.3048
    return v


def _footprint_height(ndsm, geom, percentile: float, min_pixels: int) -> float:
    """Percentile of nDSM values inside ``geom`` (raster CRS); NaN if too few pixels."""
    from rasterio.errors import WindowError
    from rasterio.features import geometry_mask
    from rasterio.windows import Window, from_bounds

    if geom is None or geom.is_empty:
        return math.nan
    win = from_bounds(*geom.bounds, transform=ndsm.transform)
    win = Window(math.floor(win.col_off), math.floor(win.row_off),
                 math.ceil(win.width) + 1, math.ceil(win.height) + 1)
    try:
        win = win.intersection(Window(0, 0, ndsm.width, ndsm.height))
    except WindowError:
        return math.nan
    data = ndsm.read(1, window=win).astype(np.float64)
    tf = ndsm.window_transform(win)
    inside = geometry_mask([geom], out_shape=data.shape, transform=tf, invert=True)
    if not inside.any():  # footprint smaller than a pixel centre: take touched pixels
        inside = geometry_mask([geom], out_shape=data.shape, transform=tf, invert=True,
                               all_touched=True)
    vals = data[inside]
    vals = vals[np.isfinite(vals)]
    return float(np.percentile(vals, percentile)) if vals.size >= min_pixels else math.nan


def assign_building_heights(
    footprints,
    ndsm_path: Union[str, Path],
    out_path: Union[str, Path, None] = None,
    *,
    percentile: float = 70.0,
    level_height: float = 3.0,
    min_height: float = 2.0,
    min_pixels: int = 1,
    overwrite: bool = False,
):
    """
    Fill missing OSM building heights from an nDSM (see compute_ndsm).

    footprints : GeoDataFrame or file path (e.g. OSM buildings from osmnx) with an
                 optional ``height`` and/or ``building:levels`` column.

    For each footprint the nDSM ``percentile`` inside it is taken as the building
    height (a high percentile approximates the roof, ignoring low edge pixels).
    Priority per building: OSM ``height`` > ``building:levels`` * ``level_height`` >
    nDSM. With ``overwrite=True`` the nDSM value wins whenever available. Estimates
    below ``min_height`` are discarded.

    Adds columns ``height_osm``, ``height_levels``, ``height_dsm``, ``height_m`` (final,
    NaN if unknown) and ``height_source`` ('osm_height' | 'osm_levels' | 'dsm' | 'missing').
    Returns the GeoDataFrame (original CRS) and writes it to ``out_path`` if given.
    """
    import rasterio

    gdf = _load_footprints(footprints)
    n = len(gdf)

    def column(name, to_metres):
        if name not in gdf.columns:
            return np.full(n, math.nan)
        return np.array([_parse_osm_number(v, to_metres=to_metres) for v in gdf[name]])

    est = {
        "osm_height": column("height", True),
        "osm_levels": column("building:levels", False) * level_height,
    }
    with rasterio.open(ndsm_path) as ndsm:
        geoms = gdf.to_crs(ndsm.crs).geometry
        dsm_h = np.array([_footprint_height(ndsm, g, percentile, min_pixels) for g in geoms])
    dsm_h[dsm_h < min_height] = math.nan
    est["dsm"] = dsm_h

    order = ["dsm", "osm_height", "osm_levels"] if overwrite else ["osm_height", "osm_levels", "dsm"]
    final = np.full(n, math.nan)
    source = np.full(n, "missing", dtype=object)
    for key in order:
        pick = np.isnan(final) & np.isfinite(est[key])
        final[pick] = est[key][pick]
        source[pick] = key

    gdf["height_osm"], gdf["height_levels"], gdf["height_dsm"] = est["osm_height"], est["osm_levels"], dsm_h
    gdf["height_m"], gdf["height_source"] = final, source
    log.info("Building heights: %s", ", ".join(
        f"{k}={int((source == k).sum())}" for k in ("osm_height", "osm_levels", "dsm", "missing")))
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(out_path)
    return gdf


# --------------------------------------------------------------------------- #
# One-call pipeline
# --------------------------------------------------------------------------- #
def dem_to_pointcloud(
    out_path: Union[str, Path],
    bbox: Optional[BBox] = None,
    *,
    center: Optional[Tuple[float, float]] = None,
    place: Optional[str] = None,
    radius_m: Optional[float] = None,
    demtype: str = DEFAULT_DEMTYPE,
    target_crs: CRSLike = None,
    api_key: Optional[str] = None,
    cache_dir: Union[str, Path] = "dem_cache",
    subsample: int = 1,
    classification: int = 0,
    force_download: bool = False,
) -> Path:
    """Fetch a DEM from OpenTopography and convert it to a point cloud."""
    tif = fetch_dem(bbox, center=center, place=place, radius_m=radius_m, demtype=demtype,
                    api_key=api_key, cache_dir=cache_dir, force=force_download)
    return raster_to_pointcloud(tif, out_path, target_crs=target_crs,
                                subsample=subsample, classification=classification)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[Sequence[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Fetch an OpenTopography DEM (or read a local GeoTIFF) and write a LAZ point cloud.")
    p.add_argument("output", help="Output .laz/.las path")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"))
    src.add_argument("--center", nargs=2, type=float, metavar=("LAT", "LON"))
    src.add_argument("--place", help="Place name, geocoded via Nominatim")
    src.add_argument("--tif", help="Use this local GeoTIFF instead of downloading")
    p.add_argument("--radius", type=float, help="Half-width in metres (with --center/--place)")
    p.add_argument("--demtype", default=DEFAULT_DEMTYPE, choices=DEMTYPES)
    p.add_argument("--crs", help="Output CRS, e.g. EPSG:27700 (default: local UTM)")
    p.add_argument("--api-key", help=f"Default: ${API_KEY_ENV}")
    p.add_argument("--cache-dir", default="dem_cache")
    p.add_argument("--subsample", type=int, default=1)
    p.add_argument("--classification", type=int, default=0)
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.tif:
        raster_to_pointcloud(a.tif, a.output, target_crs=a.crs, subsample=a.subsample,
                             classification=a.classification)
    else:
        dem_to_pointcloud(a.output, a.bbox, center=tuple(a.center) if a.center else None,
                          place=a.place, radius_m=a.radius, demtype=a.demtype,
                          target_crs=a.crs, api_key=a.api_key, cache_dir=a.cache_dir,
                          subsample=a.subsample, classification=a.classification)


if __name__ == "__main__":
    main()
