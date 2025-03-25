

'''
To prepare a slice from a City4CFD terrain.

    1.  run rusterizer (https://github.com/ipadjen/rusterizer) on the terrain as below

        rusterizer -i terrain.obj -o terrain.tif 5

    2. In QGIS run "Raster Pixel to Points" from processing toolbox and save as gpkg.

    3. Provide path the terrain_gpkg_filepath variable, z_offset, and output_path for stl.

This slice can now be given to OpenFOAM as a function to write fields. For example:

/*--------------------------------*- C++ -*----------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  7
     \\/     M anipulation  |
\*---------------------------------------------------------------------------*/

sets
{
    type            sets;
    libs            ("libsampling.so");
    
    fields          (U k);
    setFormat       vtk;
    interpolationScheme cellPoint;
    writeControl        writeTime;
    sets
    (
        terrain_offset
        {
            type        triSurfaceMesh;
            surface     "terrain.stl";
            axis        xyz;
        }	
    );
}

// ************************************************************************* //


'''

import geopandas as gpd
import open3d as o3d
import numpy as np
from scipy.spatial import Delaunay


def main():

    # Input Variables
    terrain_gpkg_filepath = 'terrain.gpkg'
    z_offset = 2
    output_filename = 'terrain.stl'

    # read in gpkg file
    terrain_gdf = gpd.read_file(terrain_gpkg_filepath)

    # offset terrain vertically and convert to stl
    gdf_to_stl(terrain_gdf, output_filename, z_offset)


def gdf_to_stl(gdf, output_filename="terrain.stl", z_offset=0):
    """
    Converts a GeoDataFrame of points with x, y, and z (stored in the "VALUE" column)
    into an STL file using Open3D. The points are assumed to be regularly spaced in x, y.

    Parameters:
        gdf (GeoDataFrame): GeoDataFrame with Point geometries and a "VALUE" column for z.
        output_filename (str): Name of the STL file to save.
        z_offset (float): Value to offset the z-coordinates.

    Returns:
        None (saves the STL file)
    """
    # Extract x, y, and z values (apply z offset)
    points = np.array([(geom.x, geom.y, z + z_offset) for geom, z in zip(gdf.geometry, gdf["VALUE"])])

    # Perform Delaunay triangulation in 2D (x, y)
    tri = Delaunay(points[:, :2])

    # Create an Open3D TriangleMesh
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(points)
    mesh.triangles = o3d.utility.Vector3iVector(tri.simplices)

    # Optional: Compute normals for better visualization
    mesh.compute_vertex_normals()

    # Save as STL file
    o3d.io.write_triangle_mesh(output_filename, mesh)

    print(f"STL file saved as {output_filename}")


if __name__ == '__main__':
    main()