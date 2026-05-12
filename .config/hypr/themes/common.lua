-- Common theme settings (gsettings and cursor)

hl.exec_cmd("gsettings set org.gnome.desktop.interface icon-theme 'Papirus-Dark'")
hl.exec_cmd("gsettings set org.gnome.desktop.interface gtk-theme 'Materia-dark-compact'")
hl.exec_cmd("gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'")

hl.exec_cmd("hyprctl setcursor Adwaita 24")
hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita'")
hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-size 24")

hl.exec_cmd("gsettings set org.gnome.desktop.interface font-antialiasing 'rgba'")
hl.exec_cmd("gsettings set org.gnome.desktop.interface font-hinting 'full'")
hl.exec_cmd("gsettings set org.gnome.desktop.interface monospace-font-name 'SauceCodePro Nerd Font 14'")
hl.exec_cmd("gsettings set org.gnome.desktop.interface font-name 'Cantarell 10'")
hl.exec_cmd("gsettings set org.gnome.desktop.interface document-font-name 'Cantarell 10'")
