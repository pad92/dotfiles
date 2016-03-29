if [ -f /etc/arch-release ];then
    if [ -x $(which yaourt) ]; then

        # Yaourt alias
        alias ya-up='yaourt -Syua'
        alias ya-check='yaourt -Qk'
        alias ya-remove='yaourt -Rns'

        # Pacman alias
        alias pacman='pacman-color'
        alias pac-upg='sudo pacman -Syu'        # Synchronize with repositories before upgrading packages that are out of date on the local system.
        alias pac-in='sudo pacman -S'           # Install specific package(s) from the repositories
        alias pac-ins='sudo pacman -U'          # Install specific package not from the repositories but from a file 
        alias pac-re='sudo pacman -R'           # Remove the specified package(s), retaining its configuration(s) and required dependencies
        alias pac-rem='sudo pacman -Rns'        # Remove the specified package(s), its configuration(s) and unneeded dependencies
        alias pac-rep='pacman -Si'              # Display information about a given package in the repositories
        alias pac-reps='pacman -Ss'             # Search for package(s) in the repositories
        alias pac-loc='pacman -Qi'              # Display information about a given package in the local database
        alias pac-locs='pacman -Qs'             # Search for package(s) in the local database

        # Additional pacman alias examples
        alias pac-mir='sudo pacman -Syy'                # Force refresh of all package lists after updating /etc/pacman.d/mirrorlist
        if [ -x "$(which alsi)" ]; then
            alsi
        fi
    fi
    if [ -x $(which keychain) ]; then
        eval $(keychain --eval --agents ssh -Q --quiet id_rsa)
    fi
fi
