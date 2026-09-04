#!/bin/bash

# ============================================================
# USER INPUT PARAMETERS
# ============================================================

create_users=0                  # Boolean flag: 0 = test, 1 = create users
filename="users.txt"            # File containing: username password
group_name="students3d"         # Group to associate users with
default_shell="/usr/bin/bash"   # Login shell


# ============================================================
# CHECKS
# ============================================================

if [[ ! -f "$filename" ]]; then
    echo "ERROR: User file '$filename' not found."
    exit 1
fi

if ! getent group "$group_name" > /dev/null; then
    echo "ERROR: Group '$group_name' does not exist."
    exit 1
fi


# ============================================================
# PROCESS USERS
# ============================================================

users=()

while read -r my_user my_pass; do

    # Skip empty lines
    [[ -z "$my_user" ]] && continue

    users+=("$my_user")

    if [[ "$create_users" -eq 1 ]]; then

        echo "Creating user: $my_user"

        # Create user without setting the password yet
        sudo useradd \
            -m \
            -g "$group_name" \
            -s "$default_shell" \
            "$my_user"

        if [[ $? -ne 0 ]]; then
            echo "ERROR: Failed to create user $my_user"
            continue
        fi

        # Set password
        echo "$my_user:$my_pass" | sudo chpasswd

        if [[ $? -ne 0 ]]; then
            echo "ERROR: Failed to set password for $my_user"
            continue
        fi

        echo "Finished creating user ${my_user}"

        # ====================================================
        # OpenFOAM setup
        # ====================================================

        echo "Setting up OpenFOAM-v2412 for user ${my_user}"

        echo "alias of2412='source /opt/OpenFOAM-v2412/etc/bashrc'" \
            | sudo tee -a "/home/$my_user/.bashrc" > /dev/null

        echo "shopt -s direxpand" \
            | sudo tee -a "/home/$my_user/.bashrc" > /dev/null

        # Make sure the user owns their .bashrc
        sudo chown "$my_user:$group_name" "/home/$my_user/.bashrc"

        echo "Finished setting up ${my_user}"
        echo

    else

        echo "USER: $my_user with password: $my_pass"

    fi

done < "$filename"


# ============================================================
# SUMMARY
# ============================================================

echo "Finished processing all ${#users[@]} users."
