BIN_DEPS=('docker' 'sudo')
STATUS=0
# === CHECKS ===
for BIN in $BIN_DEPS; do
    which $BIN 1>/dev/null 2>&1
    if [ $? -ne 0 ]; then
		(( STATUS = $STATUS + 1 ))
    fi
done

if [ $STATUS -eq 0 ]; then
	alias docker='sudo docker'
fi
