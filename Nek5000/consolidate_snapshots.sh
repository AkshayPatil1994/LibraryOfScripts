#!/bin/bash

# Consolidate all duct0.f files from fields<num> directories into a single fields directory

# Create the new fields directory
if [ -d "fields" ]; then
    echo "Warning: 'fields' directory already exists. Skipping creation."
else
    mkdir -p fields
    echo "Created 'fields' directory"
fi

# Initialise counter for sequential numbering
counter=1

# Find all fields<num> directories and sort them numerically
for dir in $(find . -maxdepth 1 -type d -name 'fields[0-9]*' | sort -V); do
    echo "Processing $dir..."
    
    # Find all duct0.f files in the current directory, sorted numerically
    for file in $(find "$dir" -maxdepth 1 -type f -name 'duct0.f*' | sort -V); do
        # Get just the filename
        filename=$(basename "$file")
        
        # Create new filename with sequential numbering (5-digit format with leading zeros)
        new_filename=$(printf "duct0.f%05d" "$counter")
        
        # Move and rename the file
        mv "$file" "fields/$new_filename"
        echo "  Moved: $filename -> $new_filename"
        
        # Increment counter
        ((counter++))
    done
done

echo "Consolidation complete! Total files moved: $((counter - 1))"
