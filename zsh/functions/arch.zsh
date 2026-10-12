# Arch
## remove orphans
clean_arch() {
  local failed=0
  local orphan_packages
  local pacnew_files

  if ! command -v pacman &>/dev/null; then
    echo "Error: pacman could not be found"
    return 1
  fi

  if ! command -v yay &>/dev/null; then
    echo "Error: yay could not be found"
    return 1
  fi

  if ! command -v paccache &>/dev/null; then
    echo "Error: paccache could not be found"
    return 1
  fi

  if ! orphan_packages=$(pacman -Qtdq); then
    echo "Error: could not query orphan packages"
    return 1
  fi

  if [[ -n "$orphan_packages" ]]; then
    echo "Removing orphan packages..."
    if ! sudo pacman -Rns ${(z)orphan_packages}; then
      echo "Error: failed to remove orphan packages"
      failed=1
    fi
  fi

  if ! yay -Scc --noconfirm; then
    echo "Error: failed to clean yay caches"
    failed=1
  fi

  echo "Checking for .pacnew, .pacsave, and .pacorig files..."
  if ! pacnew_files=$(sudo find /etc -regextype posix-extended -regex '.*\.pac(new|save|orig)$' 2>/dev/null); then
    echo "Error: could not check for pacnew, pacsave, or pacorig files"
    failed=1
  elif [[ -n "$pacnew_files" ]]; then
    echo "Found the following configuration files that need attention:"
    echo "$pacnew_files"
    echo ""
    echo "To compare each file with vimdiff:"
    echo "for file in $(echo $pacnew_files | tr '\n' ' '); do"
    echo "  if [ -f \"\${file%.pacnew}\" ]; then"
    echo "    echo \"Comparing \${file%.pacnew} with \${file}\""
    echo "    vim -d \"\${file%.pacnew}\" \"\$file\""
    echo "  fi"
    echo "done"
  else
    echo "No .pacnew, .pacsave, or .pacorig files found."
  fi

  if ! paccache -ruk0; then
    echo "Error: failed to remove uninstalled package caches"
    failed=1
  fi
  if ! paccache -rk1; then
    echo "Error: failed to retain the latest package cache"
    failed=1
  fi

  return $failed
}

## get fastest mirrors
if command -v reflector &>/dev/null; then
  mirror() {
    if ! command -v reflector &> /dev/null; then
      echo "Error: reflector could not be found"
      return 1
    fi

    local sort_type="$1"
    local -a sort_args=()
    case "$sort_type" in
      delay|score|age) sort_args=(--sort "$sort_type") ;;
    esac

    sudo reflector -p https -c FR --latest 20 --fastest 20 \
      $sort_args --verbose --save /etc/pacman.d/mirrorlist
  }

  alias mirror="mirror"
  alias mirrord="mirror delay"
  alias mirrors="mirror score"
  alias mirrora="mirror age"
fi

## Update
arch_update() {
    local -a failed_steps=()

    if ! command -v yay &> /dev/null; then
      echo "Error: yay could not be found"
      return 1
    fi

    echo "Updating system..."
    yay -Syu || { echo "Yay update failed, skipping subsequent steps"; return 1; }

    if ! clean_arch; then
        echo "Warning: package cleanup failed"
        failed_steps+=("package cleanup")
    fi

    if command -v fwupdmgr &> /dev/null; then
        echo "Checking for firmware updates..."
        if fwupdmgr refresh; then
            if ! fwupdmgr update -y; then
                echo "Error: firmware update failed"
                failed_steps+=("firmware update")
            fi
        else
            echo "Error: firmware refresh failed; skipping firmware update"
            failed_steps+=("firmware refresh")
        fi
    fi

    if command -v flatpak &> /dev/null; then
        echo "Updating flatpak packages..."
        if ! flatpak update -y; then
            echo "Error: Flatpak update failed"
            failed_steps+=("Flatpak update")
        fi
        if ! flatpak uninstall --unused -y; then
            echo "Error: Flatpak unused-runtime cleanup failed"
            failed_steps+=("Flatpak unused-runtime cleanup")
        fi
    fi

    if (( ${#failed_steps} )); then
        echo "System update completed, but these steps failed: ${(j:, :)failed_steps}"
        return 1
    fi

    echo "System update completed successfully."
    return 0
}
