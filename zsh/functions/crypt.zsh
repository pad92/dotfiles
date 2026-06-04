md5()    { echo -n $1 | openssl md5 /dev/stdin }
sha1()   { echo -n $1 | openssl sha1 /dev/stdin }
sha256() { echo -n $1 | openssl dgst -sha256 /dev/stdin }
sha512() { echo -n $1 | openssl dgst -sha512 /dev/stdin }

#urlencode() { python -c "import sys, urllib as ul; print ul.quote_plus(sys.argv[1])" "$@" }
#urldecode() { python -c "import sys, urllib as ul; print ul.unquote_plus(sys.argv[1])" "$@" }

gpg-encrypt() {
  if [ -z "$1" ]; then
    echo "Usage: gpg-encrypt <file_or_directory1> [file_or_directory2 ...]"
    return 1
  fi

  setopt localoptions nullglob

  local files=()
  for arg in "$@"; do
    if [ -f "$arg" ]; then
      if [[ "$arg" != *.gpg ]]; then
        files+=("$arg")
      fi
    elif [ -d "$arg" ]; then
      local dir_files=($arg/**/*(.-DN))
      files+=("${dir_files[@]:#*.gpg}")
    else
      echo "Warning: '$arg' does not exist or is not a valid file/directory."
    fi
  done

  if [ ${#files[@]} -eq 0 ]; then
    echo "No files to encrypt."
    return 1
  fi

  local email
  echo -n "Recipient's GPG email: "
  read -r email

  if [ -z "$email" ]; then
    echo "Error: Recipient email cannot be empty."
    return 1
  fi

  local success_files=()
  for file in "${files[@]}"; do
    local output="${file}.gpg"
    echo "Encrypting '$file' to '$output'..."
    gpg --encrypt --trust-model always --recipient "$email" --output "$output" "$file"
    if [ $? -eq 0 ]; then
      touch -r "$file" "$output"
      success_files+=("$file")
    else
      echo "Failed to encrypt '$file'"
    fi
  done

  if [ ${#success_files[@]} -gt 0 ]; then
    echo "Successfully encrypted ${#success_files[@]} file(s)."
    if _gpg_confirm_and_delete "Do you want to delete the original unencrypted file(s)? (y/N): " "${success_files[@]}"; then
      echo "Original unencrypted file(s) deleted."
    fi
  fi
}

gpg-decrypt() {
  if [ -z "$1" ]; then
    echo "Usage: gpg-decrypt <file_or_directory1> [file_or_directory2 ...]"
    return 1
  fi

  setopt localoptions nullglob

  local files=()
  for arg in "$@"; do
    if [ -f "$arg" ]; then
      files+=("$arg")
    elif [ -d "$arg" ]; then
      files+=($arg/**/*.gpg(.-DN))
    else
      echo "Warning: '$arg' does not exist or is not a valid file/directory."
    fi
  done

  if [ ${#files[@]} -eq 0 ]; then
    echo "No GPG files found to decrypt."
    return 1
  fi

  local success_files=()
  for file in "${files[@]}"; do
    if [[ "$file" == *.tar.gz.gpg || "$file" == *.tgz.gpg ]]; then
      echo "Decrypting and extracting archive '$file'..."
      gpg --decrypt "$file" | tar -xzf -
      if [[ ${pipestatus[1]} -eq 0 && ${pipestatus[2]} -eq 0 ]]; then
        success_files+=("$file")
      else
        echo "Decryption failed for '$file'"
      fi
    elif [[ "$file" == *.gpg ]]; then
      local out_file="${file%.gpg}"
      echo "Decrypting '$file' to '$out_file'..."
      gpg --decrypt --output "$out_file" "$file"
      if [ $? -eq 0 ]; then
        touch -r "$file" "$out_file"
        success_files+=("$file")
      else
        echo "Decryption failed for '$file'"
      fi
    fi
  done

  if [ ${#success_files[@]} -gt 0 ]; then
    echo "Successfully decrypted ${#success_files[@]} file(s)."
    if _gpg_confirm_and_delete "Do you want to delete the encrypted file(s)? (y/N): " "${success_files[@]}"; then
      echo "Encrypted file(s) deleted."
    fi
  fi
}

_gpg_confirm_and_delete() {
  local prompt="$1"
  shift
  local files=("$@")

  local reply
  echo -n "$prompt"
  read -r reply
  if [[ "$reply" =~ ^[yY](es)?$ ]]; then
    for file in "${files[@]}"; do
      rm -f "$file"
    done
    return 0
  fi
  return 1
}




