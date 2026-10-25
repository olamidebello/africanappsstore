#!/usr/bin/env python3
"""Update only SIP install routes, assets and catalog; retain other hosted apps."""
import json,shlex,shutil,sqlite3,subprocess,time,urllib.request,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sip_downloads import integrate_app,integrate_cards
from install_sip import install
from update_store import prop

def main():
 code=Path(prop('WorkingDirectory'));env=dict(x.split('=',1) for x in shlex.split(prop('Environment')) if '=' in x);database=Path(env.get('STORE_DATA','/var/lib/africanappsstore'))/'store.sqlite3';port=int(env.get('PORT','8080'))
 if not code.is_absolute() or not (code/'app.py').is_file() or not database.is_file():raise ValueError('Existing store installation required')
 backup=Path('/var/lib/olamide-store-update')/('sip-'+str(time.time_ns()));backup.mkdir(parents=True,mode=0o700)
 updates={Path('app.py'):integrate_app((code/'app.py').read_text()).encode(),Path('static/app.js'):integrate_cards((code/'static/app.js').read_text()).encode(),Path('sip_downloads.py'):(ROOT/'sip_downloads.py').read_bytes()}
 for p in (ROOT/'static/sip').iterdir():
  if p.is_file():updates[p.relative_to(ROOT)]=p.read_bytes()
 with sqlite3.connect(database) as c:
  previous=c.execute("SELECT domain,metadata,visible,updated FROM hosted_apps WHERE domain='sip.dobhrap.com'").fetchone()
  with sqlite3.connect(backup/'store.sqlite3') as dest:c.backup(dest)
 saved={}
 try:
  for name,content in updates.items():
   target=code/name
   if target.is_symlink():raise ValueError('Symlinked source file refused')
   saved[name]=target.read_bytes() if target.exists() else None
   if saved[name] is not None:
    p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(saved[name])
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
  subprocess.run(['python3','-m','py_compile',code/'app.py',code/'sip_downloads.py'],check=True)
  install(database);subprocess.run(['systemctl','restart','africanappsstore.service'],check=True)
  for attempt in range(15):
   try:
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/install/sip',timeout=5) as r:
     if b'Install or update Olamide SIP' not in r.read():raise ValueError('Install page missing')
    break
   except Exception:
    if attempt==14:raise
    time.sleep(1)
 except Exception:
  for name,content in saved.items():
   p=code/name
   if content is None:p.unlink(missing_ok=True)
   else:p.write_bytes(content)
  with sqlite3.connect(database) as c:
   if previous:c.execute('INSERT OR REPLACE INTO hosted_apps(domain,metadata,visible,updated) VALUES(?,?,?,?)',previous)
   else:c.execute("DELETE FROM hosted_apps WHERE domain='sip.dobhrap.com'")
  subprocess.run(['systemctl','restart','africanappsstore.service']);raise
 print('UPDATED SIP device install page and catalog. Backup: '+str(backup))
if __name__=='__main__':main()
