# Copy one or more SSH keys currently loaded in ssh-agent to a remote server.
# It displays a menu of available keys based on their comments, allows selection,
# and appends them to the remote server's ~/.ssh/authorized_keys while avoiding duplicates.
ssh-copy-agent-keys() {
    local remote_host="$1"
    local selection
    local payload
    local idx
    local i
    local key_line
    local kcomment
    
    local -a agent_keys
    local -a comments
    local -a selected_indices
    local -a raw_indices
    local -a fields

    # 1. Get keys from ssh-agent
    agent_keys=(${(f)"$(ssh-add -L 2>/dev/null)"})
    if [[ $? -ne 0 || ${#agent_keys} -eq 0 || "$agent_keys[1]" == "The agent has no identities." ]]; then
        echo "Error: No SSH keys found in the ssh-agent. Please add them first using 'ssh-add'." >&2
        return 1
    fi

    # 2. Extract comments and display the list
    echo "Available SSH keys in agent:"
    for i in {1..${#agent_keys}}; do
        key_line="$agent_keys[$i]"
        fields=(${=key_line})
        kcomment="${(j: :)fields[3,-1]}"
        if [[ -z "$kcomment" ]]; then
            kcomment="Key #$i (no comment)"
        fi
        comments[$i]="$kcomment"
        echo "  [$i] $kcomment"
    done

    # 3. Prompt for selection
    echo -n "Select the key(s) to copy (e.g. '1', '1 3', 'all', or 'q' to quit): "
    read -r selection
    
    if [[ -z "$selection" || "$selection" == "q" || "$selection" == "quit" ]]; then
        echo "Aborted."
        return 0
    fi

    if [[ "${selection:l}" == "all" ]]; then
        selected_indices=({1..${#agent_keys}})
    else
        # Replace commas with spaces and split into array
        selection="${selection//,/ }"
        raw_indices=(${(z)selection})
        for idx in $raw_indices; do
            if [[ "$idx" =~ ^[0-9]+$ ]] && (( idx >= 1 && idx <= ${#agent_keys} )); then
                selected_indices+=($idx)
            else
                echo "Warning: Invalid index '$idx' ignored." >&2
            fi
        done
    fi

    if [[ ${#selected_indices} -eq 0 ]]; then
        echo "No valid keys selected. Aborted." >&2
        return 1
    fi

    # 4. Get remote host if not provided as argument
    if [[ -z "$remote_host" ]]; then
        echo -n "Enter remote host (e.g., user@remote-server or server-alias): "
        read -r remote_host
        if [[ -z "$remote_host" ]]; then
            echo "Error: Remote host is required." >&2
            return 1
        fi
    fi

    # 5. Build the payload of public keys
    payload=""
    echo "Selected keys to copy:"
    for idx in $selected_indices; do
        echo "  - $comments[$idx]"
        payload+="$agent_keys[$idx]"$'\n'
    done

    # 6. Copy keys to remote host
    echo "Copying key(s) to $remote_host..."
    # Pipe the keys into ssh, check for duplicates, and append to authorized_keys
    echo -n "$payload" | ssh "$remote_host" '
      mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
      while read -r line; do
        [ -z "$line" ] && continue
        key_part=$(echo "$line" | cut -d" " -f2)
        comment=$(echo "$line" | cut -d" " -f3-)
        [ -z "$comment" ] && comment="Key (no comment)"
        if ! grep -qF "$key_part" ~/.ssh/authorized_keys 2>/dev/null; then
          echo "$line" >> ~/.ssh/authorized_keys
          echo "  [+] Added: $comment"
        else
          echo "  [=] Already exists: $comment"
        fi
      done
    '
    
    if [[ $? -eq 0 ]]; then
        echo "Success: Selected SSH key(s) successfully processed."
    else
        echo "Error: Failed to copy keys to $remote_host." >&2
        return 1
    fi
}
