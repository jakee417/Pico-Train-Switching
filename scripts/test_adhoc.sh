CURL http://192.168.4.1/log
CURL -X PUT "http://192.168.4.1/devices/change/0,1/DoubleLightBeam?n=100&r=0&g=0&b=10&delay=100&beam_length=3"
CURL -X PUT http://192.168.4.1/devices/toggle/0,1