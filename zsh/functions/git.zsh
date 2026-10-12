_git_for_each_repo() {
  local action="$1"
  local git_dir repo

  while IFS= read -r -d '' git_dir; do
    repo="${git_dir:h}"
    [[ "$repo" == */.terraform/* ]] && continue
    "$action" "$repo"
  done < <(find "$PWD" \( -type l -o -type d \) -name .git -print0)
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
    else
      echo -ne "\tOK\n"
    fi
}

_git_pull_repo() {
    local repo="$1"
    local output current_branch default_branch
    echo -ne "- ${repo}"
    if ! output=$(git -C "$repo" pull 2>&1); then
      current_branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
      default_branch=$(git -C "$repo" symbolic-ref --quiet --short refs/remotes/origin/HEAD)
      default_branch=${default_branch#origin/}
      if [[ -z "$default_branch" ]]; then
        echo -ne "\tERROR : unable to determine the default branch\n"
      elif ! output=$(git -C "$repo" checkout "$default_branch" 2>&1) || ! output=$(git -C "$repo" pull 2>&1); then
        echo -ne "\tERROR : unable to pull ${default_branch}\n"
      else
        echo -ne "\tERROR : unable to pull ${current_branch}, switch to ${default_branch}"
      fi
      echo "$(date +"%Y%m%d-%H%M") ERROR: ${repo}" >> prune.log
      echo "${output}" >> prune.log
      echo "" >> prune.log
    else
      echo -ne "\tOK\n"
    fi
}

git_prune_r() { _git_for_each_repo _git_prune_repo }
git_pull_r() { _git_for_each_repo _git_pull_repo }

gi() {
  curl -sLw \"\\\n\" https://www.toptal.com/developers/gitignore/api/$@
}
