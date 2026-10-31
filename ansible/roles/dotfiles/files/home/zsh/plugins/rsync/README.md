# rsync

This plugin adds aliases for frequent [rsync](https://rsync.samba.org/) commands.

To use it add `rsync` to the plugins array in you zshrc file.

```zsh
plugins=(... rsync)
```

| Alias               | Command                                          |
| ------------------- | ------------------------------------------------ |
| _rsync-copy_        | `rsync -avz --progress -h`                       |
| _rsync-move_        | `rsync -avz --progress -h --remove-source-files` |
| _rsync-update_      | `rsync -avzu --progress -h`                      |
| _rsync-synchronize_ | `rsync -avzu --delete --progress -h`             |
