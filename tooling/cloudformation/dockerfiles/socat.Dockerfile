FROM alpine:latest

RUN apk add --no-cache iproute2 socat

COPY scripts/socat.sh /usr/local/bin/socat.sh
RUN chmod +x /usr/local/bin/socat.sh

ENTRYPOINT ["/bin/sh", "/usr/local/bin/socat.sh"]
