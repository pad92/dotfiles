export ZSH="${HOME}/.local/share/dotfiles/zsh"

# Create cache dir and completions subdir if not exist
ZSH_CACHE_DIR="${HOME}/.zcache"
[[ -d ${ZSH_CACHE_DIR}/completions ]] || mkdir -p ${ZSH_CACHE_DIR}/completions

# add a function path for completion
fpath=($ZSH_CACHE_DIR/completions $ZSH/completions $fpath)

# Append the plugin directories (and their src/, as in zsh-completions) to
# fpath, including completion-only plugins such as httpie. init/completion.zsh
# runs compinit, so this must come before the init files: compinit only
# registers the completion functions already on fpath. They go last so that
# the completions shipped by zsh and by the packages (docker, age, ...) win
# over older plugin copies.
for plugin ($plugins); do
  if [[ -d $ZSH/plugins/$plugin ]]; then
    fpath+=($ZSH/plugins/$plugin)
    [[ -d $ZSH/plugins/$plugin/src ]] && fpath+=($ZSH/plugins/$plugin/src)
  fi
done
unset plugin

# Load all of the config init files that end in .zsh
for config_file ($ZSH/init/*.zsh); do
  source $config_file
done
unset config_file

# Load all functions script
for funcfiles ($ZSH/functions/*.zsh); do
  source $funcfiles
done
unset funcfiles

# Load all of the plugins that were defined in ~/.zshrc
for plugin ($plugins); do
  if [ -f $ZSH/plugins/$plugin/$plugin.plugin.zsh ]; then
    source $ZSH/plugins/$plugin/$plugin.plugin.zsh
  fi
done
unset plugin

# Theme
source "$ZSH/themes/$ZSH_THEME.zsh-theme"
