#!/bin/bash
# Check if both source and target directories were provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 /path/to/source_directory /path/to/target_directory"
    exit 1
fi
SOURCE_DIR=$1
TARGET_DIR=$2
# List of specific files to process in each processor directory (for first part)
# These files will be copied from the source into the target.
FILES=("epsilon" "k")
# List of specific files to copy in the second part
# these are solutions that come from the target.
SECOND_FILES=("nut" "p" "phi" "U")
# Ordered list of directories to check (from largest to smallest)
DIRECTORIES=(5500 5000 4500 4000 3500)

##################################################################################
# DO NOT TOUCH THINGS BELOW UNLESS YOU ARE ABOSLUTELY SURE OF WHAT YOU ARE DOING #
##################################################################################

# Find the largest existing directory from our ordered list
# We'll check the first processor directory to determine which one exists
FIRST_PROC_DIR=$(ls -d "$SOURCE_DIR"/processor* | head -1)
SOURCE_SUB_DIR=""
if [ -d "$FIRST_PROC_DIR" ]; then
    for DIR in "${DIRECTORIES[@]}"; do
        if [ -d "$FIRST_PROC_DIR/$DIR" ]; then
            SOURCE_SUB_DIR="$DIR"
            echo "Found directory $SOURCE_SUB_DIR, using it as source for all processors..."
            break
        fi
    done
fi

# If no valid directory was found, exit
if [ -z "$SOURCE_SUB_DIR" ]; then
    echo "Error: None of the directories ${DIRECTORIES[*]} exist in $FIRST_PROC_DIR"
    exit 1
fi

# Find all processor directories in source
for SOURCE_PROC_DIR in "$SOURCE_DIR"/processor*; do
    # Extract the processor number
    PROC_NUM=$(basename "$SOURCE_PROC_DIR" | sed 's/processor//')
    # Define target processor directory
    TARGET_PROC_DIR="$TARGET_DIR/processor$PROC_NUM"
    echo "Processing processor$PROC_NUM..."

    # Check if source directory exists
    if [ ! -d "$SOURCE_PROC_DIR/$SOURCE_SUB_DIR" ]; then
        echo "Warning: $SOURCE_PROC_DIR/$SOURCE_SUB_DIR does not exist, skipping..."
        continue
    fi

    # Create target processor directory if it doesn't exist
    if [ ! -d "$TARGET_PROC_DIR" ]; then
        echo "Creating $TARGET_PROC_DIR..."
        mkdir -p "$TARGET_PROC_DIR"
    fi

    # Create temporary directory in target using the found source directory name
    if [ ! -d "$TARGET_PROC_DIR/$SOURCE_SUB_DIR" ]; then
        mkdir -p "$TARGET_PROC_DIR/$SOURCE_SUB_DIR"
    fi

    # Copy files from source to target
    echo "Copying files from $SOURCE_PROC_DIR/$SOURCE_SUB_DIR to $TARGET_PROC_DIR/$SOURCE_SUB_DIR..."
    # Copy each file individually to handle cases where some may be missing
    for FILE in "${FILES[@]}"; do
        if [ -f "$SOURCE_PROC_DIR/$SOURCE_SUB_DIR/$FILE" ]; then
            cp "$SOURCE_PROC_DIR/$SOURCE_SUB_DIR/$FILE" "$TARGET_PROC_DIR/$SOURCE_SUB_DIR/"
            echo "Copied $FILE"
        else
            echo "Warning: $SOURCE_PROC_DIR/$SOURCE_SUB_DIR/$FILE does not exist, skipping..."
        fi
    done

    # Now move directories as requested
    if [ -d "$TARGET_PROC_DIR/0" ]; then
        # Check if 0_original already exists
        if [ -d "$TARGET_PROC_DIR/0_original" ]; then
            echo "Warning: $TARGET_PROC_DIR/0_original already exists, removing it..."
            rm -rf "$TARGET_PROC_DIR/0_original"
        fi
        # Move 0 to 0_original
        echo "Moving $TARGET_PROC_DIR/0 to $TARGET_PROC_DIR/0_original..."
        mv "$TARGET_PROC_DIR/0" "$TARGET_PROC_DIR/0_original"
    else
        echo "Warning: $TARGET_PROC_DIR/0 does not exist, skipping backup..."
    fi

    # Now get the flowDir value from 0_original/U (before moving the source directory to 0)
    if [ -f "$TARGET_PROC_DIR/0_original/U" ]; then
        # Extract the vector value from the flowDir line, treating binary files as text
        FLOW_DIR_VALUE=$(grep -a "flowDir" "$TARGET_PROC_DIR/0_original/U" | grep -a -o "([^;]*)" | head -1 | tr -d "()")
        if [ -n "$FLOW_DIR_VALUE" ]; then
            echo "Found flowDir vector in $TARGET_PROC_DIR/0_original/U: $FLOW_DIR_VALUE"
            # Process each file in the source directory (which will become 0)
            for FILE in "${FILES[@]}"; do
                FILE_PATH="$TARGET_PROC_DIR/$SOURCE_SUB_DIR/$FILE"
                if [ -f "$FILE_PATH" ]; then
                    # Replace just the vector part, keeping the original formatting
                    sed -i.bak "s/\([ ]*flowDir[ ]*(\)[^;)]*\();\)/\1$FLOW_DIR_VALUE\2/" "$FILE_PATH" && rm "$FILE_PATH.bak"
                    echo "Updated flowDir in $FILE_PATH"
                else
                    echo "Warning: $FILE_PATH does not exist or is not a regular file"
                fi
            done
        else
            echo "Warning: No flowDir vector found in $TARGET_PROC_DIR/0_original/U"
        fi
    else
        echo "Warning: $TARGET_PROC_DIR/0_original/U does not exist, skipping flowDir replacement..."
    fi

    # Move source directory to 0
    if [ -d "$TARGET_PROC_DIR/$SOURCE_SUB_DIR" ]; then
        echo "Moving $TARGET_PROC_DIR/$SOURCE_SUB_DIR to $TARGET_PROC_DIR/0..."
        mv "$TARGET_PROC_DIR/$SOURCE_SUB_DIR" "$TARGET_PROC_DIR/0"
    else
        echo "Warning: $TARGET_PROC_DIR/$SOURCE_SUB_DIR does not exist, cannot move to 0..."
    fi
done
echo "First part of operations complete."

# ----------------------- SECOND PART -----------------------
# Get a list of all processor directories in the target directory
echo "Starting second part of operations..."
processor_dirs=$(find "$TARGET_DIR" -maxdepth 1 -type d -name "processor*" | sort)
for proc_dir in $processor_dirs; do
  # Extract the processor number
  proc_num=${proc_dir#*processor}
  # Define source and destination directories
  src_dir="${proc_dir}/0_original"
  dest_dir="${proc_dir}/0"
  # Check if source directory exists
  if [ ! -d "$src_dir" ]; then
    echo "Warning: Source directory $src_dir does not exist. Skipping."
    continue
  fi
  # Check if destination directory exists, create if not
  if [ ! -d "$dest_dir" ]; then
    echo "Creating destination directory $dest_dir"
    mkdir -p "$dest_dir"
  fi
  # Copy the specified files
  echo "Copying files from $src_dir to $dest_dir"
  for file in "${SECOND_FILES[@]}"; do
    if [ -f "$src_dir/$file" ]; then
      cp "$src_dir/$file" "$dest_dir/"
      echo "  Copied $file"
    else
      echo "  Warning: File $file not found in $src_dir"
    fi
  done
done
echo "All operations complete!"
