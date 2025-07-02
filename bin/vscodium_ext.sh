#!/bin/sh

# List of extensions to install (as a space-separated string for sh compatibility)
extensions="
aaron-bond.better-comments
alefragnani.Bookmarks
alefragnani.project-manager
be5invis.vscode-icontheme-nomo-dark
budparr.language-hugo-vscode
chrmarti.regex
coolbear.systemd-unit-file
docker.docker
eamodio.gitlens
earshinov.sort-lines-by-selection
EditorConfig.EditorConfig
esbenp.prettier-vscode
Gruntfuggly.todo-tree
hashicorp.terraform
jaspernorth.vscode-pigments
mkhl.shfmt
ms-azuretools.vscode-docker
ms-python.debugpy
ms-python.python
ms-python.vscode-pylance
ms-vscode-remote.remote-ssh
ms-vscode-remote.remote-ssh-edit
ms-vscode-remote.remote-wsl
ms-vscode.powershell
ms-vscode.remote-explorer
nonoroazoro.syncing
oderwat.indent-rainbow
redhat.ansible
redhat.vscode-yaml
saoudrizwan.claude-dev
yzhang.markdown-all-in-one
zokugun.cron-tasks
"

# Function to install extensions
install_extensions() {
    editor_cmd=$1
    echo "-----------------------------------------------------"
    echo "Installing extensions for $editor_cmd..."
    echo "-----------------------------------------------------"
    for extension in $extensions; do
        echo "Installing: $extension"
        "$editor_cmd" --install-extension "$extension"
    done
    echo "-----------------------------------------------------"
    echo "Installation for $editor_cmd finished."
    echo "-----------------------------------------------------"
}

# Check for and install for Visual Studio Code
if command -v code > /dev/null 2>&1; then
    install_extensions code
else
    echo "'code' command not found. Skipping installation for VS Code."
fi

# Check for and install for VSCodium
if command -v codium > /dev/null 2>&1; then
    install_extensions codium
else
    echo "'codium' command not found. Skipping installation for VSCodium."
fi

echo "Script finished."
