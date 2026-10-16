_git_for_each_repo() {
  local action="$1"
  local git_dir repo
  local action_status=0

  while IFS= read -r -d '' git_dir; do
    repo="${git_dir:h}"
    [[ "$repo" == */.terraform/* ]] && continue
    "$action" "$repo" || action_status=1
  done < <(find "$PWD" \( -type l -o -type d \) -name .git -print0)
  return $action_status
}

_git_prune_repo() {
    local repo="$1"
    local output
    echo -ne "- ${repo}"
    if ! output=$(git -C "$repo" remote prune origin 2>&1); then
      echo -ne "\tERROR\n"
      echo "$(date +"%Y%m%d-%H%M") ERROR: ${repo}" >> prune.log
      echo "${output}" >> prune.log
      echo "" >> prune.log
      return 1
    else
      echo -ne "\tOK\n"
    fi
}

_git_pull_repo() {
    local repo="$1"
    local output
    echo -ne "- ${repo}"
    if ! output=$(git -C "$repo" pull --ff-only 2>&1); then
      echo -ne "\tERROR : unable to fast-forward current branch\n"
      echo "$(date +"%Y%m%d-%H%M") ERROR: ${repo}" >> prune.log
      echo "${output}" >> prune.log
      echo "" >> prune.log
      return 1
    else
      echo -ne "\tOK\n"
    fi
}

git_prune_r() { _git_for_each_repo _git_prune_repo }
git_pull_r() { _git_for_each_repo _git_pull_repo }

gi() {
  curl -sLw \"\\\n\" https://www.toptal.com/developers/gitignore/api/$@
}
