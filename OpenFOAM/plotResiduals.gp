# Request argument from the user for case index
fileInt = 200
# Set the plot output type
#set term png size 1200,1200
#set output "residualHistory.png"
set term qt
# Set Plot Formatting Parameters
set title "Residual History" font "Times New Roman,20"
set key outside 
set size square
set grid
set border lw 1.5
#set logscale x
set logscale y
set xlabel "Interation Count" font "Times New Roman,15"
set ylabel "Normalised Residuals" font "Times New Roman,15"
# Set the style and color for each data file
set style data linespoints
set style line 1 lc rgb "red" ps 1
set style line 2 lc rgb "blue" ps 1
set style line 3 lc rgb "green" ps 1
set style line 4 lc rgb "orange" ps 1
set style line 5 lc rgb "purple" ps 1
set style line 6 lc rgb "black" ps 1
# Setting ticks
set ytics 1e-6, 1e-1, 1e-1

# Plot the data
plot sprintf('residuals/res_p_%d',fileInt) title "Pressure" ls 1, \
     sprintf('residuals/res_Ux_%d',fileInt) title "Ux" ls 2, \
     sprintf('residuals/res_Uy_%d',fileInt) title "Uy" ls 3, \
     sprintf('residuals/res_Uz_%d',fileInt) title "Uz" ls 4, \
     sprintf('residuals/res_k_%d',fileInt) title "k" ls 5, \
     sprintf('residuals/res_epsilon_%d',fileInt) title "epsilon" ls 6, \
#    sprintf('residuals/res_omega_'.fileInt title "omega" ls 6, \