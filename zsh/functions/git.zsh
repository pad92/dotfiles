git_prune_r() {
  for REPO in $(find $(pwd) -type d -name .git | sed 's@/.git@@g'); do
    echo -ne "- ${REPO}"
    RET=$(git --git-dir=${REPO}/.git remote prune origin 2>&1 )
    if [ $? -ne 0 ]; then
      echo -ne "\tERROR\n"
      echo "$(date +"%Y%m%d-%H%M") ERROR: ${REPO}" >> prune.log
      echo "${RET}"                                >> prune.log
      echo ""                                      >> prune.log
    else
      echo -ne "\tOK\n"
    fi
  done
}

git_pull_r() {
  for REPO in $(find $(pwd) -type d -name .git | sed 's@/.git@@g'); do
    echo -ne "- ${REPO}"
    RET=$(git --git-dir=${REPO}/.git pull 2>&1 )
    GIT_BRANCH_CURRENT=$(git --git-dir=${REPO}/.git rev-parse --abbrev-ref HEAD)
    if [ $? -ne 0 ]; then
      GIT_BRANCH_DEFAULT=$(git --git-dir=${REPO}/.git remote show origin | awk '/HEAD branch/ {print $NF}')
      RET=$(git --git-dir=${REPO}/.git checkout ${GIT_BRANCH_DEFAULT} 2>&1)
      RET=$(git --git-dir=${REPO}/.git pull 2>&1)
      if [ $? -ne 0 ]; then
        echo -ne "\tERROR : unable to pull ${GIT_BRANCH_DEFAULT}\n"
      else
        echo -ne "\tERROR : unable to pull ${GIT_BRANCH_CURRENT}, switch to ${GIT_BRANCH_DEFAULT}"
      fi
      echo "$(date +"%Y%m%d-%H%M") ERROR: ${REPO}" >> prune.log
      echo "${RET}"                                >> prune.log
      echo ""                                      >> prune.log
    else
      echo -ne "\tOK\n"
    fi
  done
}
