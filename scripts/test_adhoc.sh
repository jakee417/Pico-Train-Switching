#!/bin/bash
curl -X PUT "http://192.168.4.1/devices/change/0,1/DoubleLightBeam?n=16&r=10&g=10&b=10&delay=10&beam_length=3"
curl -X PUT "http://192.168.4.1/devices/change/2,3/DoubleLightBeam?n=16&r=10&g=10&b=10&delay=10&beam_length=3"
curl -X PUT http://192.168.4.1/devices/toggle/0,1 &
curl -X PUT http://192.168.4.1/devices/toggle/2,3 &