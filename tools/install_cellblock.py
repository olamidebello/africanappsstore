#!/usr/bin/env python3
import argparse,hashlib,json,sqlite3,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database):
 info=json.loads((ROOT/'catalog/cellblock.json').read_text());static=ROOT/'static/cellblock';apk=static/'cellblock.apk';digest=hashlib.sha256(apk.read_bytes()).hexdigest();release=json.loads((static/'release.json').read_text())
 if digest!=info['sha256'] or digest!=release['sha256'] or digest!=(static/'cellblock.apk.sha256').read_text().split()[0]:raise ValueError('Cellblock checksum mismatch')
 if info['package']!='world.africandroid.cellblock' or info['domain']!='cellblockcatandmouse.africandroid.world':raise ValueError('Invalid Cellblock metadata')
 with zipfile.ZipFile(apk) as z:
  if not {'classes.dex','AndroidManifest.xml'}.issubset(z.namelist()):raise ValueError('Invalid APK')
 if not Path(database).is_file():raise ValueError('Existing store database required')
 with sqlite3.connect(database) as c:
  c.execute('CREATE TABLE IF NOT EXISTS hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER NOT NULL DEFAULT 1,updated INTEGER NOT NULL)')
  c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(info['domain'],json.dumps(info),int(time.time())))
 print('UPDATED: Cellblock game listing and verified Android download')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--database',required=True);a=p.parse_args();install(a.database)
