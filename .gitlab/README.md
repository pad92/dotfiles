# GitLab CI Pipeline

Documentation for [`.gitlab-ci.yml`](../.gitlab-ci.yml) at the repo root. This
repo is also hosted on **GitHub** ([`.github/workflows/`](../.github/workflows))
and a self-hosted **Gitea** instance; the forge-specific config stays thin and
the real work lives in reusable scripts under [`.ci_bin/`](../.ci_bin).

## 🪜 Stages

```
test → package → pages → release
```

## 📋 Included templates

| Template                                  | Provides                             |
| ----------------------------------------- | ------------------------------------ |
| `Security/Secret-Detection.gitlab-ci.yml` | Scans commits for leaked secrets.    |
| `Security/SAST.gitlab-ci.yml`             | Static application security testing. |

## 🧰 Jobs

| Job              | Stage   | Runs when                          | Purpose                                                                           |
| ---------------- | ------- | ---------------------------------- | --------------------------------------------------------------------------------- |
| `sast`           | test    | every commit                       | Static security analysis (from the SAST template).                                |
| `package_vim`    | package | always                             | Tar `.vim`/`.vimrc` into a `vim.tar.gz` artifact (submodules pulled recursively). |
| `pages`          | pages   | default branch + doc files change  | Build and deploy the static docs site into `public/`.                             |
| `build_pages_review` | pages | non-default branch + doc files change | Build the static docs site for validation without deploying it.                 |
| `create_release` | release | a tag is pushed (`$CI_COMMIT_TAG`) | Publish a release with notes from `CHANGELOG.md`.                                 |

### 📄 `pages`

Runs on `alpine:latest`, installs `python3`/`py3-markdown`, then calls
[`.ci_bin/build_pages.sh`](../.ci_bin/build_pages.sh) — the same script used by
the GitHub `deploy-pages.yml` workflow and the local `post-commit` hook, so the
page list stays in one place.

The pipeline uses two jobs so documentation can be built everywhere but only
**deployed** from the default branch:

1. `pages` runs on the default branch and is the official Pages deployment.
2. `build_pages_review` runs on other branches / merge requests and uploads a
   short-lived `public/` artifact for validation only.

> [!NOTE]
> `build_pages.sh` is POSIX `sh` and git-optional, so it runs on the minimal
> `alpine` image without extra packages.

### 🏷️ `create_release`

On a `v*` tag it runs
[`.ci_bin/extract_release_notes.sh`](../.ci_bin/extract_release_notes.sh) to pull
that version's section out of `CHANGELOG.md`, then hands the notes to
`release-cli create`.

> [!IMPORTANT]
> Release notes are read from `CHANGELOG.md` **at the tagged commit**. Make sure
> the `## [vX.Y.Z]` section exists before pushing the tag, otherwise the release
> gets a "No specific notes found" placeholder.

## 🔧 Shared scripts (`.ci_bin/`)

| Script                     | Used by                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| `build_pages.sh`           | GitLab `pages`, GitHub `deploy-pages.yml`, local `post-commit` hook |
| `extract_release_notes.sh` | GitLab `create_release`, GitHub `release.yml`                       |
| `gen_pages.py`             | `build_pages.sh`                                                    |

Both shell scripts are **POSIX `sh`** (no Bash-isms) so they run on minimal CI
images such as this `alpine` job.

## 🔐 Variables & secrets

No custom CI/CD variables need to be configured — the pipeline relies only on
GitLab's predefined variables.

| Name                                    | Used by                              | Source                      | Manual setup |
| --------------------------------------- | ------------------------------------ | --------------------------- | ------------ |
| `CI_JOB_TOKEN`                          | `create_release` (`release-cli`)     | Predefined for every job    | None         |
| `CI_COMMIT_TAG`                         | `create_release` rule + release name | Predefined on tag pipelines | None         |
| `CI_COMMIT_BRANCH`, `CI_DEFAULT_BRANCH` | `pages` rules                        | Predefined                  | None         |

> [!NOTE]
> `release-cli` authenticates to the Releases API with the predefined
> `CI_JOB_TOKEN`, so no personal access token or _Settings → CI/CD → Variables_
> entry is required.

The included **SAST** and **Secret-Detection** templates also run with their
defaults and need no variables.
