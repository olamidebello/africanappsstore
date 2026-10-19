# Olamidepanel Android clients

71 independent Android website clients from the Olamidepanel source inventory on 2026-10-19, including AFRICA ATONA and 55 country weather editions. Live server inventory must be reconciled before describing this as every currently hosted domain. `apps.json` is the editable source of truth. Existing Africa Weather and ATONA projects remain available with their own capabilities.

These clients provide an isolated WebView, Home, Reload, Browser, back navigation, HTTPS restrictions, and external link handling. They do not implement native SIP calls, background navigation, camera/microphone, file uploads, notifications, offline use, browser engine replacement or native healthcare/justice workflows. Use Browser for unsupported website flows. Each has a separate package and Android data storage. Only the configured hostname stays in WebView; authentication on other domains opens the browser and may require using the full website in the browser.

`python mobile/fleet/tools/prepare.py` generates editable Android vector logos, website logos, 1024×500 feature graphics and download pages for every definition. Related platforms share category symbols; country weather editions share the weather identity and have individual names, domain artwork and packages. These are initial code-native brand assets, not copies of third-party brands. Review existing approved branding before replacing production logos.

## Signing and builds

The workflow intentionally requires a persistent signing key, so future builds install as updates rather than conflicting with a new ephemeral debug key. Configure these repository Actions secrets once:

- `HOSTED_APPS_KEYSTORE_BASE64`: base64 encoding of a safely backed-up keystore, alias `hostedapps`.
- `HOSTED_APPS_KEYSTORE_PASSWORD`: keystore and private-key password.

Generate the key on a trusted operator machine using `keytool -genkeypair -keystore hosted-apps.jks -alias hostedapps -keyalg RSA -keysize 3072 -validity 10000`, entering the password interactively. Never commit the key or password. Back up the key securely. This is a development distribution channel, not Google Play publication.

Push changes or run **Build all Olamidepanel Android clients** under Actions. Java 17, Gradle 8.9, Android SDK/build-tools 35 are required. Version code is the workflow run number. The workflow builds all flavors, verifies signatures and package IDs, calculates SHA-256 checksums, and publishes only when all builds pass. Downloads and a website bundle are published to `hosted-apps-development`, with immutable per-run releases for history.

## Hosting installation

Download `hosted-app-websites.tar.gz` from a successful build onto the hosting server. Add a dedicated empty include file under `/etc/nginx/mobile-apps/` for each target domain and reference it **inside that domain's active Nginx server blocks**, preserving its current proxy and TLS configuration. If HTTP redirects to HTTPS, the download routes may be included only in its HTTPS server. Do not map a generic shared server block to several applications.

Create a JSON mapping from each real domain to its dedicated include file, for example:

```json
{"africanappsstore.space":"/etc/nginx/mobile-apps/africanappsstore.space.conf"}
```

Run (Python 3.9+):

```bash
sudo python3 mobile/fleet/tools/deploy.py --bundle hosted-app-websites.tar.gz --mapping /root/mobile-app-domains.json
```

The installer validates archive paths, APK presence/checksums and dedicated include ownership, keeps one `.previous` backup, tests Nginx and rolls back failed changes. Review/remove the previous backup before the next installation. It does not discover server blocks or rewrite site source. Add a **Download Android app** link to `/download-app` in each platform's navigation. Its landing page, APK and checksum are served by that same domain under `/mobile-app/`. Verify every public HTTPS link and APK before advertising availability. This repository update alone does not deploy to the hosting server.
