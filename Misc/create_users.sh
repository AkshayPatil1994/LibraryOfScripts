#!/bin/bash
# USER INPUT PARAMETERS
create_users="0"                # Boolean flag to create or test the users (0 or 1)
filename='user_data.txt'        # Name of the file where userdata is stored
group_name="students3d"         # Name of the group to associate the users
default_shell="/usr/bin/bash"   # Default login shell /usr/bin/bash or /usr/bin/zsh
#
# Read the users and passwords into the data frame 
#
users=()
while read -r my_user my_pass; do
        users+=("$my_user")     # Only store the username 
        if [ $create_users -eq 1 ]; then
                sudo useradd -m -g $group_name -p $(openssl passwd -1 '$my_pass') -s $default_shell $my_user
        fi
done < $filename
echo "Finished generating all ${#users[@]} users...."
