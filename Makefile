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

# Output path for the Hyprland showcase screenshot
SCREENSHOT ?= dist/hyprland.webp
PYTHON ?= python3
ANSIBLE_PLAYBOOK ?= ansible-playbook
ANSIBLE_ARGS ?=
ANSIBLE_LINT ?= ansible-lint
COVERAGE ?= $(PYTHON) -m coverage
YAMLLINT ?= yamllint
YAMLLINT_CONFIG := .yamllint
ANSIBLE_BACKUP_ROOT ?= $(HOME)
# Vault is optional: export the local password file only when it exists. The
# environment also reaches nested Ansible commands such as ansible-inventory.
DOTFILES_VAULT_PASSWORD_FILE ?= $(CURDIR)/.vault
ANSIBLE_VAULT_ENV = $(if $(wildcard $(DOTFILES_VAULT_PASSWORD_FILE)),ANSIBLE_VAULT_PASSWORD_FILE="$(DOTFILES_VAULT_PASSWORD_FILE)")
# Vault files are encrypted, not YAML: yamllint skips them.
ANSIBLE_YAML_FILES := $(filter-out ansible/group_vars/all/vault%,$(wildcard \
	ansible/site.yml ansible/obs.yml ansible/backup.yml ansible/inventory.yml \
	ansible/tasks/*.yml ansible/group_vars/*.yml ansible/group_vars/*/*.yml \
	ansible/roles/*/defaults/*.yml ansible/roles/*/tasks/*.yml \
	ansible/roles/*/vars/*.yml))

.PHONY: help install install-obs lint lint-ansible test test-python test-shell coverage screenshot \
	ansible-backup-ls ansible-backup-rm

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Run the Ansible setup (pass options with ANSIBLE_ARGS)
	ANSIBLE_CONFIG="$(CURDIR)/ansible.cfg" $(ANSIBLE_VAULT_ENV) $(ANSIBLE_PLAYBOOK) "$(CURDIR)/ansible/site.yml" $(ANSIBLE_ARGS)

install-obs: ## Install only OBS Studio, its runtime and the demo scenes
	ANSIBLE_CONFIG="$(CURDIR)/ansible.cfg" $(ANSIBLE_VAULT_ENV) $(ANSIBLE_PLAYBOOK) "$(CURDIR)/ansible/obs.yml" $(ANSIBLE_ARGS)

lint: lint-ansible ## Lint and syntax-check the Ansible project

lint-ansible: ## Run Ansible lint, yamllint, and playbook syntax checks
	$(ANSIBLE_LINT) ansible/site.yml ansible/obs.yml
	$(YAMLLINT) -c $(YAMLLINT_CONFIG) $(ANSIBLE_YAML_FILES)
	$(ANSIBLE_PLAYBOOK) ansible/site.yml --syntax-check
	$(ANSIBLE_PLAYBOOK) ansible/obs.yml --syntax-check

test: test-python test-shell ## Run the Python and shell test suites

test-python: ## Run the Python unit tests in parallel (JOBS=N, default: CPU count)
	PYTHON="$(PYTHON)" scripts/ci/run_unit_tests.sh

coverage: ## Run the Python unit tests with coverage and enforce .coveragerc floor
	PYTHON="$(PYTHON)" scripts/ci/run_unit_tests.sh --coverage
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

ansible-backup-ls: ## List Ansible-managed backups under ANSIBLE_BACKUP_ROOT (default: HOME)
	@ANSIBLE_BACKUP_ROOT="$(ANSIBLE_BACKUP_ROOT)" $(ANSIBLE_VAULT_ENV) $(ANSIBLE_PLAYBOOK) -i localhost, ansible/backup.yml

ansible-backup-rm: ## Review and remove Ansible-managed backups under ANSIBLE_BACKUP_ROOT
	@ANSIBLE_BACKUP_ROOT="$(ANSIBLE_BACKUP_ROOT)" $(ANSIBLE_VAULT_ENV) $(ANSIBLE_PLAYBOOK) -i localhost, ansible/backup.yml -e dotfiles_backup_action=remove

screenshot: ## Render the Hyprland showcase still and animated demo next to $(SCREENSHOT)
	@DOTFILES_REPOSITORY="$(CURDIR)" OUT="$(SCREENSHOT)" \
		ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh
