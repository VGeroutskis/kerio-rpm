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
        # Check if the first argument after systemctl is resolvectl
        if [[ "$1" == "resolvectl" ]]; then
            shift
            /usr/bin/resolvectl "$@"
        else
            /usr/bin/systemctl "$@"
        fi
        ;;
    *)
        echo "Unknown command"
        exit 1
        ;;
esac
