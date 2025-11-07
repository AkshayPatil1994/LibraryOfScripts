import trimesh
import numpy as np
from trimesh.transformations import rotation_matrix
from scipy.optimize import brentq
import matplotlib.pyplot as plt
#
# DEFINE ADAPTIVE GRID WITH TANH STRETCHING
#
def gen_grid(zsize, ktot, dzlin, zlin, max_stretch_ratio=3.0, use_geom = False, tol=1e-9, verbose = False):
    '''
        This function generates a grid such that
            a. Grid resolution of dzlin over a height zlin
            b. Specifies the grid such that the grid has geometric progression using the brentq method (when use_geo = True)
            c. Solves for the stretching parameter such that the remaining grid points are stretched using tanh stretching
    
    INPUT
        zsize - [float]: Total length of the domain in the z direction (default units ~ m)
        ktot - [integer]: Number of grid points in total
        dzlin - [float]: Grid size over the uniform length zlin (default units ~ m)
        zlin - [float]: Height over which uniform grid dzlin is applied (default units ~ m)
        max_stretch_ratio - [float, default value 3.0]: Maximum stretching parameter
        use_geom - [boolean, default value False]: Use geometric stretching using brentq method
        tol - [float, default value 1.0e-9]: Tolerance for numerical solver to find stretching parameter
        verbose - [boolean, default value False]: Print detailed information about grid 
    OUTPUT
        zh - [float array]: Cell center z values (default units ~ m)
        zf - [float array]: Cell face z values (default units ~ m)
        dzf - [float array]: Cell face grid size (default units ~ m)
        gf - [float]: Grid stretching factor 
        il - [integer]: Last Cell index where a uniform grid is applied (sanity check variable)
    '''
    #
    # Force data types to prevent any problems downstream
    #
    zsize = float(zsize)
    ktot = int(ktot)
    dzlin = float(dzlin)
    zlin = float(zlin)
    max_stretch_ratio = float(max_stretch_ratio)
    use_geom = bool(use_geom)
    #
    # Number of uniform cells
    #
    n_uniform = int(np.round(zlin / dzlin))
    zh_uniform = np.linspace(0.0, n_uniform * dzlin, n_uniform + 1)
    z_uniform_end = zh_uniform[-1]

    if n_uniform >= ktot:
        raise ValueError(
            f"Not enough cells: need at least {n_uniform} cells for zlin={zlin}, only {ktot} available"
        )
    #
    # Remaining cells and remaining height for stretched region
    #
    n_stretch = ktot - n_uniform
    z_stretch = zsize - z_uniform_end
    if z_stretch <= 0:
        raise ValueError(f"zlin ({zlin}) must be less than zsize ({zsize})")
    #
    # GEOMETRIC STRETCHING
    # Sum S(r) = a0 * (r^n - 1) / (r - 1)  with a0 = dzlin, n = n_stretch
    #
    def geom_sum_minus_target(r):
        if abs(r - 1.0) < 1e-12:
            return dzlin * n_stretch - z_stretch
        return dzlin * (r ** n_stretch - 1.0) / (r - 1.0) - z_stretch
    
    r_solution = None
    # Check feasibility: r -> 1 gives sum = dzlin * n_stretch
    sum_r1 = dzlin * n_stretch
    if sum_r1 <= z_stretch + 1e-12:
        # There exists r >= 1 that satisfies the equation (sum increases with r)
        # Search for r in (1.0, r_max)
        r_min = 1.0 + 1e-12
        r_max = 1.5
        # increase r_max until function at r_max > 0 (S(r_max) - z_stretch > 0)
        # we need geom_sum_minus_target(r_max) >= 0 for brentq to bracket
        while geom_sum_minus_target(r_max) < 0 and r_max < 1e6:
            r_max *= 2.0
        try:
            # Solve for r
            r_solution = brentq(geom_sum_minus_target, r_min, r_max, xtol=tol, rtol=tol, maxiter=200)            
        except ValueError:
            use_geom = False
    #
    # Build zh depending on chosen method
    #
    if use_geom and r_solution is not None:
        # Build geometric dz for stretched region
        r = float(r_solution)
        # dzs: first stretched cell = dzlin, subsequent multiplied by r
        exponents = np.arange(n_stretch, dtype=float)  # 0..n_stretch-1
        dzs_stretch = dzlin * (r ** exponents)
        # cumulative interfaces relative to the start of stretch
        zh_stretch_rel = np.concatenate(([0.0], np.cumsum(dzs_stretch)))
        # Sanity adjust last point to exactly z_stretch to avoid small numerical drift
        zh_stretch_rel[-1] = z_stretch
        # Full interface array
        zh = np.zeros(ktot + 1)
        zh[: n_uniform + 1] = zh_uniform
        zh[n_uniform + 1 :] = z_uniform_end + zh_stretch_rel[1:]
        gf = r  # report r as "stretching factor" for geometric case
        il = n_uniform - 1
    else:
        #
        # tanh-based smooth stretching, enforce first stretched dz ~= dzlin
        # n_stretch intervals -> n_stretch+1 interfaces in the stretched region: s in [0,1]
        #
        def stretched_rel(gf):
            s = np.linspace(0.0, 1.0, n_stretch + 1)
            # raw tanh profile in [0,1]
            f = 1 - np.tanh(gf * (1-s)) / np.tanh(gf)
            # normalize to [0,1]
            f = (f - f[0]) / (f[-1] - f[0])
            z_rel = f * z_stretch
            return z_rel
        #
        # We want first stretched spacing (z_rel[1] - z_rel[0] = z_rel[1]) to equal dzlin
        #
        def first_dz_minus_target(gf):
            rel = stretched_rel(gf)
            return rel[1] - dzlin
        #
        # Check monotonic behavior at gf small vs large:
        # At very small gf, tanh approx linear => rel[1] approx z_stretch*(1/(n_stretch))
        # If z_stretch/n_stretch > dzlin then a gf exists where first spacing == dzlin.
        # Bound search for gf in (1e-6, gf_max)
        #
        gf_min = 1e-6
        gf_max = 50.0
        # Check endpoints: if function changes sign we can root-find
        f_min = first_dz_minus_target(gf_min)
        f_max = first_dz_minus_target(gf_max)

        if f_min * f_max > 0:            
            rel_small = stretched_rel(1e-6)
            first_small = rel_small[1]
            scale = dzlin / first_small
            rel = stretched_rel(1.0) * scale
            # ensure top exactly z_stretch by linear remapping
            rel = rel * (z_stretch / rel[-1])
            zh = np.zeros(ktot + 1)
            zh[: n_uniform + 1] = zh_uniform
            zh[n_uniform + 1 :] = z_uniform_end + rel[1:]
            gf = 1.0
            il = n_uniform - 1
        else:
            # Root find gf such that first stretched cell equals dzlin
            gf_found = brentq(first_dz_minus_target, gf_min, gf_max, xtol=tol, rtol=tol, maxiter=200)
            rel = stretched_rel(gf_found)
            # Ensure exact top
            rel[-1] = z_stretch
            zh = np.zeros(ktot + 1)
            zh[: n_uniform + 1] = zh_uniform
            zh[n_uniform + 1 :] = z_uniform_end + rel[1:]
            gf = float(gf_found)
            il = n_uniform - 1
    #
    # Compute centers and spacings
    #
    zf = 0.5 * (zh[:-1] + zh[1:])
    dzf = np.diff(zh)
    #
    # Check stretch ratio
    #
    stretch_ratio = dzf.max() / dzf.min()
    if stretch_ratio > max_stretch_ratio:
        print(f"Warning: Stretch ratio ({stretch_ratio:.3f}) exceeds maximum ({max_stretch_ratio:.3f})")

    # Summary
    if(verbose):
        print(f"\nGrid generation summary:")
        print(f"  Domain height: {zsize:.6f} m")
        print(f"  Total cells: {ktot}")
        print(f"  Uniform region: 0 – {z_uniform_end:.6f} m ({n_uniform} cells, Δz={dzlin:.6f} m)")
        print(f"  Stretched region: {z_uniform_end:.6f} – {zsize:.6f} m ({n_stretch} cells)")
        print(f"  Stretching parameter (gf/r): {gf:.6g}")
        print(f"  Min Δz: {dzf.min():.6f} m, Max Δz: {dzf.max():.6f} m, Ratio: {stretch_ratio:.6f}")
        print(f"  Final height: {zh[-1]:.10f} m (target: {zsize:.10f} m)")
        print(f"  Height error: {abs(zh[-1] - zsize):.2e} m")
        print(f"  Last uniform grid index: {il} (Note nth point here is n+1th point since python is zero index based!)")    

    return zh, zf, dzf, gf, il
#
# DEFINE ROUND TO MULTIPLE FUNCTION
#
def round_to_multiple(number, multiple):
    '''
        This function rounds a given number to integer multiple of another 
    INPUT
        number - [float]: Number to be rounded 
        multiple - [integer]: Multiple at which number is to be rounded
    OUTPUT
        rounded multiple value of number
    '''
    return multiple * round(number / multiple)
#
# PLOT GRID
#
def plot_grid(zlin,ktot,dzf,zf):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

    # Grid spacing vs height (plot dz at midpoints zf)
    ax1.plot(dzf, zf, 'kx', markersize=8)
    ax1.axhline(zlin, color='r', linestyle='--', linewidth=1.5, label=f'Stretch start: {zlin} m')
    ax1.set_xlabel(r'Cell spacing $\Delta z$ (m)', fontsize=20)
    ax1.set_ylabel(r'$ln(z)$ (m)', fontsize=20)
    ax1.set_title('Grid Spacing Distribution', fontsize=25)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')
    ax1.legend(frameon=False,fontsize=15)

    # Cumulative Grid Distribution
    cell_numbers = np.arange(1, ktot + 1)
    ax2.plot(cell_numbers, zf, 'k+', markersize=8)
    ax2.axhline(zlin, color='r', linestyle='--', linewidth=1.5)
    ax2.set_xlabel('Cell index', fontsize=20)    
    ax2.set_title('Cell Center Heights', fontsize=25)
    ax2.grid(True, alpha=0.3)
    ax2.legend(frameon=False)
    ax2.set_yscale('log')
    

    plt.tight_layout()
    plt.show()    
#
# COMBINE & CLIP GEOMETRY
#
def combine_and_clip(obj_files, output_file, center, radius,
                     rotangledeg=0, rotaxis=[0,0,1], rotpoint=None):
    '''
        This function combines multiple OBJ files, clip geometry to a sphere around a given center, rotate about a specified point, and retain group names.
    INPUT
        obj_files - [list of strings]: List containing the full path and names of the obj files to be merged
        output_file - [string]: Name of the merged output file
        center - [list of floats]: Center about which the clipping is carried out
        radius - [float]: Radius about the center that is retained within the geometry
        rotangledeg - [float, default value 0 deg]: Rotation angle applied
        rotaxis - [list of integer, default about z axis]: Rotation axis
    OUTPUT
        Returns the clipped and rotated merged obj        
    '''
    combined_meshes = []

    center = np.array(center)

    # Default rotation point = center if not provided
    if rotpoint is None:
        rotpoint = center
    rotpoint = np.array(rotpoint)

    # Create rotation matrix (if angle != 0)
    if rotangledeg != 0:
        rot_matrix = rotation_matrix(np.deg2rad(rotangledeg), rotaxis, rotpoint)
    else:
        rot_matrix = None

    for obj_file in obj_files:
        # Load with process=False to keep group info
        scene = trimesh.load(obj_file, force='scene')

        # Each geometry in scene corresponds to a group
        for name, geom in scene.geometry.items():
            mesh = geom.copy()

            # Clip geometry to sphere
            mask = np.linalg.norm(mesh.vertices - center, axis=1) <= radius
            face_mask = mask[mesh.faces].all(axis=1)
            mesh.update_faces(face_mask)
            mesh.remove_unreferenced_vertices()

            # Apply rotation if any
            if rot_matrix is not None and len(mesh.faces) > 0:
                mesh.apply_transform(rot_matrix)

            if len(mesh.faces) > 0:
                combined_meshes.append(mesh)

    if len(combined_meshes) == 0:
        print("No geometry within clipping radius.")
        return

    # Combine into one scene
    scene_out = trimesh.Scene()
    for i, mesh in enumerate(combined_meshes):
        gname = mesh.metadata.get('group_name', f"group_{i}")
        scene_out.add_geometry(mesh, node_name=gname)

    # Export
    scene_out.export(output_file)
#
# FACTOR NPROCS
#
def get_decomp(n):
    '''
        This function calculates the decomposition factors for uDALES
    INPUT
        n - [integer]: Number of processors in total
    OUTPUT
        procx, procy - [integer]: Number of blocks in x and y
    '''
    # First check if sqrt is 2^N
    square_root = np.sqrt(n)
    if(square_root.is_integer()):
        procx, procy = square_root, square_root
        return procx, procy    
    else:
        factors = []
        i = 1
        while 2 ** i < n:
            if n % (2 ** i) == 0:
                factors.append(2 ** i)
            i += 1
        # Now get the best combination which typically is central two
        startx=len(factors)//2
        procx, procy = factors[startx], int(n/factors[startx])
        return procx, procy
#
# BEST N POINTS
#
def getN(L, delta, divisor, search_range=5):
    """
        This function finds the optimal number of grid points that:
            1. Is divisible by divisor
            2. Gives a resolution closest to the target delta
    INPUT    
        L - [float]: Domain length
        delta - [float]: Target resolution
        divisor - [int]: Number that N must be divisible by
        search_range - [int]: Number of multiples to search above and below ideal value    
    OUTPUT
        N_opt - [int]: Optimal number of grid points
    """
    # Calculate ideal number of grid points
    N_ideal = L / delta
    
    # Find the base multiple
    base_multiple = int(N_ideal // divisor)
    
    # Search through nearby multiples
    best_N = None
    best_error = float('inf')
    
    for i in range(max(1, base_multiple - search_range), base_multiple + search_range + 1):
        N_candidate = i * divisor
        if N_candidate > 0:
            delta_candidate = L / N_candidate
            error = abs(delta_candidate - delta)
            
            if error < best_error:
                best_error = error
                best_N = N_candidate
    
    return best_N
