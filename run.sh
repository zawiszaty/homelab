#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"
VAULT_PASSWORD_FILE=""

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

cleanup() {
  if [ -n "$VAULT_PASSWORD_FILE" ] && [ -f "$VAULT_PASSWORD_FILE" ]; then
    rm -f "$VAULT_PASSWORD_FILE"
  fi
}

trap cleanup EXIT

cd "$ROOT_DIR/ansible"

cmd=(ansible-playbook -i inventory.ini deploy.yml workers.yml samba.yml)

if [ -n "${ANSIBLE_VAULT_PASSWORD:-}" ]; then
  VAULT_PASSWORD_FILE="$(mktemp)"
  chmod 600 "$VAULT_PASSWORD_FILE"
  printf '%s' "$ANSIBLE_VAULT_PASSWORD" > "$VAULT_PASSWORD_FILE"
  cmd+=(--vault-password-file "$VAULT_PASSWORD_FILE")
fi

if [ -n "${ANSIBLE_SSH_PASSWORD:-}" ]; then
  if command -v sshpass >/dev/null 2>&1; then
    export SSHPASS="$ANSIBLE_SSH_PASSWORD"
    cmd=(-e "${cmd[@]}" -e "ansible_password=$ANSIBLE_SSH_PASSWORD" -e "ansible_become_password=$ANSIBLE_SSH_PASSWORD")
    exec sshpass "${cmd[@]}"
  fi

  echo "sshpass is not installed; falling back to interactive SSH password prompts" >&2
fi

exec "${cmd[@]}" --ask-pass --ask-become-pass
