#!/bin/bash

st=483500	# Starting index of the file
en=528500	# Ending index of the file
inter=500	# File write interval

# Start the for loop and generate the files to be copied
for ((num=st; num<=en; num+=inter)); do
        filename="fields/channel_test.$num"
	echo $filename
done
