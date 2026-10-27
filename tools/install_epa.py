#!/usr/bin/env python3
"""Add only Epa's PWA listing, preserving other catalog rows and store accounts."""
import argparse,json,os,shlex,shutil,sqlite3,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOMAIN='epafestival.africandroid.world'


def frontend(text):
    # Existing store versions already support install_url. Add only Epa's icon/platform label.
    if 'Install on your device' not in text:
        anchor='<a href="${esc(a.website)}" target="_blank" rel="noopener">Open website</a>'
        if anchor not in text:raise ValueError('Unrecognized store frontend; refusing to replace it')
        text=text.replace(anchor,"${a.install_url&&a.install_url.startsWith('https://')?`<a class=\"button\" href=\"${esc(a.install_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Install on your device</a>`:''}"+anchor)
    if "a.domain==='epafestival.africandroid.world'" not in text:
        anchor='<h3>${esc(a.name)}</h3>'
        if anchor not in text:raise ValueError('Hosted-app card template missing')
        text=text.replace(anchor,"${a.domain==='epafestival.africandroid.world'?'<img src=\"https://epafestival.africandroid.world/assets/app-192.png\" alt=\"Epa: Spirit of Oro-Ago\" width=\"120\" height=\"120\">':''}"+anchor,1)
    needle="'academy.africandroid.world'].includes(a.domain)?esc(a.platforms)"
    text=text.replace(needle,"'academy.africandroid.world','epafestival.africandroid.world'].includes(a.domain)?esc(a.platforms)")
    return text


def install(database,code=None,state=None):
    database=Path(database)
    if not database.is_file():raise ValueError('Existing store database not found')
    meta=json.loads((ROOT/'catalog/epafestival.json').read_text())
    if meta['domain']!=DOMAIN or meta['apk_url'] is not None:raise ValueError('Invalid Epa web-app listing')
    target=Path(code)/'static/app.js' if code else None
    old=target.read_bytes() if target else None
    new=frontend(old.decode()) if old is not None else None
    backup=Path(state or '/var/lib/olamide-store-update')/('epa-'+str(time.time_ns()))
    backup.mkdir(parents=True,mode=0o700)
    os.chmod(backup,0o700)
    with sqlite3.connect(database) as src,sqlite3.connect(backup/'store.sqlite3') as dst:src.backup(dst)
    os.chmod(backup/'store.sqlite3',0o600)
    if old is not None:(backup/'app.js').write_bytes(old)
    try:
        with sqlite3.connect(database) as con:
            con.execute('CREATE TABLE IF NOT EXISTS hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER NOT NULL DEFAULT 1,updated INTEGER NOT NULL)')
            con.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(DOMAIN,json.dumps(meta),int(time.time())))
            if target and new!=old.decode():target.write_text(new)
    except Exception:
        if target and old is not None:target.write_bytes(old)
        raise
    return {'domain':DOMAIN,'status':'listing_updated','install_url':meta['install_url'],'backup':str(backup)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database');p.add_argument('--discover',action='store_true');a=p.parse_args()
    database=a.database;code=None
    if a.discover:
        def prop(k):return subprocess.check_output(['systemctl','show','africanappsstore.service','-p',k,'--value'],text=True).strip()
        env=dict(x.split('=',1) for x in shlex.split(prop('Environment')) if '=' in x)
        database=str(Path(env.get('STORE_DATA','/var/lib/africanappsstore'))/'store.sqlite3');code=prop('WorkingDirectory')
        if not Path(code).is_absolute() or not (Path(code)/'static/app.js').is_file():raise ValueError('Existing store frontend not found')
    if not database:p.error('--database or --discover required')
    result=install(database,code)
    print(json.dumps(result))
