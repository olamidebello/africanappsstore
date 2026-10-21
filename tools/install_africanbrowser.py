#!/usr/bin/env python3
"""Register a deployed, checksum-verified Chromium browser APK in the store."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import time
import urllib.request
import zipfile


def install(database, website_root, check_public=True):
    database, root = Path(database), Path(website_root).resolve()
    if not database.is_file():
        raise ValueError('Existing store database not found')
    info = json.loads((root / 'deployment.json').read_text())
    relative = info['apk']
    if not re.fullmatch(r'downloads/android-[0-9]+/AfricanBrowser\.apk', relative):
        raise ValueError('Unexpected browser download path')
    apk = (root / relative).resolve()
    if not apk.is_relative_to(root):
        raise ValueError('Download escapes website root')
    with apk.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != info['sha256']:
        raise ValueError('APK checksum mismatch')
    with zipfile.ZipFile(apk) as archive:
        names = set(archive.namelist())
        if not {'AndroidManifest.xml', 'classes.dex'}.issubset(names) or not any(
                n.startswith('lib/arm64-v8a/') and n.endswith('.so') for n in names):
            raise ValueError('Expected an ARM64 browser APK')
    url = 'https://africanbrowser.com/' + relative
    if check_public:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=30) as response:
            if response.status != 200 or int(response.headers.get('Content-Length', -1)) != apk.stat().st_size:
                raise ValueError('Public browser download does not match the deployed file size')
    metadata = dict(
        domain='africanbrowser.com', name='AfricanBrowser', category='Communication',
        package='org.africanbrowser.browser', website='https://africanbrowser.com/',
        description='AfricanBrowser Android ARM64 Chromium browser with Pan-African branding.',
        features=['Chromium browser engine', 'Tabs, bookmarks, history and downloads',
                  'Private browsing and site permissions', 'AfricanBrowser artwork and default homepage'],
        limitations='Development signing. Device acceptance testing remains required. Google proprietary services are not included.',
        channel='development', artifact_kind='chromium-browser',
        icon='https://africanbrowser.com/assets/africanbrowser-icon.png',
        privacy='https://africanbrowser.com/legal/privacy.html',
        terms='https://africanbrowser.com/legal/terms.html',
        copyright='https://africanbrowser.com/legal/copyright.html',
        apk_url=url, sha256=digest, source=info['source'], download_status='available')
    backup = database.with_name(database.name + '.before-africanbrowser-' + str(time.time_ns()))
    with sqlite3.connect(database) as connection:
        with sqlite3.connect(backup) as saved:
            connection.backup(saved)
        connection.execute(
            'INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) '
            'ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',
            ('africanbrowser.com', json.dumps(metadata), int(time.time())))
    print('AfricanBrowser listing installed; SHA-256 ' + digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path)
    parser.add_argument('--website-root', type=Path, required=True)
    args = parser.parse_args()
    if args.database is None:
        environment = subprocess.check_output(
            ['systemctl', 'show', 'africanappsstore.service', '--property=Environment', '--value'], text=True)
        settings = dict(item.split('=', 1) for item in shlex.split(environment) if '=' in item)
        args.database = Path(settings.get('STORE_DATA', '/var/lib/africanappsstore')) / 'store.sqlite3'
    install(args.database, args.website_root)
