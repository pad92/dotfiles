#
# Defines TheFuck aliases.
#

if (( ! $+commands[thefuck] )); then
  return 1
fi

eval $(thefuck --alias)
