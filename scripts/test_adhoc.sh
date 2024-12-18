#!/bin/bash
# curl -X PUT "http://192.168.4.1/devices/change/0,1/DoubleLightBeam?n=6&r=20&g=20&b=20&delay=30&beam_length=3&reverse_at_end=1"
curl -X PUT "http://192.168.4.1/devices/change/2,3/DoubleLightBeam?n=16&r=20&g=20&b=20&delay=10&beam_length=3"
# curl -X PUT http://192.168.4.1/devices/toggle/0,1
curl -X PUT http://192.168.4.1/devices/toggle/2,3
curl http://192.168.4.1/devices
curl http://192.168.4.1/log