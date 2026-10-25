#!/usr/bin/env python3
import argparse,hashlib,json,sqlite3,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database,static=None):
    database=Path(database);static=Path(static) if static else ROOT/'static/postmaster'
    if not database.is_file():raise ValueError('Existing store database not found')
    info=json.loads((ROOT/'catalog/postmaster.json').read_text());release=json.loads((static/'release.json').read_text());apk=static/'postmaster.apk';digest=hashlib.sha256(apk.read_bytes()).hexdigest()
    if digest!=info['sha256'] or digest!=release['sha256'] or digest!=(static/'postmaster.apk.sha256').read_text().split()[0]:raise ValueError('APK checksum mismatch')
    if info['domain']!='postmaster.justisolve.com' or info['package']!='com.justisolve.postmaster' or info['version']!='1.0.0':raise ValueError('Unexpected package metadata')
    with zipfile.ZipFile(apk) as z:
        if not {'classes.dex','AndroidManifest.xml'}.issubset(z.namelist()):raise ValueError('Invalid APK')
    with sqlite3.connect(database,timeout=20) as c:
        c.execute('CREATE TABLE IF NOT EXISTS hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER NOT NULL DEFAULT 1,updated INTEGER NOT NULL)')
        c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(info['domain'],json.dumps(info),int(time.time())))
    print('UPDATED: Postmaster Android listing with verified APK checksum')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',required=True,type=Path);p.add_argument('--static',type=Path);a=p.parse_args();install(a.database,a.static)
