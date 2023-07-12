#!/bin/sh

grep -rh ^Exec ~/.config/autostart/*.desktop | while read -r line ; do
  ${line:5} &
done
