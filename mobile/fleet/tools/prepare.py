#!/usr/bin/env python3
"""Generate native vector resources and web branding from the domain manifest."""
import json, html, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
apps=json.loads((ROOT/'apps.json').read_text())
# Editable native vector symbols; country editions use the same weather identity.
paths={
'Weather':'M48,16 A16,16 0,1 1,47.9 16 M12,62 C12,48 28,44 38,50 C44,32 72,34 78,52 C96,52 96,78 78,78 L26,78 C10,78 6,68 12,62',
'Justice':'M48,16 L48,78 M24,78 L72,78 M16,34 L80,34 M24,34 L12,58 L36,58 Z M72,34 L60,58 L84,58 Z',
'Medical':'M37,16 L59,16 L59,37 L80,37 L80,59 L59,59 L59,80 L37,80 L37,59 L16,59 L16,37 L37,37 Z',
'Navigation':'M48,12 C12,12 12,52 48,84 C84,52 84,12 48,12 M48,27 A12,12 0,1 1,47.9 27',
'Hosting':'M18,18 L78,18 L78,34 L18,34 Z M18,40 L78,40 L78,56 L18,56 Z M18,62 L78,62 L78,78 L18,78 Z',
'Shopping':'M20,32 L76,32 L82,80 L14,80 Z M32,34 L32,22 C32,4 64,4 64,22 L64,34',
'Dating':'M48,80 C-8,44 10,4 36,22 L48,34 L60,22 C86,4 104,44 48,80 Z',
'Creative':'M18,76 L18,36 L38,36 L38,76 Z M48,76 L48,18 L68,18 L68,76 Z M78,76 L78,48 L88,48 L88,76 Z',
'Communications website':'M22,12 L38,32 L28,44 C36,58 44,64 56,68 L68,56 L86,72 C74,104 8,68 10,26 Z',
'Browser website':'M48,12 A36,36 0,1 1,47.9 12 M12,48 L84,48 M48,12 C24,30 24,66 48,84 C72,66 72,30 48,12',
'Technology':'M24,24 L72,24 L72,72 L24,72 Z M36,36 L60,36 L60,60 L36,60 Z M36,12 L36,24 M60,12 L60,24 M36,72 L36,84 M60,72 L60,84',
'Business':'M18,30 L78,30 L78,78 L18,78 Z M34,30 L34,18 L62,18 L62,30 M18,48 L78,48 M44,44 L52,44 L52,56 L44,56 Z'
}
for app in apps:
    path=paths[app['category']]
    d=ROOT/'app/src'/app['id']/'res/drawable';d.mkdir(parents=True,exist_ok=True)
    vector=f'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108"><path android:fillColor="{app["color"]}" android:pathData="M0,0h108v108h-108z"/><group android:translateX="6" android:translateY="6"><path android:fillColor="#00000000" android:strokeColor="#FFFFFF" android:strokeWidth="4" android:strokeLineJoin="round" android:pathData="{path}"/></group></vector>'
    (d/'app_icon.xml').write_text(vector)
    web=ROOT/'web'/app['domain']; web.mkdir(parents=True,exist_ok=True)
    icon=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108"><rect width="108" height="108" rx="22" fill="{app["color"]}"/><path transform="translate(6 6)" d="{path}" fill="none" stroke="white" stroke-width="4" stroke-linejoin="round"/></svg>'
    (web/'logo.svg').write_text(icon)
    name=html.escape(app['name'])
    banner=f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="500" viewBox="0 0 1024 500"><rect width="1024" height="500" fill="{app["color"]}"/><path transform="translate(420 35) scale(2)" d="{path}" fill="none" stroke="white" stroke-width="4"/><text x="512" y="310" text-anchor="middle" fill="white" font-family="sans-serif" font-size="34">{name}</text><text x="512" y="365" text-anchor="middle" fill="white" font-family="sans-serif" font-size="22">{app["domain"]}</text><text x="512" y="420" text-anchor="middle" fill="white" font-family="sans-serif" font-size="20">Android website client • Development edition</text></svg>'
    (web/'feature.svg').write_text(banner)
    release='https://github.com/olamidebello/africanappsstore/releases/download/hosted-apps-development/'+app['slug']+'.apk'
    (web/'index.html').write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} Android download</title><style>body{{font:18px system-ui;background:#101827;color:white;max-width:720px;margin:60px auto;padding:24px}}a{{color:#9de2ff}}.button{{display:inline-block;padding:16px;background:{app['color']};color:white;border-radius:12px}}</style><img src="logo.svg" width="108" height="108" alt=""><h1>{name} for Android</h1><p>Open {app['domain']} in a dedicated Android website client.</p><p>Android 8 or newer. Internet required. Development APK; Android may ask you to allow installation from your browser.</p><a class="button" href="{app['slug']}.apk">Download Android APK</a><p><a href="{app['slug']}.apk.sha256">SHA-256 checksum</a> · <a href="{app['url']}">Website</a></p><p>This client uses the website’s available features. Native calls, file uploads, camera, microphone, background navigation and offline features are not implemented. For these, use the Browser button.</p><p>Website data is stored in Android WebView. No additional analytics SDK is included. Review the website privacy policy before signing in.</p></html>''')
campaign=ROOT/'artwork/africa-apps-store-campaign.png'
if campaign.exists():
    shutil.copyfile(campaign,ROOT/'web/africanappsstore.space/campaign.png')
print(f'Generated branding and download pages for {len(apps)} domains')
