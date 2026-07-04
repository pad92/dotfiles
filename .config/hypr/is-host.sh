#!/usr/bin/env bash
#
# is-host.sh — Exit 0 if the current machine's hostname matches $1.
#
# Mirrors the detection order used by include/host.lua (env HOSTNAME/HOST,
# then /proc, then the hostname binary) so host-conditional shell commands
# in hypridle.conf (and any future listener) don't each reimplement it.
#
# Usage: is-host.sh <hostname>

set -eu

current="${HOSTNAME:-${HOST:-}}"
if [ -z "$current" ] && [ -r /proc/sys/kernel/hostname ]; then
  current="$(cat /proc/sys/kernel/hostname)"
fi
if [ -z "$current" ]; then
  current="$(hostname)"
fi

[ "$current" = "$1" ]
