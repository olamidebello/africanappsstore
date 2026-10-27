#!/usr/bin/env python3
"""Targeted backed-up store update; does not alter other listings, ports or TLS."""
import importlib.util,json,os,shlex,shutil,sqlite3,subprocess,time,urllib.request,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prop(name):return subprocess.check_output(['systemctl','show','africanappsstore.service','--property='+name,'--value'],text=True).strip()
def main():
 code=Path(prop('WorkingDirectory'));env=dict(x.split('=',1) for x in shlex.split(prop('Environment')) if '=' in x);data=Path(env.get('STORE_DATA','/var/lib/africanappsstore'));db=data/'store.sqlite3';port=int(env.get('PORT','8080'))
 if not code.is_absolute() or not (code/'app.py').is_file() or not db.is_file():raise ValueError('Existing store service or database not found')
 spec=importlib.util.spec_from_file_location('installer',ROOT/'tools/install_effortlesssmiles.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
 state=Path('/var/lib/effortlesssmiles-store-update')/str(time.time_ns());state.mkdir(parents=True,mode=0o700);target=code/'app.py';old=target.read_text();backup=state/'app.py';backup.write_text(old)
 with sqlite3.connect(db) as c:
  prior=c.execute('SELECT domain,metadata,visible,updated FROM hosted_apps WHERE domain=?',('effortlesssmiles.afribulkhub.com',)).fetchone()
  with sqlite3.connect(state/'store.sqlite3') as dst:c.backup(dst)
 saved={};folder=code/'static/effortlesssmiles';folder.mkdir(parents=True,exist_ok=True)
 try:
  for name in ['effortless-smiles-preview.apk','effortless-smiles-preview.apk.sha256','release.json','icon.svg']:
   path=folder/name;saved[path]=path.read_bytes() if path.exists() else None;shutil.copyfile(ROOT/'static/effortlesssmiles'/name,path)
  if 'effortless_files=' not in old:
   source=(ROOT/'app.py').read_text();start=source.index('        effortless_files=');end=source.index('        cellblock_files=',start);marker='        path=urlparse(self.path).path; query=parse_qs(urlparse(self.path).query)'
   if marker not in old:raise ValueError('Store routing changed; targeted patch cannot be applied safely')
   target.write_text(old.replace(marker,marker+'\n'+source[start:end],1));subprocess.run(['python3','-m','py_compile',target],check=True)
  result=installer.install(db,folder);subprocess.run(['systemctl','restart','africanappsstore.service'],check=True)
  expected=json.loads((folder/'release.json').read_text())
  for attempt in range(12):
   try:
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/downloads/effortless-smiles-preview.apk',timeout=10) as response:
     if hashlib.sha256(response.read(expected['size_bytes']+1)).hexdigest()!=expected['sha256']:raise ValueError('Served APK checksum mismatch')
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/hosted-apps',timeout=10) as response:
     rows=json.load(response)
     if result['visible'] and not any(x.get('domain')=='effortlesssmiles.afribulkhub.com' and x.get('sha256')==expected['sha256'] for x in rows):raise ValueError('Expected catalog listing not visible')
    break
   except Exception:
    if attempt==11:raise
    time.sleep(1)
 except Exception:
  target.write_text(old)
  for path,raw in saved.items():
   if raw is None:path.unlink(missing_ok=True)
   else:path.write_bytes(raw)
  with sqlite3.connect(db) as c:
   if prior:c.execute('UPDATE hosted_apps SET metadata=?,visible=?,updated=? WHERE domain=?',(prior[1],prior[2],prior[3],prior[0]))
   else:c.execute('DELETE FROM hosted_apps WHERE domain=?',('effortlesssmiles.afribulkhub.com',))
  subprocess.run(['systemctl','restart','africanappsstore.service'],check=True);raise
 print('UPDATED: Effortless Smiles signed preview and verified catalog entry; administrator visibility preserved')
if __name__=='__main__':main()
