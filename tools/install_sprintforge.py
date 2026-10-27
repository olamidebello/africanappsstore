#!/usr/bin/env python3
"""Publish only SprintForge in the existing Apps Store; preserve accounts and other listings."""
import shutil
import argparse,hashlib,json,os,shlex,sqlite3,subprocess,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOMAIN='sprintforge.netwizzard.tech'
def install(database,release=None,backup_root=None):
    database=Path(database)
    if not database.is_file():raise ValueError('Existing store database not found')
    meta=json.loads((ROOT/'catalog/sprintforge.json').read_text())
    meta.update(apk_url=None,sha256='',download_status='install_page')
    if release:
        if release.get('package')!='com.sprintforge.mobile.preview':raise ValueError('Unexpected package')
        meta.update(apk_url='https://github.com/olamidebello/SprintForge/releases/download/android-preview/sprintforge-preview.apk',sha256=release['sha256'],version=release['version'],download_status='available',signing_certificate_sha256=release['signing_certificate_sha256'])
    backup=Path(backup_root or '/var/lib/olamide-store-update')/('sprintforge-'+str(time.time_ns())+'.db')
    backup.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    previous=os.umask(0o077)
    try:
        with sqlite3.connect(database) as c,sqlite3.connect(backup) as dest:c.backup(dest)
    finally:os.umask(previous)
    with sqlite3.connect(database) as c:
        c.execute('CREATE TABLE IF NOT EXISTS hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER NOT NULL DEFAULT 1,updated INTEGER NOT NULL)')
        c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(DOMAIN,json.dumps(meta),int(time.time())))
    print(json.dumps({'domain':DOMAIN,'status':meta['download_status'],'backup':str(backup),'install_url':meta['install_url']}))
def verified_release():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base='https://github.com/olamidebello/SprintForge/releases/download/android-preview/'
    try:
        with opener.open(base+'release.json',timeout=30) as r:release=json.load(r)
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise
    if release.get('package')!='com.sprintforge.mobile.preview':raise ValueError('Unexpected Android package metadata')
    with opener.open(base+'sprintforge-preview.apk',timeout=60) as r:data=r.read(20_000_001)
    if len(data)>20_000_000 or len(data)!=release.get('size_bytes') or hashlib.sha256(data).hexdigest()!=release.get('sha256'):raise ValueError('Release APK does not match its published checksum')
    return release
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database');p.add_argument('--discover',action='store_true');a=p.parse_args()
    database=a.database
    if a.discover:
        raw=subprocess.check_output(['systemctl','show','africanappsstore.service','-p','Environment','--value'],text=True)
        values=dict(x.split('=',1) for x in shlex.split(raw) if '=' in x)
        database=str(Path(values.get('STORE_DATA','/var/lib/africanappsstore'))/'store.sqlite3')
    if not database:p.error('--database or --discover is required')
    install(database,verified_release())
    if a.discover:
        code=Path(subprocess.check_output(['systemctl','show','africanappsstore.service','-p','WorkingDirectory','--value'],text=True).strip())
        script=code/'static'/'app.js'
        text=script.read_text()
        anchor='<a href="${esc(a.website)}" target="_blank" rel="noopener">Open website</a>'
        addition="${a.install_url&&a.install_url.startsWith('https://')?`<a class=\"button\" href=\"${esc(a.install_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Install on your device</a>`:''}"
        if 'Install on your device' not in text:
            if anchor not in text:raise ValueError('Store UI differs; listing saved but install-button patch needs review')
            backup=Path('/var/lib/olamide-store-update')/('sprintforge-ui-'+str(time.time_ns())+'.js')
            shutil.copy2(script,backup);backup.chmod(0o600)
            script.write_text(text.replace(anchor,addition+anchor))

