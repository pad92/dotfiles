.DEFAULT_GOAL := help

# Output path for the Hyprland showcase screenshot
SCREENSHOT ?= dist/hyprland.webp
PYTHON ?= python3
ANSIBLE_PLAYBOOK ?= ansible-playbook
ANSIBLE_LINT ?= ansible-lint
YAMLLINT ?= yamllint
YAMLLINT_CONFIG := .yamllint
ANSIBLE_BACKUP_ROOT ?= $(HOME)
ANSIBLE_YAML_FILES := $(wildcard ansible/site.yml ansible/backup.yml ansible/inventory.yml \
	ansible/host_vars/*.yml ansible/group_vars/*.yml \
	ansible/roles/*/defaults/*.yml ansible/roles/*/tasks/*.yml \
	ansible/roles/*/vars/*.yml)

.PHONY: help lint lint-ansible test test-python test-shell screenshot \
	ansible-backup-ls ansible-backup-rm

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

lint: lint-ansible ## Lint and syntax-check the Ansible project

lint-ansible: ## Run Ansible lint, yamllint, and playbook syntax checks
	$(ANSIBLE_LINT) ansible/site.yml
	$(YAMLLINT) -c $(YAMLLINT_CONFIG) $(ANSIBLE_YAML_FILES)
	$(ANSIBLE_PLAYBOOK) ansible/site.yml --syntax-check

test: test-python test-shell ## Run the Python and shell test suites

test-python: ## Run the Python unit tests
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

test-shell: ## Run the shell integration tests
	bash tests/awww-monitor-scale.sh
	bash tests/hyprlock-playerctlock.sh
	zsh tests/arch-clean-no-orphans.zsh
	zsh tests/git-pull-recursive.zsh

ansible-backup-ls: ## List Ansible-managed backups under ANSIBLE_BACKUP_ROOT (default: HOME)
	@ANSIBLE_BACKUP_ROOT="$(ANSIBLE_BACKUP_ROOT)" $(ANSIBLE_PLAYBOOK) -i localhost, ansible/backup.yml

ansible-backup-rm: ## Review and remove Ansible-managed backups under ANSIBLE_BACKUP_ROOT
	@ANSIBLE_BACKUP_ROOT="$(ANSIBLE_BACKUP_ROOT)" $(ANSIBLE_PLAYBOOK) -i localhost, ansible/backup.yml -e dotfiles_backup_action=remove

screenshot: ## Render an isolated Hyprland showcase to $(SCREENSHOT)
	@DOTFILES_REPOSITORY="$(CURDIR)" OUT="$(SCREENSHOT)" \
		ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh
