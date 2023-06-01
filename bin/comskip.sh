#!/bin/sh

~/.dotfiles/bin/comcut --lockfile=/tmp/comchap.lock "$1"
#HandBrakeCLI -i "$1" -o "$1".mkv --format mkv --encoder x264 --quality 20 --loose-anamorphic --decomb fast --x264-preset fast --h264-profile high --h264-level 4.1
