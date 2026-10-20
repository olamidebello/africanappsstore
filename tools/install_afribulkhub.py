#!/usr/bin/env python3
"""Publish the checksum-verified Africa Bulk Hub release to an existing store."""
import argparse,hashlib,json,os,shlex,sqlite3,subprocess,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def service_paths():
    def prop(name):return subprocess.check_output(['systemctl','show','africanappsstore.service','--property='+name,'--value'],text=True).strip()
    code=Path(prop('WorkingDirectory'));env=dict(p.split('=',1) for p in shlex.split(prop('Environment')) if '=' in p)
    if not code.is_absolute():raise ValueError('Invalid store working directory')
    return code/'static/afribulkhub',Path(env.get('STORE_DATA','/var/lib/africanappsstore'))/'store.sqlite3'
def install(database,static):
    apk=static/'africa-bulk-hub.apk';digest=hashlib.sha256(apk.read_bytes()).hexdigest()
    info=json.loads((ROOT/'catalog/afribulkhub.json').read_text());release=json.loads((static/'release.json').read_text())
    if digest!=(static/'africa-bulk-hub.apk.sha256').read_text().split()[0] or digest!=info['sha256'] or digest!=release['sha256']:raise ValueError('APK checksum or release metadata mismatch')
    if info['package']!='com.afribulkhub.mobile' or info['version']!='1.0.0':raise ValueError('Unexpected publisher package/version')
    with zipfile.ZipFile(apk) as z:
        if not {'classes.dex','AndroidManifest.xml'}.issubset(z.namelist()):raise ValueError('Invalid APK structure')
    metadata=dict(domain='afribulkhub.com',name='Africa Bulk Hub',category='Business',package=info['package'],version=info['version'],channel=info['channel'],website=info['website'],privacy=info['privacy'],terms=info['terms'],description=info['description'],slogan=info['slogan'],icon='/downloads/africa-bulk-hub-logo.png',features=['Africa Bulk Hub branded Android website client','Products, sourcing, orders and service work through the HTTPS site','Home, Reload, Browser and legal-page controls','User-selected PDF/PNG/JPEG upload chooser; backend size limits apply'],limitations='Internet and operational website required. No offline trading or native push. Use Browser for unsupported downloads. Live payment services are not active.',apk_url=info['apk_url'],sha256=digest,download_status='available')
    if not database.is_file():raise ValueError('Existing store database not found')
    with sqlite3.connect(database,timeout=20) as c:
        c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES (?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',('afribulkhub.com',json.dumps(metadata),int(time.time())))
    print('UPDATED: Africa Bulk Hub listing; SHA-256 '+digest)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path);p.add_argument('--static',type=Path);a=p.parse_args()
    static,database=service_paths() if a.database is None or a.static is None else (a.static,a.database)
    install(a.database or database,a.static or static)
