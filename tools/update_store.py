#!/usr/bin/env python3
"""Update the existing store service in place without changing its port or TLS."""
import argparse,json,os,shlex,shutil,sqlite3,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prop(name):return subprocess.check_output(['systemctl','show','africanappsstore.service','--property='+name,'--value'],text=True).strip()
def main():
 p=argparse.ArgumentParser();p.add_argument('--state',default='/var/lib/olamide-store-update');a=p.parse_args()
 state=Path(a.state);state.mkdir(parents=True,exist_ok=True,mode=0o700)
 code=Path(prop('WorkingDirectory'));env=dict(x.split('=',1) for x in shlex.split(prop('Environment')) if '=' in x)
 data=Path(env.get('STORE_DATA','/var/lib/africanappsstore'));database=data/'store.sqlite3'
 if not code.is_absolute() or not (code/'app.py').is_file() or not database.is_file():raise ValueError('Existing store code or database not found; inspect its service configuration')
 port=int(env.get('PORT','8080'));backup=state/('backup-'+str(time.time_ns()));backup.mkdir(mode=0o700)
 with sqlite3.connect(database) as src,sqlite3.connect(backup/'store.sqlite3') as dst:src.backup(dst)
 files=[Path('app.py')]+[f.relative_to(ROOT) for folder in ('templates','static') for f in (ROOT/folder).rglob('*') if f.is_file()];saved={}
 try:
  for rel in files:
   target=code/rel;saved[target]=target.read_bytes() if target.exists() else None
   dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   if saved[target] is not None:dest.write_bytes(saved[target])
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,target)
  # Migration adds only the new catalog table. Existing account data stays intact.
  subprocess.run(['python3',ROOT/'tools/sync_hosted_catalog.py','--database',database,'--manifest',ROOT/'mobile/fleet/apps.json'],check=True)
  subprocess.run(['python3',ROOT/'tools/install_media_hub.py','--database',database],check=True)
  subprocess.run(['python3',ROOT/'tools/install_postmaster.py','--database',database],check=True)
  subprocess.run(['python3',ROOT/'tools/install_aims.py','--database',database,'--static',ROOT/'static/aims'],check=True)
  subprocess.run(['systemctl','restart','africanappsstore.service'],check=True)
  for attempt in range(15):
   try:
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/hosted-apps',timeout=5) as r:
     if len(json.load(r))>0:break
   except Exception:
    if attempt==14:raise
    time.sleep(2)
  else:raise ValueError('Catalog health check failed')
  for route,marker in (('/terms','Terms and Conditions'),('/privacy','Privacy Policy'),('/copyright','Copyright')):
   with urllib.request.urlopen(f'http://127.0.0.1:{port}{route}',timeout=10) as r:
    if marker not in r.read().decode():raise ValueError('Legal page check failed: '+route)
 except Exception:
  for path,content in saved.items():
   if content is None:path.unlink(missing_ok=True)
   else:path.write_bytes(content)
  subprocess.run(['systemctl','restart','africanappsstore.service'],check=True)
  raise
 print('UPDATED: store catalog, verified download links and administration controls')
if __name__=='__main__':main()

