#!/bin/bash
IP_ADDRESS=http://192.168.4.1
PARALLEL=10

function run() {
    for i in $(seq 1 ${PARALLEL}); do
        echo "running task $i"
        CURL -X PUT ${IP_ADDRESS}/devices/toggle/0,1 &
    done

    wait
}

echo "[parallel] toggle devices"
echo
time run
echo
echo "++++NETWORK TEST ✅++++"
exit 0