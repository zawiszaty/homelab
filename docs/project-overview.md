# Project Overview

## Purpose
This repository automates deployment of a personal homelab using:
- Ansible for host preparation and orchestration.
- Docker Compose for service lifecycle.

## Main stacks
- `media/`: Jellyfin and companion apps (*arr ecosystem, qBittorrent, Jellyseerr, etc.).
- `infrastructure/`: reverse proxy, Authentik, and observability components.
- `immich/`: Immich photo stack.
- `workers/`: worker-side observability Compose setup.

## Core deployment model
- Host-level orchestration is done from `ansible/` playbooks.
- Service definitions live in stack-specific `docker-compose.yml` files.
- Variables and inventory drive host targeting and runtime configuration.
