#!/usr/bin/env python3
"""Install only a checksum-verified Africa Jobs listing in the existing store DB."""
import argparse,hashlib,json,sqlite3,time,subprocess,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database,static):
    apk=static/'africa-jobs.apk'; digest=hashlib.sha256(apk.read_bytes()).hexdigest()
    if digest!=(static/'africa-jobs.apk.sha256').read_text().split()[0]: raise ValueError('APK checksum mismatch')
    info=json.loads((ROOT/'catalog/africajobs.json').read_text())
    metadata=dict(domain='jobs.africandroid.world',name='Africa Jobs',category='Business',package=info['package'],website=info['website'],description=info['description'],features=['Africa Jobs branded Android client','Home, Reload and Browser controls','HTTPS-only in-app navigation','Separate app login storage'],limitations='Development APK. Internet required. Use Browser for file uploads, downloads and unsupported flows. No native notifications or offline work.',apk_url='https://africanappsstore.space/downloads/africa-jobs.apk',sha256=digest,download_status='available')
    if not database.is_file(): raise ValueError('Existing store database not found')
    with sqlite3.connect(database) as c:
        c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',('jobs.africandroid.world',json.dumps(metadata),int(time.time())))
    print('Africa Jobs listing installed; SHA-256 '+digest)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,default=Path('/var/lib/africanappsstore/store.sqlite3'));p.add_argument('--static',type=Path);a=p.parse_args()
    if a.static is None:
        code=subprocess.check_output(['systemctl','show','africanappsstore.service','--property=WorkingDirectory','--value'],text=True).strip()
        if not Path(code).is_absolute(): raise ValueError('Store WorkingDirectory is not absolute')
        a.static=Path(code)/'static/africajobs'
    install(a.database,a.static)
