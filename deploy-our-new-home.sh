#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULT_PASSWORD_FILE=""

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

cleanup() {
  if [ -n "$VAULT_PASSWORD_FILE" ] && [ -f "$VAULT_PASSWORD_FILE" ]; then
    rm -f "$VAULT_PASSWORD_FILE"
  fi
}
trap cleanup EXIT

cmd=(ansible-playbook -i "$ROOT_DIR/ansible/inventory.ini" "$ROOT_DIR/ansible/our-new-home.yml")

if [ -n "${ANSIBLE_VAULT_PASSWORD:-}" ]; then
  VAULT_PASSWORD_FILE="$(mktemp)"
  chmod 600 "$VAULT_PASSWORD_FILE"
  printf '%s' "$ANSIBLE_VAULT_PASSWORD" > "$VAULT_PASSWORD_FILE"
  cmd+=(--vault-password-file "$VAULT_PASSWORD_FILE")
fi

cmd+=("$@")

if [ -n "${ANSIBLE_SSH_PASSWORD:-}" ] && command -v sshpass >/dev/null 2>&1; then
  export SSHPASS="$ANSIBLE_SSH_PASSWORD"
  cmd+=(-e "ansible_password=$ANSIBLE_SSH_PASSWORD")
  cmd+=(-e "ansible_become_password=$ANSIBLE_SSH_PASSWORD")
  "${cmd[@]}"
  exit
fi

"${cmd[@]}" --ask-pass --ask-become-pass
