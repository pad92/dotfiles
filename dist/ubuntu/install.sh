#!/bin/bash
# Modern, Idempotent, and Secure Ubuntu Setup Script
# Configured for Hyprland 0.55+ and mirroring Arch Linux package definitions
set -euo pipefail

# --- Color Helpers for Logging ---
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- 1. Root / Sudo Checks ---
if ! command -v sudo >/dev/null 2>&1; then
  log_err "Sudo is required to run this script. Please install sudo."
fi

# Detect Ubuntu Codename
CODENAME=$(lsb_release -cs)
log_info "Detected Ubuntu release: ${CODENAME}"

# Verify Ubuntu Version supports modern Wayland/Hyprland packages
# High preference for Ubuntu 24.04 (noble) or newer
if [ "${CODENAME}" = "focal" ] || [ "${CODENAME}" = "bionic" ]; then
  log_err "Ubuntu ${CODENAME} is too old for a stable Hyprland 0.55+ ecosystem. Please upgrade to 24.04 LTS (Noble) or newer."
fi

# Ensure key directories exist
sudo mkdir -p /etc/apt/keyrings /usr/share/keyrings

# --- 2. Bootstrap Minimal Keyring & Download Tools ---
log_info "Bootstrapping minimal required dependencies..."
sudo apt-get update
sudo apt-get install -y curl wget git gnupg ca-certificates lsb-release software-properties-common

# --- 3. Configure Scoped Third-Party Repositories (signed-by syntax) ---

# VS Codium
if [ ! -f "/etc/apt/sources.list.d/vscodium.list" ]; then
  log_info "Adding VS Codium repository..."
  wget -qO - https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg \
    | gpg --dearmor \
    | sudo tee /usr/share/keyrings/vscodium-archive-keyring.gpg > /dev/null
  echo "deb [signed-by=/usr/share/keyrings/vscodium-archive-keyring.gpg] https://download.vscodium.com/debs vscodium main" \
    | sudo tee /etc/apt/sources.list.d/vscodium.list
fi

# Spotify
if [ ! -f "/etc/apt/sources.list.d/spotify.list" ]; then
  log_info "Adding Spotify repository..."
  curl -fsSL https://download.spotify.com/debian/pubkey_5384CE82BA52C83A.asc \
    | gpg --dearmor \
    | sudo tee /usr/share/keyrings/spotify-archive-keyring.gpg > /dev/null
  echo "deb [signed-by=/usr/share/keyrings/spotify-archive-keyring.gpg] http://repository.spotify.com stable non-free" \
    | sudo tee /etc/apt/sources.list.d/spotify.list
fi

# Docker
if [ ! -f "/etc/apt/sources.list.d/docker.list" ]; then
  log_info "Adding Docker repository..."
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor \
    | sudo tee /etc/apt/keyrings/docker.gpg > /dev/null
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
fi

# HashiCorp
if [ ! -f "/etc/apt/sources.list.d/hashicorp.list" ]; then
  log_info "Adding HashiCorp repository..."
  curl -fsSL https://apt.releases.hashicorp.com/gpg \
    | gpg --dearmor \
    | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com ${CODENAME} main" \
    | sudo tee /etc/apt/sources.list.d/hashicorp.list
fi

# Proton Pass CLI
if ! command -v pass-cli >/dev/null 2>&1; then
  log_info "Installing Proton Pass CLI..."
  curl -fsSL https://proton.me/download/pass-cli/install.sh | bash
fi

# --- 4. Register Community PPAs for Hyprland 0.55+ ---
log_info "Enabling Ubuntu Universe repository..."
sudo add-apt-repository -y universe

log_info "Registering Community PPAs..."
# Using the highly-maintained cppiber PPA to fetch the latest Hyprland (0.55+)
sudo add-apt-repository -y ppa:cppiber/hyprland
sudo add-apt-repository -y ppa:papirus/papirus
sudo add-apt-repository -y ppa:zhangsongcui3371/fastfetch

# --- 5. Consolidated Package Installation (Matching Arch Linux Setup) ---
log_info "Updating package lists and running full installation..."
sudo apt-get update

# Note: Some applications from AUR or specialized packages are installed via standard snap/flatpak on Ubuntu
log_info "Installing system-wide applications and utilities..."
sudo apt-get install -y \
  apg \
  arj \
  bc \
  dnsutils \
  blueman \
  bluez \
  bluez-tools \
  cifs-utils \
  fastfetch \
  ffmpeg \
  fprintd \
  hdparm \
  htop \
  hunspell \
  hunspell-en-us \
  hunspell-fr \
  hyphen-en-us \
  hyphen-fr \
  inetutils-ping \
  jq \
  libjsoncpp-dev \
  lhasa \
  lshw \
  lzip \
  lzop \
  man-db \
  plocate \
  nfs-common \
  ntfs-3g \
  pipewire \
  pipewire-audio-client-libraries \
  pipewire-audio \
  pipewire-jack \
  pipewire-pulse \
  powertop \
  rkhunter \
  seahorse \
  thefuck \
  tlp \
  traceroute \
  tumbler \
  usbutils \
  wireplumber \
  xarchiver \
  xclip \
  fonts-font-awesome \
  xfonts-terminus \
  fonts-inconsolata \
  fonts-jetbrains-mono \
  fonts-ubuntu \
  fonts-noto-color-emoji \
  gtk2-engines-murrine \
  papirus-icon-theme \
  alacritty \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-compose-plugin \
  firefox \
  fwupd \
  gnome-calculator \
  gnome-disk-utility \
  gnome-keyring \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  nautilus \
  p7zip-full \
  pavucontrol \
  spotify-client \
  terraform \
  vlc \
  codium \
  zsh

# --- 6. Hyprland 0.55+ Core & Desktop Environment Packages ---
log_info "Installing Hyprland 0.55+ ecosystem..."
sudo apt-get install -y \
  hyprland \
  hyprlock \
  hypridle \
  waybar \
  wofi \
  wlogout \
  grim \
  slurp \
  wl-clipboard \
  cliphist \
  xdg-desktop-portal-hyprland \
  brightnessctl \
  playerctl \
  policykit-1-gnome \
  qtwayland5 \
  qt6-wayland

# --- 7. Docker Configuration & Cleanup ---
log_info "Configuring Docker user groups..."
CURRENT_USER="${USER:-$(whoami)}"
sudo usermod -a -G docker "${CURRENT_USER}"

log_info "Cleaning up unused package caches..."
sudo apt-get autoremove -y
sudo apt-get autoclean

# --- 9. Font Setup (Idempotent) ---
FONT_HOME="$HOME/.local/share/fonts"
log_info "Setting up custom fonts..."
mkdir -p "$FONT_HOME/adobe-fonts"

if [ ! -d "$FONT_HOME/adobe-fonts/source-code-pro" ]; then
  log_info "Cloning Source Code Pro font..."
  git clone \
     --branch release \
     --depth 1 \
     'https://github.com/adobe-fonts/source-code-pro.git' \
     "$FONT_HOME/adobe-fonts/source-code-pro"
else
  log_info "Source Code Pro font directory already exists, pulling updates..."
  git -C "$FONT_HOME/adobe-fonts/source-code-pro" pull || log_warn "Failed to update fonts repo, using existing local copy."
fi

log_info "Rebuilding font cache..."
fc-cache -f "$FONT_HOME/adobe-fonts/source-code-pro"

# --- 10. Summary and Next Steps ---
log_success "Ubuntu Hyprland 0.55+ setup completed successfully!"
echo -e "\n${GREEN}✔ Installation successful!${NC}"
echo -e "${YELLOW}Please log out and log back in to apply your new docker group permissions and initialize your Hyprland session.${NC}\n"
