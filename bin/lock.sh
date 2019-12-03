#!/bin/sh

scrot /dev/shm/i3lock-temp.png
convert -scale 5% -scale 2000% /dev/shm/i3lock-temp.png /dev/shm/i3lock-current.png
convert -blur 10x10 /dev/shm/i3lock-current.png /dev/shm/i3lock-temp.png
convert -dither FloydSteinberg -colors 8 /dev/shm/i3lock-temp.png /dev/shm/i3lock-current.png
cp /dev/shm/i3lock-current.png /dev/shm/i3lock-temp.png
rm /dev/shm/i3lock-current.png
i3lock -i /dev/shm/i3lock-temp.png
rm /dev/shm/i3lock-temp.png
