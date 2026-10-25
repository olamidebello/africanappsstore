#!/usr/bin/env python3
"""Install the checksum-verified JustiSolve preview, preserving admin visibility."""
import argparse,hashlib,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database,static):
    database=Path(database);static=Path(static)
    info=json.loads((ROOT/'catalog/justisolve.json').read_text());release=json.loads((static/'release.json').read_text());apk=static/'justisolve-preview.apk'
    digest=hashlib.sha256(apk.read_bytes()).hexdigest()
    if digest!=(static/'justisolve-preview.apk.sha256').read_text().split()[0] or digest!=info['sha256'] or digest!=release['sha256']:raise ValueError('JustiSolve APK checksum mismatch')
    if info['domain']!='justisolve.com' or info['package']!='com.justisolve.mobile.preview' or info['package']!=release['package'] or info['version']!=release['version']:raise ValueError('JustiSolve package metadata mismatch')
    if apk.stat().st_size!=release['size_bytes'] or info['signing_certificate_sha256']!=release['signing_certificate_sha256']:raise ValueError('JustiSolve release metadata mismatch')
    if not database.is_file():raise ValueError('Existing store database not found')
    with sqlite3.connect(database) as c:
        c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',('justisolve.com',json.dumps(info),int(time.time())))
        visible=c.execute("SELECT visible FROM hosted_apps WHERE domain='justisolve.com'").fetchone()[0]
    if not visible:print('JustiSolve listing hidden by administrator')
    print('JustiSolve verified preview listing installed; SHA-256 '+digest)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',required=True,type=Path);parser.add_argument('--static',type=Path,default=ROOT/'static/justisolve');args=parser.parse_args();install(args.database,args.static)
