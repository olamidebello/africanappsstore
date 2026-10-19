# Africa Weather Android

Android WebView app for https://africaweather.africandroid.world/ and the 55 country editions in `app/src/main/assets/countries.json`. The native country selector remembers the chosen edition between launches. Browser preferences are separate from app preferences. HTTPS is required; file access and mixed content are disabled. External HTTPS links and APK downloads open the browser.

GitHub Actions builds this app with Java 17, Gradle 8.9 and Android SDK 35, checks the APK signature and package identifier, and publishes `AfricaWeather.apk`, its SHA-256 file and metadata to this repository’s Releases. This is a debug-signed development app. Updates may require reinstalling. No Play Store publication is implied.

Build locally with Android SDK 35 and Gradle 8.9:

```bash
cd mobile/africaweather
gradle --no-daemon assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`. The website download button resolves an actual release asset, and stays unavailable when none exists. Publishing a GitHub release does not register an app in a running store SQLite database or deploy website changes to the hosting server.
