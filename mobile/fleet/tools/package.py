#!/usr/bin/env python3
import hashlib,json,os,shutil,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
apps=json.loads((ROOT/'apps.json').read_text())
out=ROOT/'dist';out.mkdir(exist_ok=True)
sdk=Path(os.environ['ANDROID_HOME'])/'build-tools/35.0.0'
for app in apps:
    source=ROOT/'app/build/outputs/apk'/app['id']/'debug'/f'app-{app["id"]}-debug.apk'
    subprocess.run([str(sdk/'apksigner'),'verify','--verbose',str(source)],check=True,stdout=subprocess.DEVNULL)
    package=subprocess.check_output([str(sdk/'aapt'),'dump','badging',str(source)],text=True)
    if "package: name='"+app['package']+"'" not in package: raise ValueError('Wrong package identity')
    target=out/(app['slug']+'.apk');shutil.copyfile(source,target)
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    (out/(target.name+'.sha256')).write_text(checksum+'  '+target.name+'\n')
    web=ROOT/'web'/app['domain'];shutil.copyfile(target,web/target.name);shutil.copyfile(out/(target.name+'.sha256'),web/(target.name+'.sha256'))
    app['sha256']=checksum
with tarfile.open(out/'hosted-app-websites.tar.gz','w:gz') as archive:
    archive.add(ROOT/'web',arcname='web')
(out/'apps.json').write_text(json.dumps(apps,indent=2)+'\n')
print(f'{len(apps)} signed APKs verified and packaged')
