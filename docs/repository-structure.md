# Repository Structure

## Top-level directories
- `ansible/`: playbooks, inventory, group variables template, and Jinja templates.
- `media/`: media stack Compose file and stack tasks.
- `infrastructure/`: infrastructure stack Compose file and observability config.
- `immich/`: Immich Compose file and stack tasks.
- `workers/`: worker Compose file.

## Important files
- `run.sh`: one-shot runner for primary playbooks.
- `ansible/inventory.ini`: target hosts grouped by role.
- `ansible/group_vars/all.yml`: required runtime variables and secrets (created from `all.example`).

## Where to change what
- Need to modify host selection: `ansible/inventory.ini`.
- Need to update global variables/secrets: `ansible/group_vars/all.yml`.
- Need to change a stack service: corresponding stack `docker-compose.yml`.
- Need to change orchestration logic: stack `tasks.yml` and relevant playbook under `ansible/`.
