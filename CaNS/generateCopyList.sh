#!/bin/bash
# ---
# purpose: Prints the list of vex/vey/vez filenames for a given index range, for building a copy/rsync file list.
# usage: edit st/en/inter at top, run and redirect stdout.
# tags: utility
# note: same template as dopamine/genCopyList.sh — dup.
# ---

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
