# reload zshrc
function src()
{
  autoload -U compinit zrecompile
  compinit -i

  for f in ~/.zshrc ~/.zcompdump
  do
    zrecompile -p $f && command rm -f $f.zwc.old
  done

  source ~/.zshrc
}
