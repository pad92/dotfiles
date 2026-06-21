# Arch
## remove orphans
if [ $(command -v pacman) ] && [ $(command -v yay) ]; then
  function clean_arch {
    # Validate that required commands exist
    if ! command -v pacman &> /dev/null; then
      echo "Error: pacman could not be found"
      return 1
    fi

    if ! command -v yay &> /dev/null; then
      echo "Error: yay could not be found"
      return 1
    fi

    ORPHAN=$(pacman -Qtdq)

    if [ -n "${ORPHAN}" ]; then
      echo "Remove orphans"
      sudo pacman -Rns $(pacman -Qtdq)
    fi
    yay -Scc --noconfirm
    echo "Checking for .pacnew, .pacsave, and .pacorig files..."
    PACNEW_FILES=$(sudo find /etc -regextype posix-extended -regex ".*\.pac(new|save|orig)$" 2> /dev/null)
    if [ -n "$PACNEW_FILES" ]; then
      echo "Found the following configuration files that need attention:"
      echo "$PACNEW_FILES"
      echo ""
      echo "To compare each file with vimdiff:"
      echo "for file in $(echo $PACNEW_FILES | tr '\n' ' '); do"
      echo "  if [ -f \"\${file%.pacnew}\" ]; then"
      echo "    echo \"Comparing \${file%.pacnew} with \${file}\""
      echo "    vim -d \"\${file%.pacnew}\" \"\$file\""
      echo "  fi"
      echo "done"
    else
      echo "No .pacnew, .pacsave, or .pacorig files found."
    fi
    paccache -ruk0
    paccache -rk1
  }
fi

## get fastest mirrors
if [ $(command -v reflector) ]; then
  function mirror() {
    # Validate that required command exists
    if ! command -v reflector &> /dev/null; then
      echo "Error: reflector could not be found"
      return 1
    fi

    local sort_type="$1"
    local cmd=""

    case "$sort_type" in
      "delay")
        cmd="sudo reflector -p https -c FR --latest 20 --fastest 20 --sort delay --verbose --save /etc/pacman.d/mirrorlist"
        ;;
      "score")
        cmd="sudo reflector -p https -c FR --latest 20 --fastest 20 --sort score --verbose --save /etc/pacman.d/mirrorlist"
        ;;
      "age")
        cmd="sudo reflector -p https -c FR --latest 20 --fastest 20 --sort age --verbose --save /etc/pacman.d/mirrorlist"
        ;;
      *)
        cmd="sudo reflector -p https -c FR --latest 20 --fastest 20 --verbose --save /etc/pacman.d/mirrorlist"
        ;;
    esac

    eval "$cmd"
  }

  alias mirror="mirror"
  alias mirrord="mirror delay"
  alias mirrors="mirror score"
  alias mirrora="mirror age"
fi

## Update
function arch_update {
    if ! command -v yay &> /dev/null; then
      echo "Error: yay could not be found"
      return 1
    fi

    echo "Updating system..."
    yay -Syu || { echo "Yay update failed, skipping subsequent steps"; return 1; }

    clean_arch

    if command -v fwupdmgr &> /dev/null; then
        echo "Checking for firmware updates..."
        if fwupdmgr refresh; then
            fwupdmgr update -y
        else
            echo "Warning: Firmware refresh failed"
        fi
    fi

    if command -v flatpak &> /dev/null; then
        echo "Updating flatpak packages..."
        flatpak update -y
        flatpak uninstall --unused -y
    fi
}
