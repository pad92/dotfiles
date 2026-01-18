#!/bin/bash
# This script installs vim configuration and plugins from my dotfiles
# Usage: curl -s https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | bash
# or: wget -qO - https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | bash

# Function to detect OS and install git if needed
install_git_if_needed() {
    if ! command -v git &> /dev/null; then
        echo "Git is not installed. Installing git..."

        # Detect OS family
        if command -v pacman &> /dev/null; then
            # Arch Linux
            sudo pacman -Syu --noconfirm git
        elif command -v apt &> /dev/null; then
            # Debian/Ubuntu
            sudo apt update
            sudo apt install -y git
        elif command -v dnf &> /dev/null; then
            # Rocky Linux/RHEL/Fedora
            sudo dnf install -y git
        else
            echo "Unsupported OS. Please install git manually."
            exit 1
        fi

        if ! command -v git &> /dev/null; then
            echo "Failed to install git. Exiting."
            exit 1
        fi
    fi
}

# Check if vim files already exist
if [ -e ~/.vim ] || [ -e ~/.vimrc ]; then
    echo '~/.vim or ~/.vimrc already exist'
    exit 1
fi

# Install git if needed
install_git_if_needed

# Create temporary directory
TMP_VIM=$(mktemp -d)

# Clone repository
git clone --recursive https://gitlab.com/pad92/dotfiles.git "${TMP_VIM}"

# Move files to home directory
mv "${TMP_VIM}/.vim" ~/
mv "${TMP_VIM}/.vimrc" ~/

# Remove temporary directory
rm -rf "${TMP_VIM}"

# Install vim bundles
vim +BundleInstall! +BundleClean +q
