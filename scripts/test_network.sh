#!/bin/bash
IP_ADDRESS=http://192.168.4.1
echo "++++NETWORK TEST++++"
echo
echo "delete logs"
echo
curl -X "DELETE" ${IP_ADDRESS}/log
echo
echo "status"
echo
curl ${IP_ADDRESS}/
echo
echo "scan"
echo
curl ${IP_ADDRESS}/scan
echo
echo "network"
echo
curl ${IP_ADDRESS}/network
echo
echo "devices"
echo
curl ${IP_ADDRESS}/devices
echo
echo "profiles"
echo
curl ${IP_ADDRESS}/profiles
echo
echo "log"
echo
curl ${IP_ADDRESS}/log
echo
echo "++++NETWORK TEST ✅++++"
exit 0