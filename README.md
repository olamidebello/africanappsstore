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

## Africa Jobs Android client and store download

`mobile/africajobs` contains the Africa Jobs HTTPS Android website client, approved logo, and a dependency-light SDK build script. `catalog/africajobs.json` records its verified build metadata. `static/africajobs` contains the development APK, checksum and logo after a successful build. This is an Android website client, not a native implementation of every marketplace feature.

To publish the checked-in APK and listing on the existing store server:

```sh
cd /opt/africanappsstore-deployer
git pull --ff-only origin main
ansible-playbook -i localhost, -c local ansible/deploy-africajobs-mobile.yml
```

The playbook updates the current service using its existing backup mechanism, checks the APK checksum, adds the Africa Jobs Hosted apps listing, and verifies HTTPS. Website link: `https://africanappsstore.space/#Hosted%20apps`. APK route: `/downloads/africa-jobs.apk`. The site is not changed until the playbook runs on the hosting server. The current database default is `/var/lib/africanappsstore/store.sqlite3`; deployments using another database must pass the matching path to the listing installer.

The initial APK is a development build. Its signing identity must be preserved for compatible updates; rebuilding with a new key requires uninstalling the older app. Use a persistent private production keystore for a production release. No production signing key is committed.

## Africa Bulk Hub Android release

`catalog/afribulkhub.json` and `static/afribulkhub/` contain the signed Africa Bulk Hub 1.0.0 website-client APK, checksum, generated logo/banner and release metadata. Package `com.afribulkhub.mobile`, Android 8+. Slogan: **Connecting Africa. Trading Beyond.** No private signing key is in this repository.

On the existing hosting server, pull this source and run `ansible-playbook -i localhost, -c local ansible/deploy-afribulkhub-mobile.yml`. It uses the existing store backup/update mechanism, installs a checksum-verified Hosted apps listing while preserving its visibility setting, and verifies the public download and catalog. Source publication alone does not deploy the live website. The app needs internet and the operational afribulkhub.com site; no offline trading, native push or live payment processing is included. Blob-based downloads may need the native Browser control. Android device acceptance testing remains outstanding.

Public paths after deployment: `/downloads/africa-bulk-hub.apk`, `/downloads/africa-bulk-hub.apk.sha256`, `/downloads/africa-bulk-hub-logo.png`, `/downloads/africa-bulk-hub-banner.png`, and `/downloads/africa-bulk-hub-release.json`. The listing appears under **Hosted apps**. Two integration tests cover public APK/logo HEAD/download behavior and preservation of other catalog records and visibility.


## AfricanBrowser Chromium listing

After deploying a verified browser build on the hosting server, run:

```sh
python3 tools/install_africanbrowser.py --website-root /var/www/olamide-auto/africanbrowser.com/public_html
```

The installer reads the browser deployment manifest, verifies the local ARM64 APK
checksum and structure, checks the public HTTPS download size, backs up the
existing store database, and replaces only the africanbrowser.com listing.
It preserves visibility and links to the immutable browser-hosted APK. The
service STORE_DATA setting supplies the database path; --database overrides it.
Subsequent fleet sync preserves this Chromium listing instead of replacing it
with the generic website client. This listing describes a development APK.
The browser repository's ansible/olamidepanel.yml chains rebuild, website
deployment and this installer. No other app listings are deleted.

## Africa Media Hub listing
The Hosted apps catalog includes Africa Media Hub, its app icon, slogan, TV and connection features, website, and device-specific install page. No unverified APK URL is advertised. `tools/update_store.py` upserts this listing during deployment and preserves existing administrator visibility settings and unrelated apps. Publish with `ansible/pull-and-deploy.yml` using the existing service, port, domain and TLS configuration.

## AIMS Android signed release

`static/aims/aims.apk` contains AIMS 1.0.1, package `world.africandroid.aims`, Android 8+. The signature was verified with Android SDK apksigner; SHA-256 and signing-certificate fingerprints are in `catalog/aims.json`. Private keys are not committed. AIMS is an HTTPS website client with document picker, Home/Reload/Back and browser controls. It requires internet and the operational AIMS site; offline identity, native biometrics and push notifications are not included. Physical Android device acceptance testing remains outstanding.

`tools/update_store.py` installs the AIMS listing as part of routine updates. The installer verifies the local APK checksum, preserves hidden/visible state and other listings; fleet sync does not downgrade it. `/downloads/aims.apk`, `/downloads/aims.apk.sha256` and `/downloads/aims-logo.png` are public GET/HEAD routes after deployment.

Run on the hosting server: `ansible-playbook -i localhost, -c local ansible/deploy-aims-mobile.yml`. This pulls AIMS and store source, deploys the AIMS install page/embedded APK, updates the existing store with its backup mechanism, and checks public HTTPS install/download/catalog endpoints. Existing AIMS accounts and store users stay intact. Repository publication alone does not update the live website.

## Postmaster Android listing
Postmaster 1.0.0 (com.justisolve.postmaster, Android 8+) is included as a signed development APK under static/postmaster, with checksum, public signing fingerprint and logo. Deploy with ansible/deploy-postmaster-mobile.yml. The store updater preserves existing visibility and unrelated apps. Public routes: /downloads/postmaster.apk, /downloads/postmaster.apk.sha256, /downloads/postmaster-logo.png and /downloads/postmaster-release.json. Postmaster's install page: https://postmaster.justisolve.com/install.

Internet and valid website HTTPS are required. File selection/upload is supported; external checkout opens the browser. No offline mail or native push; device acceptance testing is pending. No private signing material is committed.


## Kakakin publication across two hosts

Kakakin runs on 154.16.170.86. Public africanappsstore.space currently points to 181.214.149.146. Updating an africanappsstore.service copy on the Kakakin machine does not update that public store. The Kakakin publisher now checks all public DNS addresses against the target host before it changes store files. It does not move DNS or replace other domains. For verified NAT deployments, Ansible may be given store_public_addresses explicitly.

On the public store host (181.214.149.146), run:

```sh
curl -fL https://raw.githubusercontent.com/olamidebello/africanappsstore/main/scripts/publish-kakakin.sh -o /root/publish-kakakin.sh
bash /root/publish-kakakin.sh
```

The bootstrap preserves source edits, updates the existing store with database/code backups, checks the locally served APK checksum and catalog entry, then verifies public HTTPS downloads and catalog. No Kakakin application rebuild or administrator password is needed. From a controller already authorized for SSH to the store, use `ansible-playbook -i '181.214.149.146,' -u root ansible/publish-mobile.yml` in the Kakakin checkout instead. SSH authorization must already exist; the script does not copy credentials or change DNS to work around missing access.

## Publish Media phone-to-TV Android APK

On the server hosting African Apps Store:

```bash
ansible-pull -U https://github.com/olamidebello/africanappsstore.git -C main \
  -d /opt/africa-media-store-bootstrap -i localhost, -c local \
  ansible/deploy-media-phone-tv-apk.yml
```

This downloads the pinned successful Media Actions artifact through nightly.link, verifies the archive SHA-256 and APK SHA-256/size, backs up the existing store code/database, publishes the APK and updates only the Media catalog record. It preserves administrator visibility and rolls back the targeted store changes if verification fails. If the Media service account also exists on this server, the same APK is copied to `/var/lib/africa-media/downloads`. The source artifact expires January 27, 2027; once deployed the store keeps its own APK copy. A future release needs a new pinned manifest. No GitHub token is needed for the public download relay. The release is a development-signed universal APK, not a Play Store release; existing APK signing conflicts may require separate user action, and no app is automatically uninstalled.

Download after successful deployment: `https://africanappsstore.space/downloads/africa-media-android-debug.apk`. Server deployment does not install it on phones or TVs. The phone must install the new APK, then pair/approve the TV through Install on device. Android package signature and package ID were verified before preparing this release; physical TV testing remains pending.
