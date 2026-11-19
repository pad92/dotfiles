# GitLab CI Pipeline

This page documents the root-level [`.gitlab-ci.yml`](../.gitlab-ci.yml). The
repository is also hosted on **GitHub** ([`.github/workflows/`](../.github/workflows))
and a self-hosted **Gitea** instance. Shared CI tasks use scripts from
[`scripts/ci/`](../scripts/ci).

## Stages

```
test → validate → package → pages → release
```

## Included templates

| Template                              | Provides                                               |
| ------------------------------------- | ------------------------------------------------------ |
| `Jobs/Secret-Detection.gitlab-ci.yml` | Scans commits for leaked secrets.                      |
| `Jobs/SAST.gitlab-ci.yml`             | Static application security testing.                   |
| `Jobs/SAST-IaC.gitlab-ci.yml`         | Scans infrastructure configuration, including Ansible. |

All jobs inherit the `chataigne` runner tag from `default:tags`.

## Jobs

| Job                  | Stage    | Runs when                                                                                                           | Purpose                                                                     |
| -------------------- | -------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Security scanners    | test     | Scanner template rules match                                                                                        | Scan source, infrastructure configuration, and commits for security issues. |
| `unit_tests`         | test     | Every default-branch, tag and scheduled pipeline; elsewhere, changes to code, tests, roles, scripts or CI settings  | Run the Python suite in parallel under coverage.                            |
| `shell_tests`        | test     | Same as `unit_tests`                                                                                                | Run `make test-shell` next to the Python suite.                             |
| `pages_tests`        | test     | Same changes as `build_pages_review`, on any branch; never on tags                                                  | Run the page generator tests (`test_gen_pages.py`).                         |
| `ansible_lint`       | validate | Branch and tag pipelines                                                                                            | Install `make` and the pinned Ansible tools, then run `make lint-ansible`.  |
| `package_vim`        | package  | Every default-branch pipeline; elsewhere, changes to `.vim/`, `.vimrc`, the role defaults or `fetch_vim_plugins.py` | Package Vim configuration and pinned plugins as `vim.tar.gz`.               |
| `package_zsh`        | package  | Every default-branch pipeline; elsewhere, changes to the Zsh tree, `.zshrc.j2` or the build scripts                 | Package Zsh configuration and pinned plugins as `zsh.tar.gz`.               |
| `package_nvim`       | package  | Every default-branch pipeline; elsewhere, changes to `.config/nvim/` in pushes and merge requests                   | Package Neovim configuration as `nvim.tar.gz`.                              |
| `pages`              | pages    | Default branch when a Markdown file or the page generator changes, or a `vX.Y.Z` release tag                        | Build and deploy the documentation site to `public/`.                       |
| `build_pages_review` | pages    | Non-default branch or merge request with matching changes                                                           | Build the documentation site for review without deploying it.               |
| `create_release`     | release  | A tag is pushed (`$CI_COMMIT_TAG`)                                                                                  | Publish a release with notes from `CHANGELOG.md`.                           |

### `unit_tests` and `shell_tests`

[`scripts/ci/run_unit_tests.py`](../scripts/ci/run_unit_tests.py) runs the
Python tests in parallel. A few tests drive `ansible-playbook` for up to two
minutes while most take milliseconds, so each slow test gets its own process and starts
first. The durations of the previous run are kept in the runner cache under
`.cache/unit-tests/`, with one key for every branch. Without them, the first
run starts one process per test class and is slower. The job also caches pip
downloads and the Ansible collections, keyed on their requirement files. The
log ends with the slowest tests.

Splitting `unit_tests` into two `parallel` shards was tried and reverted: both
shards ran on the same runner host, competed for its CPUs and each lasted longer
(about 850 s) than the single job (about 690 s). Shard only if the runner has
spare capacity.

The job runs on Python 3.14 with `COVERAGE_CORE=sysmon`, which makes branch
coverage cheaper than the default tracer. Tests started as subprocesses, such as
`ansible-playbook`, are not traced.

`shell_tests` runs `make test-shell`, the shell and zsh scripts of `tests/`,
next to `unit_tests`, on the same Python image and requirements. The Makefile
holds the list, so a new script runs in CI and locally alike. It only reads the pip
cache, so the two concurrent jobs never overwrite each other's archive.

On merge requests and branch pushes, the two jobs run only when a change
touches `ansible/`, `tests/`, `scripts/`, `requirements-*.txt`, `.coveragerc`,
`.gitlab-ci.yml`, `.gitmodules`, `Makefile`, `ansible.cfg` or `mypy.ini`. The
tests do not read Markdown files or `assets/`, so documentation-only changes
skip them. A branch with an open merge request runs them only in the merge
request pipeline, not in the push pipeline. A new branch has no diff to
compare, so GitLab runs them. When a test starts reading
another path, add it to `.unit_test_rules` in `.gitlab-ci.yml`.

### `pages_tests`

This job runs `scripts/ci/test_gen_pages.py` on `alpine:latest` with `git`,
`python3`, `py3-markdown` and `py3-pygments`, on the changes that start
`build_pages_review`, plus the test file and the Hyprtoolkit palette that the
style tests compare with `style.css`. Some tests build a throwaway Git
repository; the Pages jobs do not install Git, so the generator tests run apart.

### `pages`

This job runs on `alpine:latest`, installs `python3`, `py3-markdown` and
`py3-pygments`, and
calls [`scripts/ci/build_pages.sh`](../scripts/ci/build_pages.sh). The GitHub
`deploy-pages.yml` workflow and local `post-commit` hook use the same script.
Every Markdown file of the repository becomes a page, and relative links to
other files point to the GitLab file browser at `CI_COMMIT_SHA`. The canonical
URLs, `sitemap.xml` and `robots.txt` use `https://dotfiles.depad.fr/`, the
domain `CI_PAGES_URL` redirects to (`url` in `scripts/ci/pages.json`). The
[`deploy-pages.yml`](../.github/workflows/README.md#deploy-pagesyml) section
describes the page layout, the link rules and the site settings.

The `pages` job deploys documentation from the default branch when a Markdown
file or the page generator changes, and from `vX.Y.Z` release tags. The `build_pages_review` job builds
documentation on non-default branches and merge requests without deploying it.
GitLab treats `rules:changes` as true on pipelines without a push diff, so the
review job explicitly skips tag pipelines
([GitLab rules](https://docs.gitlab.com/ci/yaml/#ruleschanges)).

1. `pages` runs on the default branch after documentation changes and on release
   tags. It publishes the site from that commit.
2. `build_pages_review` runs on other branches and merge requests, then uploads a
   short-lived `public/` artifact for validation only.

> [!NOTE]
> `build_pages.sh` uses POSIX `sh` and does not require Git, so it runs on the
> minimal `alpine` image with only the Python packages above. Without Git, `gen_pages.py`
> finds the Markdown files by walking the checkout and skips the submodules
> listed in `.gitmodules`.

### `create_release`

When a `v*` tag is pushed, this job runs
[`scripts/ci/extract_release_notes.sh`](../scripts/ci/extract_release_notes.sh)
to extract that version's section from `CHANGELOG.md`, then passes the notes to
`release-cli create`.

> [!IMPORTANT]
> Release notes come from `CHANGELOG.md` **at the tagged commit**. Add the
> `## [vX.Y.Z]` section before pushing the tag. Without it, the release uses the
> placeholder "No specific notes found".

## Shared scripts (`scripts/ci/`)

| Script                     | Used by                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| `build_pages.sh`           | GitLab `pages`, GitHub `deploy-pages.yml`, local `post-commit` hook |
| `extract_release_notes.sh` | GitLab `create_release`, GitHub `release.yml`                       |
| `gen_pages.py`             | `build_pages.sh`, with the settings of `pages.json`                 |

Both shell scripts use **POSIX `sh`**, so they run on minimal CI images such as
the `alpine` job.

## Variables & secrets

The pipeline uses GitLab's predefined variables; no custom CI/CD variables are
needed.

| Name                                    | Used by                              | Source                      | Manual setup |
| --------------------------------------- | ------------------------------------ | --------------------------- | ------------ |
| `CI_JOB_TOKEN`                          | `create_release` (`release-cli`)     | Predefined for every job    | None         |
| `CI_COMMIT_TAG`                         | `create_release` rule + release name | Predefined on tag pipelines | None         |
| `CI_COMMIT_BRANCH`, `CI_DEFAULT_BRANCH` | `pages` rules                        | Predefined                  | None         |

> [!NOTE]
> `release-cli` uses the predefined `CI_JOB_TOKEN` to authenticate with the
> Releases API. No personal access token or _Settings → CI/CD → Variables_ entry
> is needed.

The included **SAST**, **IaC Scanning**, and **Secret Detection** templates run
with their defaults and need no custom variables.
