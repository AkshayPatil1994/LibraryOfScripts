#!/bin/zsh

# Name of the log file to be used
logfile="logs/run_200.log"
# Prefix for the output file in residuals
outfileprefix="200"
# Make sure that residuals folder exists
if [ -d "residuals" ]; then
	echo "Residuals folder already exists....."
else
	echo "Generating residuals folder....."
	mkdir residuals
fi
# Setup the outputfile names for all parameters
pout="residuals/res_p_$outfileprefix"
Uxout="residuals/res_Ux_$outfileprefix"
Uyout="residuals/res_Uy_$outfileprefix"
Uzout="residuals/res_Uz_$outfileprefix"
kout="residuals/res_k_$outfileprefix"
omegaout="residuals/res_omega_$outfileprefix"
epsilonout="residuals/res_epsilon_$outfileprefix"
# Log pressure residuals
cat $logfile  | grep -A 1 "Solving for Uz" | grep "Solving for p" | awk '{print $8}' | tr -d \, > $pout
# Log velocity residuals
cat $logfile  | grep "Solving for Ux" | awk '{print $8}' | tr -d \, > $Uxout
cat $logfile  | grep "Solving for Uy" | awk '{print $8}' | tr -d \, > $Uyout
cat $logfile  | grep "Solving for Uz" | awk '{print $8}' | tr -d \, > $Uzout
# Turbulence parameters residuals
cat $logfile | grep "Solving for k" | awk '{print $8}' | tr -d \, > $kout
cat $logfile | grep "Solving for omega" | awk '{print $8}' | tr -d \, > $omegaout
cat $logfile | grep "Solving for epsilon" | awk '{print $8}' | tr -d \, > $epsilonout