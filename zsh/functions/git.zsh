git_prune_r() {
  for REPO in $(find $(pwd) -type d -name .git | sed 's@/.git@@g'); do
    echo -ne "- ${REPO}"
    PRUNE=$(git --git-dir=${REPO}/.git remote prune origin 2&>1 )
    if [ $? -ne 0 ]; then
      echo -ne "\tERROR\n"
      echo "$(date +"%Y%m%d-%H%M") ERROR: ${REPO}" >> prune.log
      echo "${PRUNE}"                              >> prune.log
      echo ""                                      >> prune.log
    else
      echo -ne "\tOK\n"
    fi
  done
}
