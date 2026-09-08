#!/bin/bash
# ---
# purpose: Verifies presence of expected Nek5000-style field output files (fields/channel_test.$num) over a numbered range.
# usage: edit start/end/interval at top, run in case dir.
# tags: postprocessing, utility
# note: same template as CaNS/checkfiles.sh, single-file-per-step naming — dup.
# ---

start=500 	# Starting index of the file
end=528500	# Ending index of the file
interval=500	# File write interval

# Initialise the iterator and total file counter
fileNum=0
totFile=0
# Beging the for loop to count and check if files are present
for ((num=start; num<=end; num+=interval)); do
	filename="fields/channel_test.$num"
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
