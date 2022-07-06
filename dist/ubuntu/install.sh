#!/bin/sh
sudo apt update
sudo apt-get upgrade -y
sudo apt install curl wget git pavucontrol python3-i3ipc -y
wget -qO - https://regolith-desktop.io/regolith.key | sudo apt-key add -
wget -qO - https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg \
    | gpg --dearmor \
    | sudo dd of=/usr/share/keyrings/vscodium-archive-keyring.gpg
curl -sS https://download.spotify.com/debian/pubkey_5E3C45D7B312C643.gpg | sudo apt-key add -
sudo mkdir -p /etc/apt/keyrings ; curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -

if [ ! -f "/etc/apt/sources.list.d/regolith.list" ]; then
  echo deb "[arch=amd64] https://regolith-desktop.io/release-ubuntu-focal-amd64 focal main" | \
    sudo tee /etc/apt/sources.list.d/regolith.list
fi

if [ ! -f "/etc/apt/sources.list.d/vscodium.list" ]; then
  echo 'deb [ signed-by=/usr/share/keyrings/vscodium-archive-keyring.gpg ] https://download.vscodium.com/debs vscodium main' \
    | sudo tee /etc/apt/sources.list.d/vscodium.list
fi

if [ ! -f "/etc/apt/sources.list.d/spotify.list" ]; then
  echo "deb http://repository.spotify.com stable non-free" | sudo tee /etc/apt/sources.list.d/spotify.list
fi

if [ ! -f "/etc/apt/sources.list.d/docker.list" ]; then
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
fi

sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo add-apt-repository ppa:aslatter/ppa
sudo add-apt-repository ppa:snwh/ppa

sudo apt update
sudo apt install -y \
  alacritty \
  ca-certificates \
  nitrogen \
  xautolock \
  thefuck \
  codium \
  picom \
  terraform \
  containerd.io \
  curl \
  docker-ce \
  docker-ce-cli \
  docker-compose-plugin \
  git \
  gnupg \
  htop \
  i3-gaps \
  lsb-release \
  neofetch \
  spotify-client \
  vim \
  fonts-font-awesome \
  zsh

sudo usermod -a -G docker $USER

sudo apt-get autoremove -y
sudo apt-get autoclean

sudo snap install teams
sudo snap remove chromium


FONT_HOME=~/.local/share/fonts

mkdir -p "$FONT_HOME/adobe-fonts"

git clone \
   --branch release \
   --depth 1 \
   'https://github.com/adobe-fonts/source-code-pro.git' \
   "$FONT_HOME/adobe-fonts/source-code-pro" && \
fc-cache -f -v "$FONT_HOME/adobe-fonts/source-code-pro"

wget -qO /tmp/1password.deb https://downloads.1password.com/linux/debian/amd64/stable/1password-latest.deb && sudo dpkg -i /tmp/1password.deb && rm /tmp/1password.deb
