# Lsmod all with params
function lsmodp {
    cat /proc/modules | cut -f 1 -d " " | while read module; do
        echo "Module: $module"
        if [ -d "/sys/module/$module/parameters" ]; then
            ls /sys/module/$module/parameters/ | while read parameter; do
            echo -n "Parameter: $parameter --> "
            sudo cat /sys/module/$module/parameters/$parameter
        done
        fi
        echo
    done
}
