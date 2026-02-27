# Deployment Workflow

## Prerequisites
- Ansible installed on the control machine.
- SSH connectivity to all target hosts.

## Minimal deployment steps
1. Create variables file:
   - `cp ansible/group_vars/all.example ansible/group_vars/all.yml`
2. Fill required values in `ansible/group_vars/all.yml`.
3. Update host groups in `ansible/inventory.ini`.
4. Run deployment:
   - `./run.sh`

## Operational notes
- The process installs Docker on targets and deploys Compose stacks.
- Existing remote ports, storage paths, and network constraints can affect successful rollout.
- Validate host readiness before broad changes to avoid multi-stack failures.
