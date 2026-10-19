#!/usr/bin/env python3
"""Install verified download pages via explicit Nginx server include mapping.
Run on hosting server; no guessing document roots or replacing virtual hosts.
"""
import argparse,json,re,subprocess,tarfile,tempfile,shutil,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--mapping',type=Path,required=True);args=p.parse_args()
mapping=json.loads(args.mapping.read_text()); root=Path('/var/www/olamide-mobile')
if not mapping: raise SystemExit('No domain-to-Nginx-include mappings configured')
with tempfile.TemporaryDirectory() as tmp:
    stage=Path(tmp)
    with tarfile.open(args.bundle) as archive:
        for m in archive.getmembers():
            if not (m.isfile() or m.isdir()) or m.name.startswith('/') or '..' in Path(m.name).parts: raise ValueError('Unsafe archive')
        archive.extractall(stage)
    planned=[]
    for domain,include in mapping.items():
        if not re.fullmatch(r'(?:[a-z0-9-]+\.)+[a-z]{2,63}',domain): raise ValueError('Invalid domain')
        src=stage/'web'/domain; apks=list(src.glob('*.apk'))
        if len(apks)!=1: raise ValueError('APK missing for '+domain)
        apk=apks[0];expected=apk.with_name(apk.name+'.sha256').read_text().split()[0]
        if hashlib.sha256(apk.read_bytes()).hexdigest()!=expected: raise ValueError('Checksum failed')
        dest=root/domain
        include=Path(include)
        if not include.is_absolute() or not include.is_relative_to('/etc/nginx'): raise ValueError('Include must be under /etc/nginx')
        if not include.is_file(): raise ValueError('Create and reference the dedicated include in both active server blocks first: '+str(include))
        before=include.read_text()
        if before.strip() and not before.startswith('# Olamide mobile downloads'): raise ValueError('Refusing unmanaged include')
        planned.append((src,dest,include,before))
    changed=[]
    try:
        for src,dest,include,before in planned:
            dest.parent.mkdir(parents=True,exist_ok=True)
            backup=dest.with_name(dest.name+'.previous')
            if backup.exists(): raise ValueError('Previous backup exists; review it first: '+str(backup))
            if dest.exists(): dest.rename(backup)
            changed.append((dest,backup,include,before))
            shutil.copytree(src,dest)
            for item in [dest,*dest.rglob('*')]: item.chmod(0o755 if item.is_dir() else 0o644)
            include.write_text('# Olamide mobile downloads\nlocation = /download-app { return 302 /mobile-app/; }\nlocation ^~ /mobile-app/ { alias '+str(dest)+'/; index index.html; autoindex off; }\n')
        subprocess.run(['nginx','-t'],check=True)
        subprocess.run(['systemctl','reload','nginx'],check=True)
    except Exception:
        for dest,backup,include,before in reversed(changed):
            include.write_text(before)
            if dest.exists(): shutil.rmtree(dest)
            if backup.exists(): backup.rename(dest)
        raise
print('Download pages installed. Add /download-app to each website navigation and verify HTTPS downloads.')
