# GitLab CI Pipeline

This page documents the root-level [`.gitlab-ci.yml`](../.gitlab-ci.yml). The
repository is also hosted on GitHub ([`.github/workflows/`](../.github/workflows))
and on a self-hosted Gitea instance. The documentation site and the scripts of
[`scripts/ci/`](../scripts/ci) are shared by every forge and documented once,
on the GitHub Actions page: see
[Documentation site](../.github/workflows/README.md#documentation-site) and
[Shared scripts](../.github/workflows/README.md#shared-scripts-scriptsci).

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

All jobs inherit the `chataigne` runner tag from `default:tags`. A new commit
on a branch cancels the interruptible jobs of its previous pipeline
(`workflow:auto_cancel:on_new_commit: interruptible`). Only the tests and
`ansible_lint` are interruptible; package, Pages and release jobs always run
to the end.

## Jobs

| Job                  | Stage    | Runs when                                                                                                                             | Purpose                                                                                                    |
| -------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Security scanners    | test     | Scanner template rules match                                                                                                          | Scan source, infrastructure configuration and commits for security issues.                                 |
| `unit_tests`         | test     | Every default-branch, tag, scheduled or manual pipeline; elsewhere, changes to code, tests, roles, scripts or CI settings             | Run the Python suite in parallel under coverage.                                                           |
| `shell_tests`        | test     | Same as `unit_tests`                                                                                                                  | Run `make test-shell` next to the Python suite.                                                            |
| `pages_tests`        | test     | Same changes as `build_pages_review`, on any branch including the default one; never on tags                                          | Run the page generator tests (`test_gen_pages.py`).                                                        |
| `ansible_lint`       | validate | Branch and tag pipelines                                                                                                              | Install `make` and `requirements-ansible.txt`, which includes the test pins, then run `make lint-ansible`. |
| `package_vim`        | package  | Every default-branch pipeline; elsewhere, changes to `.vim/`, `.vimrc`, the role defaults, `fetch_vim_plugins.py` or `package_vim.sh` | Package Vim configuration and pinned plugins as `vim.tar.gz`.                                              |
| `package_zsh`        | package  | Every default-branch pipeline; elsewhere, changes to `zsh/`, `.zshenv`, `.zshrc.j2`, the role defaults or the build scripts           | Package Zsh configuration and pinned plugins as `zsh.tar.gz`.                                              |
| `package_nvim`       | package  | Every default-branch pipeline; elsewhere, changes to `.config/nvim/` in pushes and merge requests                                     | Package Neovim configuration as `nvim.tar.gz`.                                                             |
| `pages`              | pages    | Default branch when a site input changes, or a `vX.Y.Z` tag                                                                           | Build and deploy the documentation site to `public/`.                                                      |
| `build_pages_review` | pages    | Non-default branch or merge request with matching changes                                                                             | Build the documentation site for review without deploying it.                                              |
| `create_release`     | release  | Any tag pipeline (`$CI_COMMIT_TAG`)                                                                                                   | Publish a release with notes from `CHANGELOG.md`.                                                          |

### `unit_tests` and `shell_tests`

[`scripts/ci/run_unit_tests.py`](../scripts/ci/run_unit_tests.py) runs the
Python tests in parallel. A few tests drive `ansible-playbook` for minutes
while most take milliseconds, so each slow test gets its own process and starts
first. The durations of the previous run are kept in the runner cache under
`.cache/unit-tests/`, with a single key (`unit-test-durations`) shared by
every branch and saved even when the job fails. Without them, the first run
starts one process per test class and is slower. The job also caches pip
downloads and the Ansible collections, keyed on their requirement files. The
log ends with the slowest tests.

Splitting `unit_tests` into two `parallel` shards was tried and reverted: both
shards ran on the same runner host, competed for its CPUs and each lasted
longer (about 850 s) than the single job (about 690 s). Shard only if the
runner has spare capacity.

The job runs on Python 3.14 with `COVERAGE_CORE=sysmon`, which makes branch
coverage cheaper than the default tracer. Tests started as subprocesses, such
as `ansible-playbook`, are not traced. `coverage report` fails the job below
the `fail_under` floor of `.coveragerc` (98%), as `make coverage` does
locally, and the job publishes a Cobertura report.

`shell_tests` runs `make test-shell`, the shell and zsh scripts of `tests/`,
next to `unit_tests`, on the same Python image and requirements. The Makefile
holds the list, so a new script runs in CI and locally alike. The job only
reads the pip cache, so the two concurrent jobs never overwrite each other's
archive.

On merge requests and branch pushes, the two jobs run only when a change
touches `ansible/`, `tests/`, `scripts/`, `requirements-*.txt`, `.coveragerc`,
`.gitlab-ci.yml`, `.gitmodules`, `Makefile`, `ansible.cfg` or `mypy.ini`. The
tests do not read Markdown files or `assets/`, so documentation-only changes
skip them. A branch with an open merge request runs them only in the merge
request pipeline. A new branch has no diff to compare, so GitLab runs them.
When a test starts reading another path, add it to `.unit_test_rules` in
`.gitlab-ci.yml`.

### `pages_tests`

This job runs `scripts/ci/test_gen_pages.py` on `python:3.14-alpine` with
`git` and the `markdown` and `pygments` versions pinned in
`scripts/ci/pages-requirements.txt`. It watches the inputs of
`build_pages_review`, which include the test file and the Hyprtoolkit palette
that the style tests compare with `style.css`. Some tests build a throwaway Git
repository. The Pages jobs do not install Git, so the generator tests run in a
job of their own.

### `pages` and `build_pages_review`

Both jobs run on `python:3.14-alpine`, install the versions pinned in
[`scripts/ci/pages-requirements.txt`](../scripts/ci/pages-requirements.txt)
and call [`scripts/ci/build_pages.sh`](../scripts/ci/build_pages.sh). The
image has no Git, so `gen_pages.py` finds the Markdown files by walking the
checkout. Relative links to other files point to the GitLab file browser at
`CI_COMMIT_SHA`. The canonical URLs, `sitemap.xml` and `robots.txt` use
`https://dotfiles.depad.fr/`, the domain `CI_PAGES_URL` redirects to (`url` in
`scripts/ci/pages.json`). The page layout, the link rules, the menu and the
site settings are described in
[Documentation site](../.github/workflows/README.md#documentation-site).

`pages` publishes the site from the default branch when a site input changes:
a Markdown file, an image, the stylesheet, an icon, `gen_pages.py`,
`pages.json`, `build_pages.sh`, `pages-requirements.txt` or `.gitlab-ci.yml`.
It also runs on tags that match `vX.Y.Z` exactly.

`build_pages_review` runs on other branches and in merge request pipelines
when the same inputs change (minus `.gitlab-ci.yml`, plus `test_gen_pages.py`
and `hyprtoolkit.conf.j2`). It uploads a `public/` artifact that expires after
a week and deploys nothing. GitLab treats `rules:changes` as true on pipelines
without a push diff, so the job explicitly skips tag pipelines
([GitLab rules](https://docs.gitlab.com/ci/yaml/#ruleschanges)).

### `create_release`

This job runs on every tag pipeline, whatever the tag name. It runs
[`scripts/ci/extract_release_notes.sh`](../scripts/ci/extract_release_notes.sh)
to extract that version's section from `CHANGELOG.md`, then passes the notes to
`release-cli create`. GitHub's `release.yml` only reacts to `v*` tags.

> [!IMPORTANT]
> Release notes come from `CHANGELOG.md` **at the tagged commit**. Add the
> `## [vX.Y.Z]` section before pushing the tag. Without it, the release uses the
> placeholder "No specific notes found".

## Variables and secrets

The pipeline uses GitLab's predefined variables. No custom CI/CD variable is
needed.

| Name                                    | Used by                                                        | Source                      | Manual setup |
| --------------------------------------- | -------------------------------------------------------------- | --------------------------- | ------------ |
| `CI_JOB_TOKEN`                          | `create_release` (`release-cli`)                               | Predefined for every job    | None         |
| `CI_COMMIT_TAG`                         | Test and Pages rules, `create_release` rule and name           | Predefined on tag pipelines | None         |
| `CI_COMMIT_BRANCH`, `CI_DEFAULT_BRANCH` | Test, package and Pages rules                                  | Predefined                  | None         |
| `CI_PIPELINE_SOURCE`                    | Test and package rules                                         | Predefined                  | None         |
| `CI_OPEN_MERGE_REQUESTS`                | `.unit_test_rules`, skips push pipelines of an open MR         | Predefined                  | None         |
| `CI_PROJECT_DIR`                        | pip cache path, `ANSIBLE_CONFIG` in `ansible_lint`             | Predefined                  | None         |
| `CI_PROJECT_URL`, `CI_COMMIT_SHA`       | `gen_pages.py`, file browser links                             | Predefined                  | None         |
| `CI`                                    | `build_pages.sh`, fails instead of skipping without `markdown` | Predefined                  | None         |

> [!NOTE]
> `release-cli` uses the predefined `CI_JOB_TOKEN` to authenticate with the
> Releases API. No personal access token or _Settings → CI/CD → Variables_
> entry is needed.

The included SAST, IaC Scanning and Secret Detection templates run with their
defaults and need no custom variables.
