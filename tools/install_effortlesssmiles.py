#!/usr/bin/env python3
"""Verify the release and upsert only the Effortless Smiles hosted listing."""
import argparse,hashlib,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database,static=None):
 static=Path(static or ROOT/'static/effortlesssmiles');info=json.loads((ROOT/'catalog/effortlesssmiles.json').read_text());release=json.loads((static/'release.json').read_text());apk=static/'effortless-smiles-preview.apk'
 digest=hashlib.sha256(apk.read_bytes()).hexdigest()
 if digest!=info['sha256'] or digest!=release['sha256'] or digest!=(static/(apk.name+'.sha256')).read_text().split()[0]:raise ValueError('Effortless Smiles checksum mismatch')
 if release['package']!='com.effortlesssmiles.mobile.preview' or info['package']!=release['package'] or info['version']!=release['version'] or apk.stat().st_size!=release['size_bytes']:raise ValueError('Effortless Smiles release metadata mismatch')
 if info['signing_certificate_sha256']!=release['signing_certificate_sha256'] or release['demo_payments_enabled'] is not False or release['demo_purchases_enabled'] is not False:raise ValueError('Unexpected signing or demo safety metadata')
 database=Path(database)
 if not database.is_file():raise ValueError('Existing store database not found')
 with sqlite3.connect(database) as c:
  c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(info['domain'],json.dumps(info),int(time.time())))
  visible=c.execute('SELECT visible FROM hosted_apps WHERE domain=?',(info['domain'],)).fetchone()[0]
 return {'sha256':digest,'visible':bool(visible)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--static');a=p.parse_args();print(json.dumps(install(a.database,a.static)))
