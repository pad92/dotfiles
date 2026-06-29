.DEFAULT_GOAL := help

# Output path for the Hyprland showcase screenshot
SCREENSHOT ?= hyprland-showcase.png

.PHONY: help screenshot

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

screenshot: ## Render an isolated Hyprland showcase to $(SCREENSHOT)
	@OUT="$(SCREENSHOT)" bin/hypr-screenshot.sh
