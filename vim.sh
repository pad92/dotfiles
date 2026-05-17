#!/usr/bin/env bash
# This script installs vim configuration and plugins from my dotfiles
# Usage: curl -sL https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | bash
# or: wget -qO- https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | bash

set -euo pipefail

PACKAGE_URL="https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/raw/vim.tar.gz?job=package_vim"

# Print an error message to stderr and exit
die() {
    echo "Error: $*" >&2
    exit 1
}

# Function to detect OS and install git if needed
install_git_if_needed() {
    if command -v git &> /dev/null; then
        return 0
    fi

    echo "Git is not installed. Installing git..."

    # Detect OS family
    if command -v pacman &> /dev/null; then
        sudo pacman -Syu --noconfirm git
    elif command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y git
    else
        die "Unsupported OS. Please install git manually."
    fi

    # Verify installation
    if ! command -v git &> /dev/null; then
        die "Failed to install git."
    fi
}

main() {
    # Check if vim files already exist
    if [[ -e ~/.vim || -e ~/.vimrc ]]; then
        die "~/.vim or ~/.vimrc already exists."
    fi

    # Git is needed by Vundle to install plugins
    install_git_if_needed

    echo "Downloading and extracting vim configuration package..."
    if command -v curl &> /dev/null; then
        curl -sL "$PACKAGE_URL" | tar -xz -C ~/
    elif command -v wget &> /dev/null; then
        wget -qO- "$PACKAGE_URL" | tar -xz -C ~/
    else
        die "curl or wget is required to download the package."
    fi

    echo "Installing vim plugins via Vundle..."
    vim +PluginInstall! +qall

    echo "Vim configuration successfully installed!"
}

main "$@"
