#!/bin/bash
startAngle=10     # Starting angle of the simulation
interval=20       # Interval/increment between each angle
endAngle=350       # Ending value of the angle
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
#       Do not touch beyond this line unless you are absolutely sure of what              #
#       you are doing                                                                     #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Setting up the array for all the angles used in this simulation
for ((i=${startAngle};i<=${endAngle};i+=${interval})); do
        foldername="fields_$i"
        echo "Working on $foldername ..."
        mkdir $foldername/1200
        mv $foldername/{epsilon,k,U,p,phi,nut,uniform} $foldername/1200/
        ls $foldername/
done
