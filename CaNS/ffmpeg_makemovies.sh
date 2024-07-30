# A short list of ffmpeg and file rename routines that are useful

# Padd zeros to a figure that is not correctly named
starti=100        # Starting index
interval=100      # interval between two
endi=30000        # Ending index
width=5           # total number of zeros e.g. 1 will be 00001
# Main loop to rename files
for ((i=${starti};i<=${endi};i+=${interval})); do
	padded_number=$(printf "%0${width}d" $i)
	mv "figure_$i.png" "figure_$padded_number.png"
	
done

# Creates a movie using multiple pictures as long as the file is numbered with padded 0 
ffmpeg -framerate 30 -pattern_type glob -i 'figures/figure_*.png' -c:v libx264 -pix_fmt yuv420p out.mp4
