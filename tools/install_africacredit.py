#!/usr/bin/env python3
"""Register the verified Africa Credit APK in an existing store database."""
import argparse,hashlib,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database,assets):
    meta=json.loads((ROOT/'catalog/africacredit.json').read_text())
    apk=assets/'africa-credit.apk'
    digest=hashlib.sha256(apk.read_bytes()).hexdigest()
    if digest!=meta['sha256'] or digest!=(assets/'africa-credit.apk.sha256').read_text().split()[0]:
        raise ValueError('Africa Credit APK checksum mismatch')
    if not database.is_file():raise ValueError('Existing store database missing; pass --database')
    item=dict(domain='credit.africandroid.world',name=meta['name'],category='Finance',package=meta['package'],website=meta['website'],description=meta['description'],version=meta['version'],apk_url=meta['apk_url'],sha256=digest,download_status='available',features=['Signed Android website client','Nigerian Pidgin interface where translated','Separate application login storage','HTTPS-only navigation'],limitations='Internet required. No native push, offline access or new financial provider integrations. Use browser for downloads and unsupported flows.')
    with sqlite3.connect(database) as c:
        c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',('credit.africandroid.world',json.dumps(item),int(time.time())))
    print('Africa Credit listing installed; SHA-256 '+digest)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);a=p.parse_args();install(a.database,a.assets)
