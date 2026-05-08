#!/bin/bash
COMMAND=$1
shift

case "$COMMAND" in
    podman)
        /usr/bin/podman "$@"
        ;;
    ip)
        /usr/sbin/ip "$@"
        ;;
    systemctl)
        /usr/bin/systemctl "$@"
        ;;
    *)
        echo "Unknown command"
        exit 1
        ;;
esac
