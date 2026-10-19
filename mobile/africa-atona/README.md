# AFRICA ATONA Android beta

Foreground Android WebView client for https://africaatona.africandroid.world/.

Source platform and deployment: https://github.com/olamidebello/Africaatona

Build: Java 17, Android SDK 35, Gradle 8.9; `gradle -p mobile/africa-atona :app:assembleDebug` from repository root.

Workflow `.github/workflows/africa-atona-android.yml` publishes versioned development prereleases and SHA-256 checksums. This is a debug-signed development client, not a Play Store release. Hosting must be deployed separately. No offline or background navigation.
