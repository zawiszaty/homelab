# Backup And Restore

## Scope
- PostgreSQL backup for:
  - `infrastructure/postgresql` (Authentik)
  - `immich/database` (Immich)
- Local dump retention on target host.
- Optional offsite sync with Restic to Google Drive via Rclone.

## Variables
Set in `ansible/group_vars/all.yml`:
- `backup_enabled`
- `backup_dir`
- `backup_retention_days`
- `backup_cron_hour`
- `backup_cron_minute`
- `backup_offsite_enabled`
- `backup_restic_repository`
- `backup_restic_password`
- `backup_rclone_config_path`
- `backup_restic_keep_daily`
- `backup_restic_keep_weekly`
- `backup_restic_keep_monthly`

## Google Drive (offsite)
1. Install and configure Rclone on target host:
   - `sudo rclone config`
   - create remote named `gdrive`
2. Ensure config exists at:
   - `/root/.config/rclone/rclone.conf`
3. Set:
   - `backup_offsite_enabled: true`
   - `backup_restic_repository: "rclone:gdrive:homelab-backups"`
   - `backup_restic_password: "<strong-password>"`
4. Run deployment:
   - `./run.sh`

## What gets executed
- Ansible installs `/usr/local/bin/homelab-db-backup`.
- Cron runs daily and appends logs to:
  - `/var/log/homelab-db-backup.log`
- Dumps are stored in:
  - `{{ backup_dir }}/postgres/infrastructure`
  - `{{ backup_dir }}/postgres/immich`

## Manual run
```bash
sudo /usr/local/bin/homelab-db-backup
```

## Restore examples
Infrastructure (Authentik):
```bash
cd /mnt/storage/infrastructure
set -a; source .env; set +a
cat /mnt/storage/backups/postgres/infrastructure/authentik-YYYYmmdd-HHMMSS.dump \
  | docker compose exec -T -e PGPASSWORD="$PG_PASS" postgresql \
  pg_restore -U "${PG_USER:-authentik}" -d "${PG_DB:-authentik}" --clean --if-exists
```

Immich:
```bash
cd /mnt/storage/immich
set -a; source .env; set +a
cat /mnt/storage/backups/postgres/immich/immich-YYYYmmdd-HHMMSS.dump \
  | docker compose exec -T -e PGPASSWORD="$DB_PASSWORD" database \
  pg_restore -U "$DB_USERNAME" -d "$DB_DATABASE_NAME" --clean --if-exists
```
