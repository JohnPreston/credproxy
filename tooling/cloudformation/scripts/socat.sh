#!/usr/bin/env sh
apk add --no-cache socat && \
    socat TCP4-LISTEN:1338,fork,reuseaddr TCP4:credproxy:1338 &
wait
