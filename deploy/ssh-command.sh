#!/usr/bin/env bash
set -euo pipefail
command=${SSH_ORIGINAL_COMMAND:-}
if [[ $command == status ]]; then
    exec sudo -n /usr/local/sbin/banasdev-deploy status
elif [[ $command =~ ^deploy\ ([a-f0-9]{40})\ ([a-f0-9]{64})$ ]]; then
    exec sudo -n /usr/local/sbin/banasdev-deploy "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
fi
echo 'This key only permits banas.dev status and deployment.' >&2
exit 2
