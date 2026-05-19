# Archive extraction
function extract {
  local remove_archive=false
  if [[ "$1" == "-r" || "$1" == "--remove" ]]; then
    remove_archive=true
    shift
  fi

  if [ -z "$1" ]; then
    # display usage if no parameters given
    echo "Usage: extract [-r|--remove] <path/file_name>.<zip|rar|bz2|gz|tar|tbz2|tgz|Z|7z|xz|ex|tar.bz2|tar.gz|tar.xz>"
    echo "       extract [-r|--remove] <path/file_name_1.ext> [path/file_name_2.ext] [path/file_name_3.ext]"
  else
    for n in "$@"
    do
      if [ -f "$n" ] ; then
        local success=false
        case "${n%,}" in
          *.cbt|*.tar.bz2|*.tar.gz|*.tar.xz|*.tbz2|*.tgz|*.txz|*.tar)
            tar xvf "$n" && success=true
            ;;
          *.lzma)
            unlzma ./"$n" && success=true
            ;;
          *.bz2)
            bunzip2 ./"$n" && success=true
            ;;
          *.cbr|*.rar)
            unrar x -ad ./"$n" && success=true
            ;;
          *.gz)
            gunzip ./"$n" && success=true
            ;;
          *.cbz|*.epub|*.zip)
            unzip ./"$n" && success=true
            ;;
          *.z)
            uncompress ./"$n" && success=true
            ;;
          *.7z|*.arj|*.cab|*.cb7|*.chm|*.deb|*.dmg|*.iso|*.lzh|*.msi|*.pkg|*.rpm|*.udf|*.wim|*.xar)
            7z x ./"$n" && success=true
            ;;
          *.xz)
            unxz ./"$n" && success=true
            ;;
          *.exe)
            cabextract ./"$n" && success=true
            ;;
          *.cpio)
            cpio -id < ./"$n" && success=true
            ;;
          *.cba|*.ace)
            unace x ./"$n" && success=true
            ;;
          *)
            echo "extract: '$n' - unknown archive method"
            return 1
            ;;
        esac

        if [ "$success" = true ]; then
          if [ "$remove_archive" = true ]; then
            echo "Removing source archive: $n"
            rm -f "$n"
          fi
        else
          echo "extract: extraction of '$n' failed"
          return 1
        fi
      else
        echo "'$n' - file does not exist"
        return 1
      fi
    done
  fi
}

