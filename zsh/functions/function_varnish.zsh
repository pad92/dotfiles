which varnishadm 1>/dev/null 2>&1
if (( $? == 0 )); then
    if [ -x $(which varnishadm) ]; then
        varnish_reload () {
            VARNISHADM=$(which varnishadm)
            DATE=$(date +%Y%m%d_%H%M%S)
            $VARNISHADM "vcl.load $DATE /usr/local/etc/varnish/production.vcl"
            if [ $? -eq 0 ]
            then
                $VARNISHADM "vcl.use $DATE"
                echo "VCL used : $DATE"
            else
                echo "Fail to compile VCL"
            fi
        }
    fi
fi
