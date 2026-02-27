# AGENTS.md

## Project in one paragraph
Homelab is an infrastructure-as-code repository that uses Ansible and Docker Compose to deploy self-hosted services across one or more hosts. It manages three main service domains: media, infrastructure (including observability), and Immich.

## Keep context minimal
When working in this repository:
- Prefer task-focused changes over broad refactors.
- Touch only files needed for the current request.
- Reuse existing Ansible and Compose patterns instead of introducing new structure.

## Detailed docs
For deeper context, use these focused docs:
- [Project Overview](docs/project-overview.md)
- [Repository Structure](docs/repository-structure.md)
- [Deployment Workflow](docs/deployment-workflow.md)
