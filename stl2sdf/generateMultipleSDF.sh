#!/bin/bash

# Initalise python environment
source /home/apatil5/pythonenvs/stlpy/bin/activate
# Files to be computed
runmat=("45" "90" "135" "180")
# Check size of the array
lenrun=${#runmat[@]}
echo "SDF computations for $lenrun cases...."
# Loop over all and edit the files
for ((i=0;i<${lenrun};i++)); do
	echo "Running case $((i+1)) with theta=${runmat[$i]}....."
	# Edit the file with the right values
	sed_command='s/inFile = '\''assets\/voxelisedBulding_*[0-9]*deg.obj'\''/inFile = '\''assets\/voxelisedBulding_${runmat[$i]}deg.obj'\''/'
	eval "sed -i \"$sed_command\" generateSDFmpi.py"
	# Now grep and print to screen
	cat generateSDFmpi.py | grep "inFile = 'assets"
	# Set the log file name
	myLogfile="logs/sdf${runmat[$i]}deg.log"
	echo "Logging I/O to $myLogfile"
	# Run the SDF generator
	mpirun -np 12 python -u generateSDFmpi.py > $myLogfile
	# Convert the Arrays to CaNS
	python numpy2CaNSarray.py
	# Move the results to the results folder with the right name
	outu=$(echo "results/sdfu_${runmat[$i]}.bin")
	outv=$(echo "results/sdfv_${runmat[$i]}.bin")
	outw=$(echo "results/sdfw_${runmat[$i]}.bin")
	outp=$(echo "results/sdfp_${runmat[$i]}.bin")
	mv assets/sdfu.bin $outu
	mv assets/sdfv.bin $outv
	mv assets/sdfw.bin $outw
	mv assets/sdfp.bin $outp
	# Echo end of loop message
	echo "Done with case $((i+1)) with theta=${runmat[$i]}...."
	echo "-		-	-	-	-"
done
