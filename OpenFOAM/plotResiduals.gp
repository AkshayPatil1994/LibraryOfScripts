#!/bin/bash
# Force check if `plots` directory exists
if [ -d "plots" ]; then
	echo "Plots directory already exists"
else
	echo "Generating plots directory to save figures..."
	mkdir plots
fi
# Name of all the turbulence closures
turbClosure=("kOmegaSST" "kEpsilon")
retauarray=("200" "400" "600" "800" "1000" "1500" "2000" "2500" "3000" "5000")
# Grep and edit the plotting file for each variable
lenClosure=${#turbClosure[@]}
lenretau=${#retauarray[@]}
for ((i=0;i<${lenClosure};i++)); do
    for ((j=0;j<${lenretau};j++)); do
	# Edit the Retau value
        sed_command='s/fileInt=*[0-9]*[[:space:]]# Location/fileInt=${retauarray[$j]}	# Location/'
        eval "sed -i \"$sed_command\" plotres.gp"
	# Edit the closure name
	sed_command='s/turbClos=\"[^\"]*\"[[:space:]]# turbModel/turbClos=\"${turbClosure[$i]}\"	# turbModel/'
	eval "sed -i \"$sed_command\" plotres.gp"
        gnuplot plotres.gp
        echo "Done with case Retau:${retauarray[$j]} and Closure:${turbClosure[$i]}"
    done
done
