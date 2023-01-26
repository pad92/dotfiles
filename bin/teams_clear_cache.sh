#!/bin/sh

# This script cleans all cache for Microsoft Teams on Linux
# Tested on Ubuntu-like, Debian by @necrifede, Arch Linux by @lucas-dclrcq and Manjaro with flatpak by @danie1k. Feel free to test/use in other distributions.
# Tested Teams via snap package.
# Tested Teams via flatpak package.
#
# fork from https://gist.github.com/mrcomoraes/c83a2745ef8b73f9530f2ec0433772b7
#
# Variable process name is defined on case statement.

export TEAMS_PROCESS_NAME=teams
cd "$HOME"/.var/app/com.microsoft.Teams/config/Microsoft/Microsoft\ Teams || exit 1

# Test if Microsoft Teams is running
if [ "$(pgrep ${TEAMS_PROCESS_NAME} | wc -l)" -gt 1 ]; then
  rm -rf Application\ Cache/Cache/*
  rm -rf blob_storage/*
  rm -rf Cache/* # Main cache
  rm -rf Code\ Cache/js/*
  rm -rf databases/*
  rm -rf GPUCache/*
  rm -rf IndexedDB/*
  rm -rf Local\ Storage/*
  #rm -rf backgrounds/* # Background function presents on Teams for Windows only.
  find ./ -maxdepth 1 -type f -name "*log*" -exec rm {} \;
  sleep 5
  killall ${TEAMS_PROCESS_NAME}
  # After this, MS Teams will open again.
else
  echo "Microsoft Teams is not running."
  exit
fi
