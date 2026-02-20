# Set terminal and output based on argument
if (exists("outfile")) {
    set terminal pngcairo size 1200,800 font "Arial,12"
    set output outfile
} else {
    set terminal qt size 1200,800 font "Arial,12"
}

# Set up the plot
set title "Solver Residuals vs Time" font "Arial,14 bold"
set xlabel "Time" font "Arial,12"
set ylabel "Initial Residual" font "Arial,12"

# Use semi-log scale
set logscale y

# Grid for better readability
set grid ytics xtics mxtics mytics

# Legend positioning
set key right top

# Line styles for clarity
set style line 1 lt 1 lw 2 pt 7 ps 0.5 lc rgb "#E41A1C"  # Red
set style line 2 lt 1 lw 2 pt 7 ps 0.5 lc rgb "#377EB8"  # Blue
set style line 3 lt 1 lw 2 pt 7 ps 0.5 lc rgb "#4DAF4A"  # Green
set style line 4 lt 1 lw 2 pt 7 ps 0.5 lc rgb "#984EA3"  # Purple
set style line 5 lt 1 lw 2 pt 7 ps 0.5 lc rgb "#FF7F00"  # Orange
set style line 6 lt 1 lw 2 pt 7 ps 0.5 lc rgb "#A65628"  # Brown

# CSV settings
set datafile separator ","

# Check that infile was provided
if (!exists("infile")) {
    print "ERROR: No input file specified. Use -e \"infile='yourfile.dat'\""
    exit
}

# Plot all parameters
plot infile using 1:2 with linespoints ls 1 title 'Ux', \
     '' using 1:3 with linespoints ls 2 title 'Uy', \
     '' using 1:4 with linespoints ls 3 title 'Uz', \
     '' using 1:5 with linespoints ls 4 title 'p', \
     '' using 1:6 with linespoints ls 5 title 'epsilon', \
     '' using 1:7 with linespoints ls 6 title 'k'

# Keep window open if plotting interactively
if (!exists("outfile")) { pause mouse close }
