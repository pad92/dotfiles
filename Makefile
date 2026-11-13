.DEFAULT_GOAL := help

# A Git hook run from a linked worktree inherits GIT_DIR and GIT_INDEX_FILE.
# Tests that create repositories of their own would then act on this one:
# `git init` turns it bare and `git config` writes their identity into it.
# Every variable from `git rev-parse --local-env-vars` is dropped for recipes,
# so git commands find their repository from their working directory.
unexport GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG GIT_CONFIG_PARAMETERS \
	GIT_CONFIG_COUNT GIT_OBJECT_DIRECTORY GIT_DIR GIT_WORK_TREE \
	GIT_IMPLICIT_WORK_TREE GIT_GRAFT_FILE GIT_INDEX_FILE GIT_NO_REPLACE_OBJECTS \
	GIT_REPLACE_REF_BASE GIT_PREFIX GIT_SHALLOW_FILE GIT_COMMON_DIR

# ---------------------------------------------------------------------------
# Run options, set on the command line: make check TAGS=dotfiles HOST=PadsP5560
# ---------------------------------------------------------------------------
# Playbook of ansible/ to run: site (the workstation) or obs (OBS only).
PLAYBOOK ?= site
# Host of ansible/inventory.yml configured over SSH, this machine by default.
# The short hostname, as the hostname fact that tasks/target.yml checks.
HOST ?= $(shell uname -n | cut -d. -f1)
# Comma-separated tag lists passed to --tags and --skip-tags.
TAGS ?=
SKIP_TAGS ?=
# Any non-empty value asks for the sudo password (--ask-become-pass).
BECOME_PASS ?=
# Any other ansible-playbook option, for example "-e packages_upgrade_system=true".
ANSIBLE_ARGS ?=

# Tools and paths
PYTHON ?= python3
ANSIBLE_PLAYBOOK ?= ansible-playbook
ANSIBLE_GALAXY ?= ansible-galaxy
# Collections pinned in ansible/requirements.yml, installed where ansible.cfg
# looks for them first.
GALAXY_REQUIREMENTS := ansible/requirements.yml
GALAXY_COLLECTIONS_PATH := .ansible/collections
ANSIBLE_LINT ?= ansible-lint
COVERAGE ?= $(PYTHON) -m coverage
YAMLLINT ?= yamllint
YAMLLINT_CONFIG := .yamllint
# Home whose dotfile backups and broken links make clean removes. The former
# name ANSIBLE_BACKUP_ROOT still selects it. DRY_RUN=1 only lists; 0 or
# empty removes, and any other value is refused.
ANSIBLE_BACKUP_ROOT ?= $(HOME)
CLEAN_ROOT ?= $(ANSIBLE_BACKUP_ROOT)
DRY_RUN ?=
# Interpreter of ansible-playbook, which clean_obsolete.py needs to import
# Ansible: PYTHON may lack it when Ansible comes from pipx or a virtualenv.
# Evaluated only when make clean runs.
ANSIBLE_PYTHON ?= $(or $(shell $(ANSIBLE_PLAYBOOK) --version 2>/dev/null | \
	sed -n 's/^ *python version = .*(\(.*\))$$/\1/p'),$(PYTHON))
# Output path for the Hyprland showcase screenshot
SCREENSHOT ?= dist/hyprland.webp

# Playbooks that configure an inventory host.
PLAYBOOKS := site obs
# Vault files are encrypted, not YAML: yamllint skips them.
ANSIBLE_YAML_FILES := $(filter-out ansible/group_vars/all/vault%,$(wildcard \
	ansible/site.yml ansible/obs.yml ansible/inventory.yml \
	ansible/tasks/*.yml ansible/group_vars/*/*.yml ansible/host_vars/*.yml \
	ansible/roles/*/defaults/*.yml ansible/roles/*/tasks/*.yml \
	ansible/roles/*/vars/*.yml))

# Vault is optional: export the local password file only when it exists. The
# environment also reaches nested Ansible commands such as ansible-inventory.
DOTFILES_VAULT_PASSWORD_FILE ?= $(CURDIR)/.vault
ANSIBLE_VAULT_ENV = $(if $(wildcard $(DOTFILES_VAULT_PASSWORD_FILE)),ANSIBLE_VAULT_PASSWORD_FILE="$(DOTFILES_VAULT_PASSWORD_FILE)")
# ansible.cfg is named explicitly: Ansible ignores it in a world-writable
# directory, and the targets may run from elsewhere with make -C.
ANSIBLE_ENV = ANSIBLE_CONFIG="$(CURDIR)/ansible.cfg" $(ANSIBLE_VAULT_ENV)

# $(call run_playbook,<extra options>): run PLAYBOOK on HOST. The selection
# options come first, so ANSIBLE_ARGS can still add to or override them.
# PLAYBOOK must be exactly one of PLAYBOOKS: filter-out takes PLAYBOOK as text,
# so a % in it is not a wildcard. $(error) is expanded when the recipe runs, so
# an unknown PLAYBOOK only stops the targets that use it.
run_playbook = $(if $(and $(filter 1,$(words $(PLAYBOOK))),$(if $(filter-out $(PLAYBOOKS),$(PLAYBOOK)),,valid)),,$(error PLAYBOOK=$(PLAYBOOK) is not one of: $(PLAYBOOKS)))$(ANSIBLE_ENV) \
	$(ANSIBLE_PLAYBOOK) "$(CURDIR)/ansible/$(PLAYBOOK).yml" --limit "$(HOST)" \
	$(if $(TAGS),--tags "$(TAGS)") $(if $(SKIP_TAGS),--skip-tags "$(SKIP_TAGS)") \
	$(if $(BECOME_PASS),--ask-become-pass) $(1) $(ANSIBLE_ARGS)

.PHONY: help deploy check plan tags tasks install install-obs galaxy galaxy-force \
	verify lint lint-ansible test test-python test-shell coverage screenshot \
	ansible-backup-ls ansible-backup-rm clean

help: ## Show this help
	@printf 'Usage: make <target> [VARIABLE=value ...]\n\nTargets:\n'
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@printf '\nVariables of the Ansible targets:\n'
	@printf '  \033[36m%-18s\033[0m %s\n' \
		'PLAYBOOK=$(PLAYBOOK)' 'playbook of ansible/: $(PLAYBOOKS)' \
		'HOST=$(HOST)' 'inventory host, or a pattern such as all' \
		'TAGS=a,b' 'run only these tags (list them with make tags)' \
		'SKIP_TAGS=a,b' 'skip these tags' \
		'BECOME_PASS=1' 'ask for the sudo password' \
		'ANSIBLE_ARGS=...' 'any other ansible-playbook option'

## Ansible runs ---------------------------------------------------------------

deploy: ## Apply PLAYBOOK to HOST (TAGS, SKIP_TAGS, BECOME_PASS, ANSIBLE_ARGS)
	$(call run_playbook)

check: ## Preview deploy without changing HOST (--check, diffs shown)
	$(call run_playbook,--check)

# The plan stops the play at a task of the packages role. A tag selection that
# skips this task would let the next roles, such as dotfiles, change HOST.
plan: ## Print the package plan of HOST and change nothing (no TAGS or SKIP_TAGS)
	$(if $(TAGS)$(SKIP_TAGS),$(error make plan takes no TAGS or SKIP_TAGS: they could skip the stop after the package plan and change HOST))
	$(call run_playbook,-e packages_action=plan)

# Listing runs no task, so it never needs the sudo password.
tags tasks: override BECOME_PASS :=

tags: ## List the tags of PLAYBOOK
	$(call run_playbook,--list-tags)

tasks: ## List the tasks that deploy would run with the current TAGS
	$(call run_playbook,--list-tasks)

# Former names, kept for scripts and habits.
install: deploy ## Same as deploy

# install-obs has its own recipe: as a prerequisite, deploy would run only
# once, so `make install install-obs` would skip the OBS playbook.
install-obs: override PLAYBOOK := obs
install-obs: ## Same as deploy PLAYBOOK=obs: OBS, its runtime and demo scenes
	$(call run_playbook)

# $(call clean_obsolete,<extra options>)
clean_obsolete = $(ANSIBLE_ENV) "$(ANSIBLE_PYTHON)" scripts/clean_obsolete.py --root "$(CLEAN_ROOT)" $(1)

clean: ## Remove dotfile backups, migration leftovers and broken links (DRY_RUN=1 lists)
	$(if $(filter-out 0 1,$(DRY_RUN)),$(error DRY_RUN=$(DRY_RUN) is not 0 or 1))
	@$(call clean_obsolete,$(if $(filter 1,$(DRY_RUN)),--dry-run))

# Former names, kept for scripts and habits: they now cover every leftover
# that make clean removes, not only the backups.
ansible-backup-ls: ## Same as make clean DRY_RUN=1
	@$(call clean_obsolete,--dry-run)

ansible-backup-rm: ## Same as make clean
	@$(call clean_obsolete)

## Ansible collections ------------------------------------------------------

# $(call galaxy_install,<extra options>)
galaxy_install = $(ANSIBLE_GALAXY) collection install -r "$(CURDIR)/$(GALAXY_REQUIREMENTS)" \
	-p "$(CURDIR)/$(GALAXY_COLLECTIONS_PATH)" $(1)

galaxy: ## Install the pinned collections that are missing or at another version
	$(call galaxy_install)

galaxy-force: ## Reinstall the collections of requirements.yml even when installed (--force)
	$(call galaxy_install,--force)

## Repository checks ---------------------------------------------------------

verify: lint test ## Run every static check and test suite (lint, then test)

lint: lint-ansible ## Lint and syntax-check the Ansible project

lint-ansible: ## Run Ansible lint, yamllint, and playbook syntax checks
	$(ANSIBLE_LINT) $(PLAYBOOKS:%=ansible/%.yml)
	$(YAMLLINT) -c $(YAMLLINT_CONFIG) $(ANSIBLE_YAML_FILES)
	$(foreach playbook,$(PLAYBOOKS),$(ANSIBLE_PLAYBOOK) ansible/$(playbook).yml --syntax-check &&) true

test: test-python test-shell ## Run the Python and shell test suites

test-python: ## Run the Python unit tests in parallel, longest first (JOBS=N, default: CPU count)
	$(PYTHON) scripts/ci/run_unit_tests.py

coverage: ## Run the Python unit tests with coverage and enforce .coveragerc floor
	$(PYTHON) scripts/ci/run_unit_tests.py --coverage
	$(COVERAGE) report

test-shell: ## Run the shell integration tests
	sh tests/hybrid-gpu.sh
	bash tests/awww-monitor-scale.sh
	bash tests/hyprlock-playerctlock.sh
	bash tests/claude-statusline.sh
	bash tests/hypr-keybinds.sh
	bash tests/hypr-screenshot.sh
	bash tests/hypr-record.sh
	bash tests/vault-toggle.sh
	zsh tests/arch-clean-no-orphans.zsh
	zsh tests/git-pull-recursive.zsh
	zsh tests/zsh-completion.zsh

screenshot: ## Render the Hyprland showcase still and animated demo next to $(SCREENSHOT)
	@DOTFILES_REPOSITORY="$(CURDIR)" OUT="$(SCREENSHOT)" \
		ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh
