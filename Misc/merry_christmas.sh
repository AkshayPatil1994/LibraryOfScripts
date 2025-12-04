#!/bin/bash

# Setup the default user input values
INTERVAL=${1:-0.5}                      # Default 0.5 seconds
MESSAGE=${2:-"Merry Christmas!"}        # Default message
#
# ANSI color codes
#
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
RESET='\033[0m'
#
# Array of colors for decorations
#
COLORS=("$RED" "$YELLOW" "$BLUE" "$MAGENTA" "$CYAN" "$WHITE")
#
# Function to generate tree
#
draw_tree() {
    local color_index=$1
    clear
    #
    # Tree layers
    #
    local tree=(
        "        *        "
        "       ***       "
        "      *0*0*      "
        "     ***0***     "
        "    **0***0**    "
        "   *****0*****   "
        "  ***0*****0***  "
        " ****0**0**0**** "
        "*******0*********"
        "    *******      "
        "      ***        "
    )
    
    # Calculate starting position for message
    local msg_row=2
    local spacing=5
    
    # Print tree with decorations and message
    for i in "${!tree[@]}"; do
        local line="${tree[$i]}"
        local colored_line=""
        
        # Replace 0s with colored decorations
        for ((j=0; j<${#line}; j++)); do
            char="${line:$j:1}"
            if [ "$char" = "0" ]; then
                local color="${COLORS[$(( (color_index + j) % ${#COLORS[@]} ))]}"
                colored_line+="${color}O${RESET}"
            elif [ "$char" = "*" ]; then
                colored_line+="${GREEN}*${RESET}"
            else
                colored_line+="$char"
            fi
        done
        
        # Print tree line with message on the side
        if [ $i -eq $msg_row ]; then
            echo -e "${colored_line}$(printf '%*s' $spacing '')${MESSAGE}"
        else
            echo -e "$colored_line"
        fi
    done
    
    # Trunk
    echo -e "      ${YELLOW}|||${RESET}"
    echo -e "      ${YELLOW}|||${RESET}"
}
#
# Animation loop
#
echo "Press Ctrl+C to exit..."
sleep 1

counter=0
while true; do
    draw_tree $counter
    counter=$(( (counter + 1) % ${#COLORS[@]} ))
    sleep "$INTERVAL"
done
