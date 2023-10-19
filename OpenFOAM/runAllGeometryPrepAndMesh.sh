#!/bin/zsh
# Name of the output stl
outMesh='geo/SF.stl'
# Check if logs directory exists
if [ -d "logs" ]; then
	echo "Starting script...."
else
	mkdir logs
	echo "`logs` missing, creating it now....."
fi
# Generate the cube geometry and save the mesh
gmsh geo/generateCubes.geo -2 -o $outMesh > logs/geocube.log
# Replace the dummy text
sed -i 's/Created by Gmsh/Buildings/g' $outMesh
# Copy the file to the right location
rsync $outMesh constant/triSurface/
echo "Done with generating the cubes...."
# Run surfaceFeatures
surfaceFeatures > logs/surfaceFeatures.log
echo "Done with surface features....."
# Generate the blockMeshDict
m4 system/blockMeshDict.m4 > system/blockMeshDict
blockMesh > logs/blockMesh.log
echo "Done with blockMesh......"
# Generate the snappyHexMesh
echo "To follow the progress for snappyHexMesh, read logs/snappyHex.log....."
snappyHexMesh -overwrite > logs/snappyHex.log
echo "Done with snappyHexMesh......"