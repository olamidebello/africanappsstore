#!/usr/bin/env python3
"""Verify/download a pinned build, then upsert only the Media listing, preserving visibility."""
import argparse,hashlib,io,json,sqlite3,time,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ensure_package(static):
 static=Path(static);static.mkdir(parents=True,exist_ok=True);release=json.loads((ROOT/'static/media/release.json').read_text());apk=static/'africa-media-android-debug.apk'
 if not apk.is_file() or hashlib.sha256(apk.read_bytes()).hexdigest()!=release['sha256']:
  with urllib.request.urlopen(release['artifact_url'],timeout=60) as response: raw=response.read(30000001)
  if len(raw)>30000000 or hashlib.sha256(raw).hexdigest()!=release['artifact_sha256']:raise ValueError('Build archive checksum mismatch')
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   entry=archive.getinfo('africa-media-android-debug.apk')
   if entry.file_size!=release['size_bytes']:raise ValueError('APK size mismatch')
   data=archive.read(entry)
  if hashlib.sha256(data).hexdigest()!=release['sha256']:raise ValueError('APK checksum mismatch')
  temporary=apk.with_suffix('.apk.pending');temporary.write_bytes(data);temporary.chmod(0o644);temporary.replace(apk)
 apk.chmod(0o644)
 static.chmod(0o755)
 for name in ['release.json','africa-media-android-debug.apk.sha256']:
  target=static/name;target.write_bytes((ROOT/'static/media'/name).read_bytes());target.chmod(0o644)
 return release

def install(database,static=None):
 database=Path(database)
 if not database.is_file():raise ValueError('Existing store database not found')
 static=Path(static or ROOT/'static/media');release=ensure_package(static);metadata=json.loads((ROOT/'catalog/africa-media-hub.json').read_text())
 if metadata['domain']!='media.africandroid.world' or metadata['sha256']!=release['sha256'] or metadata['package']!=release['package']:raise ValueError('Unexpected Media Hub release')
 with sqlite3.connect(database) as c:
  c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(metadata['domain'],json.dumps(metadata),int(time.time())))
  visible=c.execute('SELECT visible FROM hosted_apps WHERE domain=?',(metadata['domain'],)).fetchone()[0]
 return {'sha256':release['sha256'],'visible':bool(visible)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--database',required=True,type=Path);p.add_argument('--static',type=Path);a=p.parse_args();print(json.dumps(install(a.database,a.static)))
