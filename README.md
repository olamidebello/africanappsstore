# African Apps Store

Self-hosted independent APK marketplace. Python 3 standard library, SQLite, responsive browser GUI, Nginx, systemd and Let's Encrypt. No Node or pip build is required. This is an initial implementation, **not a complete Google Play equivalent**.

## Deploy

Install Ansible on the control machine. Point the domain's A record at your Debian/Ubuntu server and allow TCP 80/443. Run from this checkout:

```bash
export ADMIN_EMAIL=you@example.com
read -rsp 'Initial administrator password: ' ADMIN_PASSWORD
export ADMIN_PASSWORD
```

The play targets `store`. Create this inventory:

```ini
[store]
181.214.149.146 ansible_user=root
```

Save it as `inventory.ini`, then run `ansible-playbook -i inventory.ini ansible/deploy.yml --ask-pass`. Prefer SSH keys and omit `--ask-pass` when configured. Set `-e store_domain=other.example` to use another domain. Initial admin creation is idempotent and does not reset an existing password. The password is passed in a process environment during initialization, never persisted as plaintext. Do not deploy another service on port 8080 without changing this configuration.

Ansible installs dependencies, deploys code, creates database tables and administrator, configures Nginx and HTTPS, starts the service, enables renewal and checks backend health. It preserves an existing site configuration so Certbot changes survive subsequent runs. Existing unrelated virtual hosts are preserved. DNS, registrar changes and SSH credentials are not provisioned.

## Local development

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='use-a-unique-long-password' python3 app.py
```

Open http://127.0.0.1:8080. Production must use HTTPS and `COOKIE_SECURE=1`. Run `python3 -m unittest discover -s tests -v`.

## Working flows

- Apps/Games/Books catalog, text search including developer, popularity charts and app detail pages.
- Email/password registration and sign-in; scrypt password hashes, expiring HttpOnly sessions and CSRF protection.
- Draft creation, APK upload, SHA-256 fingerprints, submission, administrator approve/reject/suspend, authenticated downloads and download library.
- Wishlist, 1–5 star reviews after download, edit/delete own review, publisher replies, reports.
- Beta/preregistration interest lists with leave controls. These do not distribute testing tracks or trigger installations.
- Persisted account preference records, support ticket creation/history and administrator report/ticket/audit visibility.
- Role and ownership checks on the server. Only administrators can publish.

## Scope and integration gaps

See FEATURES.md. Books currently use the same APK submission model; there is no ebook reader or audiobook playback. Categories are metadata, not a curated taxonomy. Theme preferences restore and apply Light, Dark, or the system appearance. Personalization, country availability and notifications are not yet controlled by preferences. Administrator support/report views are read-only. There are no seeded apps, fabricated reviews or fake sales.

APK upload checks ZIP structure and presence of AndroidManifest.xml only. It does **not** validate APK signatures, package/version correspondence, malware, permissions or compatibility. Administrators must independently verify these before publication. Downloads count transfers, not installations. This version reads APKs into memory (25 MiB maximum) and is intended for small deployments; larger stores need streamed object storage and a production application server.

Back up `/var/lib/africanappsstore` using SQLite's online backup API plus a consistent copy of immutable APK files; test restoration. Migration currently creates missing tables only. Existing table changes require versioned migrations before future schema upgrades. No production server deployment or load/security audit is implied by this repository.

## Review fixes (October 2026)

Shared app links now load the catalog and account before opening details. Protected views and download actions offer sign-in; registration explains the 12-character minimum. Saved theme and recommendation selections restore correctly, with theme applied to the interface. Request failures show useful errors and form submission prevents duplicate clicks. Layout handles long identifiers and narrow mobile screens.

Homepage and static assets support HEAD. Invalid JSON shapes, blank registration names, invalid app metadata and malformed APK containers return validation errors. Session responses omit bearer tokens and release details omit internal file paths. Existing ownership, CSRF and moderation checks remain enforced.

Validate with `python3 -m unittest discover -s tests -v` and `node --check static/app.js`. Deploy the updated checkout using the existing Ansible playbook; database and APK data remain in the persistent data directory.


## Hosted mobile catalog and store administration

Run `ansible-playbook -i localhost, -c local ansible/update-store-catalog.yml` on the hosting server after pulling this repository. This updates the **existing** `africanappsstore.service` working directory, preserving its current port, data directory and TLS proxy. Code and SQLite backups are saved under `/var/lib/olamide-store-update`. Code is restored and the service restarted if local catalog health fails. Schema changes are additive; rollback does not overwrite live user database activity.

The **Hosted apps** navigation lists the 71 source-inventory website clients with their actual client features and limitations. Download links are activated only when a deployed APK and matching checksum exist under `/var/www/olamide-mobile/<domain>/`. Missing builds display “APK build pending”. APK signature/package validation happens in the build pipeline; catalog synchronization validates its local checksum. Public HTTPS availability is checked by the mobile deployment playbook. Re-run the store updater after mobile deployment to refresh listings. Successful server builds also synchronize an existing store database automatically.

Existing store administrators can open **Administration** to grant/remove store administrator roles, show/hide hosted listings, close/reopen support tickets and inspect reports/audit history. All writes use the existing authenticated session, CSRF validation and SQLite backend. Role changes revoke the affected sessions, and administrators cannot remove their own access. This controls the store only; it does not grant administrator access to unrelated hosted platforms. Existing developer APK moderation remains available through its backend API.

ATONA provider and super-admin provisioning is in `olamidebello/Africaatona`, `deploy/auto-provision.yml`. Other hosted products still need their own backend-specific administrator integrations; no generic cross-database dashboard is represented as completed platform control.

## Pull and deploy updates (existing server)

On the hosting server, run:

```bash
sudo apt-get update && sudo apt-get install -y git ansible
sudo mkdir -p /opt/olamide-store-deployer
sudo git -C /opt/olamide-store-deployer rev-parse --git-dir >/dev/null 2>&1 || sudo git clone https://github.com/olamidebello/africanappsstore.git /opt/olamide-store-deployer
sudo git -C /opt/olamide-store-deployer pull --ff-only
sudo ansible-playbook -i localhost, -c local /opt/olamide-store-deployer/ansible/pull-and-deploy.yml
```

This playbook updates an already installed `africanappsstore.service`. It discovers the existing service working directory, data path and port, preserves its configuration and TLS, backs up SQLite and replaced code, deploys Python/static/template files, synchronizes the hosted catalog, restarts the service and checks local catalog and legal routes. Local deployment failures restore changed code (including removal of newly added files); the live database is not overwritten during rollback. Public HTTPS failures stop the playbook for investigation after deployment. Existing source checkout edits are not discarded. The existing catalog updater now also includes templates and styles. No administrator password is required for an update.
