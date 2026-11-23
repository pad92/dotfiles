# CI Workflows

This repository is hosted on GitHub, on GitLab (see [GitLab CI](../../.gitlab/README.md)) and on a self-hosted Gitea instance. The forges call the same scripts from
[`scripts/ci/`](../../scripts/ci). This page documents the GitHub Actions
workflows, then the parts every forge shares: the documentation site and the
shared scripts.

> [!NOTE]
> A Gitea Actions runner also scans `.github/workflows`, so these files run on
> Gitea too unless a job is scoped to GitHub. See
> [Multi-forge notes](#multi-forge-notes).

## Workflows

| File                                   | Trigger                                    | Purpose                                                     |
| -------------------------------------- | ------------------------------------------ | ----------------------------------------------------------- |
| [`deploy-pages.yml`](deploy-pages.yml) | Push or PR to `main` (documentation paths) | Build the documentation site and deploy it to GitHub Pages. |
| [`package-vim.yml`](package-vim.yml)   | Push or PR to `main` (Vim paths)           | Package the Vim configuration and plugins as `vim.tar.gz`.  |
| [`package-zsh.yml`](package-zsh.yml)   | Push or PR to `main` (Zsh paths)           | Package the Zsh configuration and plugins as `zsh.tar.gz`.  |
| [`package-nvim.yml`](package-nvim.yml) | Push or PR to `main` (Neovim paths)        | Package `.config/nvim` as `nvim.tar.gz`.                    |
| [`release.yml`](release.yml)           | Push a `v*` tag                            | Publish a release with notes from `CHANGELOG.md`.           |

### `deploy-pages.yml`

The workflow watches the same paths as the GitLab `pages` job: Markdown files,
images, the page generator and its settings, the stylesheet and the icons. A
push also runs it when the workflow file itself changes. It installs the
versions pinned in
[`scripts/ci/pages-requirements.txt`](../../scripts/ci/pages-requirements.txt)
with the runner's system Python and calls
[`scripts/ci/build_pages.sh`](../../scripts/ci/build_pages.sh), described in
[Documentation site](#documentation-site). Every run uploads the `public/`
artifact. Only runs on `main` deploy it, to the `github-pages` environment.

### `package-vim.yml`

Packages the Vim configuration as a `vim-package` artifact, with the plugins
pinned in `dotfiles_vim_pack_plugins`. `scripts/ci/fetch_vim_plugins.py` reads
that list from the role defaults and clones each plugin under
`.vim/pack/dotfiles/start/` without its `.git` directory. The steps live in
`scripts/ci/package_vim.sh`, shared with the GitLab `package_vim` job.

### `package-zsh.yml`

Packages the Zsh configuration and its pinned plugins as a `zsh.tar.gz`
artifact through `scripts/ci/package_zsh.sh`, the script of the GitLab
`package_zsh` job.

### `package-nvim.yml`

Packages `.config/nvim` as an `nvim-package` artifact when that configuration
changes.

### `release.yml`

When a `v*` tag is pushed, the workflow:

1. runs [`scripts/ci/extract_release_notes.sh`](../../scripts/ci/extract_release_notes.sh)
   to pull that version's section out of `CHANGELOG.md`;
2. creates the release with `jq` and `curl` through the REST API
   (`POST $GITHUB_API_URL/repos/$GITHUB_REPOSITORY/releases`).

GitHub and Gitea accept the same request, and both runners provide
`GITHUB_API_URL`, `GITHUB_REPOSITORY` and `secrets.GITHUB_TOKEN`, so the
workflow publishes releases on either forge.

> [!IMPORTANT]
> The release notes are read from `CHANGELOG.md` **at the tagged commit**.
> Add the `## [vX.Y.Z]` section before pushing the tag. Without it, the release
> uses the placeholder "No specific notes found".

## Documentation site

[`scripts/ci/build_pages.sh`](../../scripts/ci/build_pages.sh) renders the
repository's Markdown files into `public/` with
[`gen_pages.py`](../../scripts/ci/gen_pages.py). The GitHub `deploy-pages.yml`
workflow, the GitLab `pages` and `build_pages_review` jobs and the local
`post-commit` hook all call it. `make pages` builds the site with `CI=1`, as
the CI jobs do, and opens `public/index.html` with `xdg-open` (set `XDG_OPEN`
to use another command).

`build_pages.sh` uses POSIX `sh` and needs only the Python packages of
`pages-requirements.txt`. When the `markdown` module is missing, it fails in CI
(`CI` is set) and skips the build in the local hook. Without Pygments, code
renders without highlighting.

### Site settings

`gen_pages.py` holds only the page template. `build_pages.sh` passes it
`--config` [`scripts/ci/pages.json`](../../scripts/ci/pages.json), which sets:

| Key                | Meaning                                                                       |
| ------------------ | ----------------------------------------------------------------------------- |
| `title`            | Site name, in the navbar and as the home page title                           |
| `url`              | Public URL for canonical links, `sitemap.xml` and `robots.txt`                |
| `home`             | Markdown file published as `index.html`                                       |
| `image`            | Open Graph preview image, used when a page links it (`null` for none)         |
| `nav`              | Menu sections in order, each a `label` and a `target`                         |
| `nav_labels`       | Menu labels that replace a page's first heading or a directory name           |
| `nav_exclude`      | Pages kept out of the menu (`fnmatch`, `*` also matches `/`), still published |
| `renamed_prefixes` | Source prefixes published under another name                                  |
| `skipped_dirs`     | Directories never scanned when Git is missing                                 |
| `asset_extensions` | Linked files copied into the site instead of pointing to the forge            |

A missing, unknown or mistyped key stops the build with exit code 2.

### Pages and links

When Git is available, the generator publishes the Markdown files that
`git ls-files` lists, so a new file appears on the site only once it is
tracked. Without Git, as on the GitLab image, it walks the checkout instead,
skipping `skipped_dirs` and the submodules listed in `.gitmodules`.

Each page keeps its source path with an `.html` extension:
`dist/arch/install.md` becomes `dist/arch/install.html`. The `home` page
becomes the site index, and `.github/` is published as `github/` because
`actions/upload-pages-artifact` drops `.github` from the artifact. A page's
title is its first heading, else its path; the home page takes the site title.

`gen_pages.py` rewrites the `href` and `src` of real `<a>`, `<img>` and
`<source>` tags. Tags shown as code stay as written. The rules are:

- a link to a Markdown file goes to its page, query and anchor included;
- a link starting with `/` is relative to the repository root, as on the forges;
- a linked image is copied into `public/`, under `github/` for `.github/`;
- a link to any other file or directory goes to the forge's file browser at
  the built commit (`GITHUB_SHA` on GitHub, `CI_COMMIT_SHA` on GitLab). The
  local preview links to the file in the checkout instead.

A link to a missing file, or to a heading or anchor its page lacks, fails the
build: `gen_pages.py` lists the broken links on stderr and exits 1. The
`test-gen-pages` pre-commit hook builds the site on every Markdown change, so
broken links are caught before the commit. The hook also runs when the
stylesheet, an icon or the Hyprland palette in `hyprtoolkit.conf.j2` changes.

Only the `id` and `name` attributes of the page body count as anchors;
`id="x"` written in a paragraph does not. Heading ids follow GitHub: accents
stay (`## Présentation` gets `#présentation`), punctuation goes, each space
becomes a hyphen (`## Install & configure` gets `#install--configure`) and a
repeated heading gets `-1`, `-2`. GitLab merges runs of hyphens, so a link
written for GitLab may fail the build. Headings inside an alert are numbered
in document order with the rest of the page.

Fenced code follows CommonMark: backtick or tilde fences, closed by a fence of
the same character at least as long, so a four-backtick fence can show a
three-backtick one. A fence inside a blockquote or an alert is a code block
too. Alerts (`> [!NOTE]`) work at the top level and inside list items. Each
build also deletes what a previous build left in `public/` for renamed or
deleted pages.

### Menu

`nav` in `pages.json` lists the menu sections in order: Home (`README.md`),
Quick start (`QUICKSTART.md`), Ansible (`ansible/`), Arch Linux
(`dist/arch/`), CI (this page and the GitLab one) and Changelog
(`CHANGELOG.md`).

A target is one page, a list of pages shown as a dropdown (CI), or a
directory (Ansible, Arch Linux). A directory's dropdown mirrors its tree: its
`README.md` as Overview, its other pages, then one entry per subdirectory. A
subdirectory links its own `README.md`, or shows as a heading without one
(`roles/`), with its pages indented below. A directory with no page and a
single subdirectory is folded into one entry (`a/b`). A new README in a listed
directory therefore appears without any setting change.

An entry's label comes from `nav_labels`, else the page's first heading, else
the file name (the directory name for a README). The generator drops a target
that has no published page from the menu without an error. The
`test_every_menu_section_has_pages` test in `scripts/ci/test_gen_pages.py`
fails instead, so commit a new page such as `QUICKSTART.md` together with its
`nav` entry.

The current section is highlighted, and a submenu of more than ten entries
takes two columns on wide screens. Dropdowns open on hover with a mouse, and
on click on touch screens or in the collapsed menu.

### SEO and theme

Each `<head>` has a description from the page's first paragraph with text,
cut to 160 characters, Open Graph and Twitter card tags, a canonical URL and
the `og:image`. Every build, the local preview included, writes `sitemap.xml`
and `robots.txt`. Their URLs start with `url`, the GitLab Pages domain
`https://dotfiles.depad.fr/`, where `robots.txt` sits at the root of the
host. The GitHub copy points there too, so search engines index one site.
`SITE_URL` overrides `url`. Crawlers ignore `robots.txt` on a project site
such as `<user>.github.io/<repo>/`, so submit the sitemap in Google Search
Console or Bing Webmaster Tools.

The pages use the Gruvbox colors of the Hyprland desktop: `style.css` takes
its dark background, text and accent from `hyprtoolkit.conf.j2`, and a test
checks they match. The theme menu, last in the navbar, picks Light, Dark or
Auto (the default, which follows the desktop) and saves the choice in
`localStorage`; its button shows a sun, a moon or a half circle. A script in
`<head>` sets `data-theme` on `<html>` before the page is drawn, and Gruvbox
Light applies under `data-theme="light"`. Without JavaScript the site stays
dark. Code uses the Pygments `gruvbox-dark` and `gruvbox-light` styles.

The favicon files (`favicon.ico` at 16, 32 and 48 px, `favicon.png` at 192 px
and `apple-touch-icon.png` at 180 px) sit next to `style.css` in
`scripts/ci/` and are copied to the site root. The Pages jobs run when one of
them changes. The CDN stylesheets and scripts carry Subresource Integrity
hashes: `gen_pages.py` builds their tags from `CDN_INTEGRITY`, which also
gives the command to recompute a hash.

## Shared scripts (`scripts/ci/`)

| Script                     | Used by                                                                         |
| -------------------------- | ------------------------------------------------------------------------------- |
| `build_pages.sh`           | `deploy-pages.yml`, GitLab `pages` and `build_pages_review`, `post-commit` hook |
| `extract_release_notes.sh` | `release.yml`, GitLab `create_release`                                          |
| `build_zsh_package.py`     | `package_zsh.sh`                                                                |
| `fetch_vim_plugins.py`     | `package_vim.sh`, `build_zsh_package.py`                                        |
| `gen_pages.py`             | `build_pages.sh`, with the settings of `pages.json`                             |
| `package_vim.sh`           | `package-vim.yml`, GitLab `package_vim`                                         |
| `package_zsh.sh`           | `package-zsh.yml`, GitLab `package_zsh`                                         |
| `run_unit_tests.py`        | GitLab `unit_tests`, `make test-python` and `make coverage`                     |
| `test_gen_pages.py`        | GitLab `pages_tests`, `test-gen-pages` pre-commit hook                          |

The shell scripts use POSIX `sh`, so they run on minimal images such as
GitLab's Alpine ones.

## Variables and secrets

The runners provide the tokens these workflows use. No custom secret or
variable is needed.

| Name                           | Used by            | Source                                                  | Manual setup |
| ------------------------------ | ------------------ | ------------------------------------------------------- | ------------ |
| `GITHUB_TOKEN`                 | `release.yml`      | Injected by GitHub Actions and by the Gitea runner      | None         |
| OIDC token (`id-token: write`) | `deploy-pages.yml` | Issued by GitHub for Pages                              | None         |
| `GITHUB_SHA`                   | `gen_pages.py`     | Predefined; file browser links with `GITHUB_SERVER_URL` | None         |

> [!NOTE]
> `release.yml` declares `permissions: contents: write` so the automatic token
> can create releases. The workflow sets this permission; the repository
> settings do not need a change.

Two forge settings must be enabled once:

- GitHub Pages, for `deploy-pages.yml`: _Settings → Pages → Build and
  deployment → Source: GitHub Actions_. The job deploys to the `github-pages`
  environment.
- Gitea Actions, for the repository. The runner injects a `GITHUB_TOKEN` with
  write access to the current repository, which is enough to create releases.

## Multi-forge notes

Gitea's runner also picks up `.github/workflows`. `release.yml` uses only the
REST API, so it runs on both GitHub and Gitea. `deploy-pages.yml`,
`package-vim.yml`, `package-zsh.yml` and `package-nvim.yml` rely on GitHub
Pages or artifact upload, so their jobs are guarded with:

```yaml
if: ${{ github.server_url == 'https://github.com' }}
```

On Gitea, `github.server_url` is the instance URL and those jobs skip.
