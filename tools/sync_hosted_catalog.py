#!/usr/bin/env python3
"""Synchronize truthful hosted-client descriptions and verified local downloads."""
import argparse,hashlib,json,re,sqlite3,time
from pathlib import Path
FEATURES=['Dedicated website client','Home and reload controls','External browser links','HTTPS-only in-app navigation','Separate app storage per domain']
def synchronize(db,manifest,downloads):
    apps=json.loads(Path(manifest).read_text());rows=[]
    for app in apps:
        domain=app['domain'];slug=app['slug']
        if not re.fullmatch(r'(?:[a-z0-9-]+\.)+[a-z]{2,63}',domain) or slug!=domain.replace('.','-'):raise ValueError('Invalid domain manifest')
        apk=Path(downloads)/domain/(slug+'.apk');checksum=apk.with_name(apk.name+'.sha256')
        ready=False;digest=''
        if apk.is_file() and checksum.is_file():
            digest=hashlib.sha256(apk.read_bytes()).hexdigest();ready=digest==checksum.read_text().split()[0]
            if not ready:raise ValueError('APK checksum mismatch for '+domain)
        rows.append((domain,json.dumps(dict(domain=domain,name=app['name'],category=app['category'],package=app['package'],website=app['url'],description=f"{app['name']} Android website client for {domain}. Access the platform’s existing web experience in a dedicated app.",features=FEATURES,limitations='Internet required. Native calls, background navigation, camera, microphone, file uploads and offline operation are not implemented. Use Browser for unsupported flows.',apk_url='https://'+domain+'/mobile-app/'+slug+'.apk' if ready else None,sha256=digest,download_status='available' if ready else 'build_pending')),int(time.time())))
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE IF NOT EXISTS hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER NOT NULL DEFAULT 1,updated INTEGER NOT NULL)')
        # A verified Chromium release replaces the generic website client for
        # this domain. Routine fleet sync must not downgrade it to a wrapper.
        specialized=c.execute('SELECT metadata FROM hosted_apps WHERE domain=?',('justisolve.com',)).fetchone()
        if specialized and json.loads(specialized[0]).get('artifact_kind')=='justisolve-preview':
            rows=[row for row in rows if row[0]!='justisolve.com']
        existing=c.execute('SELECT metadata FROM hosted_apps WHERE domain=?',('africanbrowser.com',)).fetchone()
        if existing and json.loads(existing[0]).get('artifact_kind')=='chromium-browser':
            rows=[row for row in rows if row[0]!='africanbrowser.com']
        aims=c.execute('SELECT metadata FROM hosted_apps WHERE domain=?',('identity.africandroid.world',)).fetchone()
        if aims and json.loads(aims[0]).get('artifact_kind')=='aims-android-client':
            rows=[row for row in rows if row[0]!='identity.africandroid.world']
        sip=c.execute('SELECT metadata FROM hosted_apps WHERE domain=?',('sip.dobhrap.com',)).fetchone()
        if sip and json.loads(sip[0]).get('artifact_kind')=='olamide-sip-native':
            rows=[row for row in rows if row[0]!='sip.dobhrap.com']
        c.executemany('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',rows)
    print(f'Synchronized {len(rows)} listings; downloads enabled only for checksum-verified local APKs')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--manifest',required=True);p.add_argument('--downloads',default='/var/www/olamide-mobile');a=p.parse_args();synchronize(a.database,a.manifest,a.downloads)
