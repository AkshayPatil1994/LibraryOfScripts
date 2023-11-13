#!/bin/bash

st=151000	# Starting index of the file
en=160000	# Ending index of the file
inter=1000	# File write interval

# Start the for loop and generate the files to be copied
for ((num=st; num<=en; num+=inter)); do
	filename=$(printf 'vex_fld_%07d.bin' $num)
	echo $filename
	filename=$(printf 'vey_fld_%07d.bin' $num)
	echo $filename
	filename=$(printf 'vez_fld_%07d.bin' $num)
	echo $filename
done
