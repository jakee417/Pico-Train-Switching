IP_ADDRESS=http://192.168.4.1
echo "++++NETWORK TEST++++"
echo
echo "delete logs"
echo
CURL -X "DELETE" ${IP_ADDRESS}/log
echo
echo "status"
echo
CURL ${IP_ADDRESS}/
echo
echo "scan"
echo
CURL ${IP_ADDRESS}/scan
echo
echo "network"
echo
CURL ${IP_ADDRESS}/network
echo
echo "devices"
echo
CURL ${IP_ADDRESS}/devices
echo
echo "profiles"
echo
CURL ${IP_ADDRESS}/profiles
echo
echo "log"
echo
CURL ${IP_ADDRESS}/log
echo
echo "++++NETWORK TEST ✅++++"
exit 0