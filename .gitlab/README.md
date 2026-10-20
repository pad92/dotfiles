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

| Template                                  | Provides                             |
| ----------------------------------------- | ------------------------------------ |
| `Security/Secret-Detection.gitlab-ci.yml` | Scans commits for leaked secrets.    |
| `Security/SAST.gitlab-ci.yml`             | Static application security testing. |

## Jobs

| Job                  | Stage    | Runs when                                                                 | Purpose                                                                           |
| -------------------- | -------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `sast`               | test     | Branch pipelines                                                          | Run static security analysis with the included template's default rules.          |
| `ansible_lint`       | validate | Branch and tag pipelines                                                  | Install `make` and the pinned Ansible tools, then run `make lint-ansible`.        |
| `package_vim`        | package  | Branch and tag pipelines                                                  | Package `.vim` and `.vimrc` as `vim.tar.gz`, with submodules fetched recursively. |
| `package_nvim`       | package  | Branch and tag pipelines                                                  | Package `.config/nvim` as `nvim.tar.gz`.                                          |
| `pages`              | pages    | Default branch when documentation files change, or a `vX.Y.Z` release tag | Build and deploy the documentation site to `public/`.                             |
| `build_pages_review` | pages    | Non-default branch or merge request with matching changes                 | Build the documentation site for review without deploying it.                     |
| `create_release`     | release  | A tag is pushed (`$CI_COMMIT_TAG`)                                        | Publish a release with notes from `CHANGELOG.md`.                                 |

### `pages`

This job runs on `alpine:latest`, installs `python3` and `py3-markdown`, and
calls [`scripts/ci/build_pages.sh`](../scripts/ci/build_pages.sh). The GitHub
`deploy-pages.yml` workflow and local `post-commit` hook use the same script,
which keeps the page list in one place.

The `pages` job deploys documentation from the default branch when a documented
file changes, and from `vX.Y.Z` release tags. The `build_pages_review` job builds
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
> minimal `alpine` image without extra packages.

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
| `gen_pages.py`             | `build_pages.sh`                                                    |

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

The included **SAST** and **Secret-Detection** templates also run with their
defaults and need no variables.
