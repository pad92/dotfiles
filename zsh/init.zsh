export ZSH=${HOME}/.dotfiles/zsh/

# Create cache dir if not exist
[[ -d ${HOME}/.zcache ]] || mkdir ${HOME}/.zcache

# add a function path
fpath=($ZSH/completions $fpath)

# Load all of the config files in ~/oh-my-zsh that end in .zsh
# TIP: Add files you don't want in git to .gitignore
for config_file ($ZSH/init/*.zsh); do
  source $config_file
done
unset config_file

is_plugin() {
  local base_dir=$1
  local name=$2
  test -f $base_dir/plugins/$name/$name.plugin.zsh \
    || test -f $base_dir/plugins/$name/_$name
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
for funcfiles ($ZSH/functions/*); do
  source $funcfiles
done
unset funcfiles

# Figure out the SHORT hostname
SHORT_HOST=${HOST/.*/}

# Load and run compinit
autoload -U compinit
compinit -i -d "${ZSH_COMPDUMP}"

# Load all of the plugins that were defined in ~/.zshrc
for plugin ($plugins); do
  if [ -f $ZSH/plugins/$plugin/$plugin.plugin.zsh ]; then
    source $ZSH/plugins/$plugin/$plugin.plugin.zsh
  fi
done
unset plugin

# Theme
source "$ZSH/themes/$ZSH_THEME.zsh-theme"
