## Homelab

Ansible + Docker Compose setup for my homelab services. It installs Docker
on target hosts and deploys:

- media stack (Jellyfin, *arr apps, qBittorrent, Jellyseerr, etc.)
- infrastructure (reverse proxy, Authentik, observability stack)
- Immich

## What gets deployed

- Media stack: Jellyfin, Sonarr, Radarr, Prowlarr, qBittorrent, Bazarr,
  Jellyseerr, plus a flare-bypasser side stack.
- Infrastructure stack: reverse proxy, Authentik, and the observability stack
  (Prometheus, Loki, Grafana, Promtail, node-exporter).
- Immich: photo management stack.

## Repository layout

- `ansible/` playbooks, inventory, and templates.
- `media/` docker-compose + Ansible tasks for the media stack.
- `infrastructure/` docker-compose + observability stack.
- `immich/` docker-compose + Ansible tasks for Immich.
- `workers/` docker-compose for worker observability.
- `run.sh` one-shot runner for the main playbooks.

## Usage (minimal)

1) Copy vars and edit:
```
cp ansible/group_vars/all.example ansible/group_vars/all.yml
```
2) Update inventory in `ansible/inventory.ini`.
3) Run the playbooks:
```
./run.sh
```

Requires Ansible and SSH access to the hosts listed in the inventory.

## Configuration notes

- `ansible/group_vars/all.yml` is required. It defines `remote_dir`,
  `remote_user`, and Authentik secrets.
- `ansible/inventory.ini` controls the `servers` and `workers` host groups.
- Some services expect local ports and disks to be available on the target hosts.
- Samba is installed directly on the `nas` host as a system service (not a container) via `ansible/samba.yml`.
- Grafana uses a hybrid model: dashboards from repo are provisioned into
  folder `Provisioned`, while custom dashboards should be created in other
  folders in UI (for example `Custom`) to avoid being overwritten by deploy.

## Samba (system-level on NAS)

1) In `ansible/group_vars/all.yml`, set:
- `samba_user`
- `samba_password`
- `samba_shares` (paths to export over SMB)
2) Run `./run.sh` to apply playbooks including Samba setup.

## Typical flow

1) Add hosts to the inventory.
2) Fill in group vars.
3) Run `./run.sh` to install Docker and deploy stacks.
