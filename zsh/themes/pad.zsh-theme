# Dynamic username color based on privilege (Red for root, Cyan for standard)
_USERCOLOR="%(!.red.cyan)"

# The prompt
# %!  - History event number
# %?  - Exit status of last command (shown in red only if non-zero)
# %n  - Username
# %m  - Hostname
# %~  - Current directory (contracted to ~ natively, no subshells!)
PROMPT='
%! %(?..%F{red}%?%f )%F{$_USERCOLOR}%n%f@%F{yellow}%m%f %B%F{green}%~%f%b$(git_prompt_info)
'

# The right-hand prompt (uncomment if desired)
# RPROMPT='%(?..%F{red}%?↵%f)'

# Git Prompt configuration
ZSH_THEME_GIT_PROMPT_PREFIX=" [%F{cyan}"
ZSH_THEME_GIT_PROMPT_SUFFIX="%f ]"
ZSH_THEME_GIT_PROMPT_CLEAN="%F{green} ✔"
ZSH_THEME_GIT_PROMPT_DIRTY="%F{yellow} ♻"

ZSH_THEME_GIT_PROMPT_STATUS_PREFIX="["
ZSH_THEME_GIT_PROMPT_STATUS_SUFFIX=" %f]"
ZSH_THEME_GIT_PROMPT_UNTRACKED="%F{cyan} ✱"
ZSH_THEME_GIT_PROMPT_ADDED="%F{green} ✚"
ZSH_THEME_GIT_PROMPT_MODIFIED="%F{yellow} ✎"
ZSH_THEME_GIT_PROMPT_DELETED="%F{red} ✖"
ZSH_THEME_GIT_PROMPT_RENAMED="%F{blue} ➟"
ZSH_THEME_GIT_PROMPT_UNMERGED="%F{magenta} ♒"

ZSH_THEME_GIT_PROMPT_AHEAD="%F{blue} ⩚"
ZSH_THEME_GIT_PROMPT_BEHIND="%F{blue} ⩛"

ZSH_THEME_VIRTUALENV_PREFIX="%B%F{white}(env: %F{green}"
ZSH_THEME_VIRTUALENV_SUFFIX="%B%F{white})%f "

# More symbols to choose from:
# ☀ ✹ ☄ ♆ ♀ ♁ ♐ ♇ ♈ ♉ ♚ ♛ ♜ ♝ ♞ ♟ ♠ ♣ ⚢ ⚲ ⚳ ⚴ ⚥ ⚤ ⚦ ⚒ ⚑ ⚐ ♺ ♻ ♼ ☰ ☱ ☲ ☳ ☴ ☵ ☶ ☷
# ✡ ✔ ✖ ✚ ✱ ✤ ✦ ❤ ➜ ➟ ➼ ✂ ✎ ✐ ⨀ ⨁ ⨂ ⨍ ⨎ ⨏ ⨷ ⩚ ⩛ ⩡ ⩱ ⩲ ⩵  ⩶ ⨠  ✭ ⚡ ☂
# ⬅ ⬆ ⬇ ⬈ ⬉ ⬊ ⬋ ⬒ ⬓ ⬔ ⬕ ⬖ ⬗ ⬘ ⬙ ⬟  ⬤ 〒 ǀ ǁ ǂ ĭ Ť Ŧ
