export ZSH=${HOME}/.dotfiles/zsh

# Create cache dir if not exist
ZSH_CACHE_DIR="${HOME}/.zcache"
[[ -d ${ZSH_CACHE_DIR} ]] || mkdir ${ZSH_CACHE_DIR}

# add a function path for completion
fpath=($ZSH/completions $fpath)

# Load all of the config init files that end in .zsh
for config_file ($ZSH/init/*.zsh); do
  source $config_file
done
unset config_file


is_plugin() {
  local base_dir=$1
  local name=$2
  test -f $base_dir/plugins/$name/$name.plugin.zsh
}
# Add all defined plugins to fpath. This must be done
# before running compinit.
for plugin ($plugins); do
  if is_plugin $ZSH $plugin; then
    fpath=($ZSH/plugins/$plugin $fpath)
  fi
done
unset plugin
unset -f is_plugin

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
