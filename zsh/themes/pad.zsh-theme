if [ "$USER" = "root" ]; then
    _USERCOLOR="red"
else
    _USERCOLOR="green"
fi

function collapse_pwd {
    echo $(pwd | sed -e "s,^$HOME,~,")
}


# The prompt
PROMPT='
%! %{$fg[cyan]%}%n%{$reset_color%} at %{$fg[yellow]%}%m%{$reset_color%} in %{$fg_bold[green]%}$(collapse_pwd)%{$reset_color%}$(git_prompt_info)
'

# The right-hand prompt
RPROMPT='%(?..%{$fg[red]%}%?↵%{$reset_color%} )'

# local time, color coded by last return code
time_enabled="%(?.%{$fg[green]%}.%{$fg[red]%})%T%{$reset_color%}"
time_disabled="%{$fg[green]%}%*%{$reset_color%}"
time=$time_enabled

ZSH_THEME_GIT_PROMPT_PREFIX=" on [%{$fg[cyan]%}"
ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%} ]"
ZSH_THEME_GIT_PROMPT_CLEAN="%{$fg[green]%} ✔"
ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[yellow]%} ♻"

ZSH_THEME_GIT_PROMPT_STATUS_PREFIX="["
ZSH_THEME_GIT_PROMPT_STATUS_SUFFIX=" %{$reset_color%}]"
ZSH_THEME_GIT_PROMPT_UNTRACKED="%{$fg[cyan]%} ✱"
ZSH_THEME_GIT_PROMPT_ADDED="%{$fg[green]%} ✚"
ZSH_THEME_GIT_PROMPT_MODIFIED="%{$fg[yellow]%} ✎"
ZSH_THEME_GIT_PROMPT_DELETED="%{$fg[red]%} ✖"
ZSH_THEME_GIT_PROMPT_RENAMED="%{$fg[blue]%} ➟"
ZSH_THEME_GIT_PROMPT_UNMERGED="%{$fg[magenta]%} ♒"

ZSH_THEME_GIT_PROMPT_AHEAD="%{$fg[blue]%} ⩚"
ZSH_THEME_GIT_PROMPT_BEHIND="%{$fg[blue]%} ⩛"

ZSH_THEME_VIRTUALENV_PREFIX="%{${fg_bold[white]}%}(env: %{$fg[green]%}"
ZSH_THEME_VIRTUALENV_SUFFIX="%{${fg_bold[white]}%})%{${reset_color}%} "

# More symbols to choose from:
# ☀ ✹ ☄ ♆ ♀ ♁ ♐ ♇ ♈ ♉ ♚ ♛ ♜ ♝ ♞ ♟ ♠ ♣ ⚢ ⚲ ⚳ ⚴ ⚥ ⚤ ⚦ ⚒ ⚑ ⚐ ♺ ♻ ♼ ☰ ☱ ☲ ☳ ☴ ☵ ☶ ☷
# ✡ ✔ ✖ ✚ ✱ ✤ ✦ ❤ ➜ ➟ ➼ ✂ ✎ ✐ ⨀ ⨁ ⨂ ⨍ ⨎ ⨏ ⨷ ⩚ ⩛ ⩡ ⩱ ⩲ ⩵  ⩶ ⨠  ✭ ⚡ ☂
# ⬅ ⬆ ⬇ ⬈ ⬉ ⬊ ⬋ ⬒ ⬓ ⬔ ⬕ ⬖ ⬗ ⬘ ⬙ ⬟  ⬤ 〒 ǀ ǁ ǂ ĭ Ť Ŧ
