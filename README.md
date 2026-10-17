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
