#!/usr/bin/env sh
apk add --no-cache iproute2 socat
ip addr add 169.254.170.2 dev lo
socat TCP4-LISTEN:1338,fork,reuseaddr TCP4:credproxy:1338 &
socat TCP4-LISTEN:80,fork,reuseaddr,bind=169.254.170.2 TCP4:credproxy:1338 &
wait
