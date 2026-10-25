#!/usr/bin/env python3
"""Upsert only the checksum-verified AIMS listing, preserving admin visibility."""
import argparse,hashlib,json,shlex,sqlite3,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database,static):
 info=json.loads((ROOT/'catalog/aims.json').read_text());apk=static/'aims.apk'
 digest=hashlib.sha256(apk.read_bytes()).hexdigest()
 if digest!=info['sha256'] or digest!=(static/'aims.apk.sha256').read_text().split()[0]:raise ValueError('AIMS APK checksum mismatch')
 if not database.is_file():raise ValueError('Existing store database not found')
 metadata=dict(domain='identity.africandroid.world',name='AIMS — Africa Identity Management System',category='Productivity',package=info['package'],version=info['version'],website=info['website'],install_url=info['install_url'],description='One Identity. A World of Possibilities. AIMS Android client for identity applications, documents, appointments and secure messages.',features=info['features'],limitations=info['limitations'],apk_url=info['apk_url'],sha256=digest,signer_sha256=info['signer_sha256'],download_status='available',artifact_kind='aims-android-client')
 with sqlite3.connect(database) as c:
  c.execute('CREATE TABLE IF NOT EXISTS hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER NOT NULL DEFAULT 1,updated INTEGER NOT NULL)')
  c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',('identity.africandroid.world',json.dumps(metadata),int(time.time())))
 print('AIMS signed Android listing installed; SHA-256 '+digest)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--database',type=Path);p.add_argument('--static',type=Path,default=ROOT/'static/aims');a=p.parse_args()
 if a.database is None:
  env=subprocess.check_output(['systemctl','show','africanappsstore.service','--property=Environment','--value'],text=True)
  settings=dict(x.split('=',1) for x in shlex.split(env) if '=' in x);a.database=Path(settings.get('STORE_DATA','/var/lib/africanappsstore'))/'store.sqlite3'
 install(a.database,a.static)
