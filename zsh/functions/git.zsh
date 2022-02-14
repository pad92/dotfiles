git_rp() {
  for REPO in $(find ${PWD} -type d -name .git | sed 's@/.git@@g'); do
    echo ${REPO}
    GIT_PRUNE=$(git -C "${REPO}" remote prune origin)
  done
}
