# Africa Jobs Android client

Native Android WebView shell, package `world.africandroid.africajobs`, Android 8+. Uses the approved Africa Jobs emblem. Home, reload, browser, back navigation, HTTPS-only same-host browsing and isolated login storage. No JavaScript bridge, cleartext traffic, file access, third-party cookies or certificate bypass. Uploads, blob downloads and external authentication should use Browser. Internet and a working jobs.africandroid.world deployment are required. This is a development distribution, not a Play Store release or a native rewrite.

Build using Android SDK platform 35, build-tools 35.0.0 and JDK 17. Set ANDROID_HOME, JOBS_KEYSTORE, JOBS_KEY_PASSWORD and optional JOBS_KEY_ALIAS, then run `bash mobile/africajobs/tools/build.sh`. Back up the signing key securely. Keep the same key for future updates, and increment manifest versionCode for each release. Never commit a key or password.
