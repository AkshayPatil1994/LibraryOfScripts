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

# Slow down the video using ffmpeg
ffmpeg -i input_movie.mp4 -filter:v "setpts=2.0*PTS" slow_movie.mp4

# Vertical and horizontal stack of multiple videos
ffmpeg -i contour.mp4 -i velocity.mp4 -filter_complex vstack finalout.mp4  # Verticall stack
ffmpeg -i contour.mp4 -i velocity.mp4 -filter_complex hstack finalout.mp4. # Horizontally stack

# Nstacks
ffmpeg -i video1.mp4 -i video2.mp4 -i video3.mp4 -filter_complex "[0:v][1:v][2:v]vstack=inputs=3" -c:v libx264 output.mp4

# High Quality GIF
ffmpeg -i out.mp4 -vf "fps=5,scale=1028:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 output.gif
