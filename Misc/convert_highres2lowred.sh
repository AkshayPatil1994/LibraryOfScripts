#!/bin/bash

# Usage: ./convert_pdf.sh <density> <input_file> <quality> <output_file>

# Assign command-line arguments to variables
DENSITY="$1"
INPUT_FILE="$2"
QUALITY="$3"
OUTPUT_FILE="$4"

# Check if all arguments are provided
if [ $# -ne 4 ]; then
  echo "Usage: $0 <density> <input_file> <quality> <output_file>"
  exit 1
fi

# Run the ImageMagick command
magick -density "$DENSITY" "$INPUT_FILE" -quality "$QUALITY" "$OUTPUT_FILE"
