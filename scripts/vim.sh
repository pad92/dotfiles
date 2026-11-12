# shellcheck shell=bash
# This script installs vim configuration and plugins from my dotfiles
# Usage: curl -sL https://gitlab.com/pad92/dotfiles/-/raw/main/scripts/vim.sh | bash
# or: wget -qO- https://gitlab.com/pad92/dotfiles/-/raw/main/scripts/vim.sh | bash

set -euo pipefail

# The archive holds .vimrc, ~/.vim and the plugins pinned in the dotfiles
# role, as a Vim package under .vim/pack/dotfiles/start. Vim loads them at
# startup, so nothing is cloned or installed afterwards.
PACKAGE_URL="https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/raw/vim.tar.gz?job=package_vim"

# Print an error message to stderr and exit
die() {
    echo "Error: $*" >&2
    exit 1
}

main() {
    # Check if vim files already exist
    if [[ -e ~/.vim || -e ~/.vimrc ]]; then
        die "$HOME/.vim or $HOME/.vimrc already exists."
    fi

    echo "Downloading and extracting vim configuration package..."
    if command -v curl &> /dev/null; then
        curl -fsSL "$PACKAGE_URL" | tar -xz -C ~/
    elif command -v wget &> /dev/null; then
        wget -qO- "$PACKAGE_URL" | tar -xz -C ~/
    else
        die "curl or wget is required to download the package."
    fi

    echo "Vim configuration successfully installed!"
}

main "$@"
