#!/bin/bash
# ---
# purpose: Verifies presence of expected velocity field binary output files (vex/vey/vez) over a numbered range to spot missing/incomplete output.
# usage: edit start/end/interval at top, run from case dir (expects data/ subfolder).
# tags: postprocessing, utility
# note: same template as dopamine/checkfiles.sh, different file-naming convention — dup.
# ---

start=1000 	# Starting index of the file
end=160000	# Ending index of the file
interval=1000	# File write interval

# Initialise the iterator and total file counter
fileNum=0
totFile=0
# Beging the for loop to count and check if files are present
for ((num=start; num<=end; num+=interval)); do

	filename=$(printf 'data/vex_fld_%07d.bin' $num)
	if [[ -r $filename ]]; then
		echo "$filename exist."
		((fileNum=fileNum+1))
	else
		echo "problem finding $filename...."
	fi
	((totFile=totFile+1))
	filename=$(printf 'data/vey_fld_%07d.bin' $num)
	if [[ -r $filename ]]; then
		echo "$filename exist."
		((fileNum=fileNum+1))
	else
		echo "problem finding $filename...."
	fi
	((totFile=totFile+1))
	filename=$(printf 'data/vez_fld_%07d.bin' $num)
	if [[ -r $filename ]]; then
		echo "$filename exist."
		((fileNum=fileNum+1))
	else
		echo "problem finding $filename...."
	fi
	((totFile=totFile+1))
done
# Print to screen the total number of files present
echo "Total files present $fileNum/$totFile"
