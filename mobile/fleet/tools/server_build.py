#!/usr/bin/env python3
"""Root-owned, repeatable on-server Android build; signing secrets never logged."""
import argparse,fcntl,hashlib,json,os,secrets,shutil,subprocess,tempfile,time,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(argv,**kw):
    return subprocess.run([str(a) for a in argv],check=True,**kw)
def download(url,path):
    with urllib.request.urlopen(url,timeout=120) as src,path.open('wb') as dst: shutil.copyfileobj(src,dst)
def extract_zip(archive,dest):
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            if entry.filename.startswith('/') or '..' in Path(entry.filename).parts: raise ValueError('Unsafe tool archive')
        z.extractall(dest)
def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--mapping',type=Path,required=True)
    p.add_argument('--force',action='store_true');p.add_argument('--incremental',action='store_true');args=p.parse_args()
    os.umask(0o077);args.state.mkdir(parents=True,exist_ok=True)
    with (args.state/'deploy.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        apps=json.loads((ROOT/'apps.json').read_text());mapping=json.loads(args.mapping.read_text())
        if not mapping or not set(mapping).issubset({a['domain'] for a in apps}): raise ValueError('Mapping has unknown domains or is empty')
        for inc in mapping.values():
            path=Path(inc)
            if not path.is_absolute() or not path.is_relative_to('/etc/nginx') or not path.is_file(): raise ValueError('Dedicated Nginx include missing: '+str(path))
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        identity=hashlib.sha256((commit+args.mapping.read_text()).encode()).hexdigest()
        marker=args.state/'deployed.json'
        if marker.exists() and json.loads(marker.read_text()).get('identity')==identity and not args.force:
            print('UNCHANGED: source and domain mappings already deployed');return
        sdk=args.state/'android-sdk';sdk.mkdir(exist_ok=True)
        manager=sdk/'cmdline-tools/latest/bin/sdkmanager'
        if not manager.exists():
            with tempfile.TemporaryDirectory(dir=args.state) as td:
                td=Path(td);z=td/'sdk.zip'
                download('https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip',z)
                extract_zip(z,td/'sdk');manager.parent.parent.parent.mkdir(parents=True,exist_ok=True)
                shutil.move(str(td/'sdk/cmdline-tools'),str(manager.parent.parent))
                for script in manager.parent.iterdir(): script.chmod(0o700)
        env=dict(os.environ,ANDROID_HOME=str(sdk),ANDROID_SDK_ROOT=str(sdk))
        run([manager,'--licenses'],input=('y\n'*200).encode(),stdout=subprocess.DEVNULL,env=env)
        run([manager,'platform-tools','platforms;android-35','build-tools;35.0.0'],env=env)
        gradle=args.state/'gradle-8.9/bin/gradle'
        if not gradle.exists():
            with tempfile.TemporaryDirectory(dir=args.state) as td:
                z=Path(td)/'gradle.zip';url='https://services.gradle.org/distributions/gradle-8.9-bin.zip'
                download(url,z)
                expected=urllib.request.urlopen(url+'.sha256',timeout=30).read().decode().split()[0]
                if hashlib.sha256(z.read_bytes()).hexdigest()!=expected: raise ValueError('Gradle checksum mismatch')
                extract_zip(z,args.state)
            gradle.chmod(0o700)
        # Tool ZIPs may not retain executable permissions through Python zipfile.
        for directory in (sdk/'build-tools/35.0.0',sdk/'platform-tools'):
            if directory.exists():
                for tool in directory.rglob('*'):
                    if tool.is_file() and tool.open('rb').read(4) in (b'\x7fELF',b'#!/b',b'#!/u'): tool.chmod(0o700)
        signing=args.state/'signing';signing.mkdir(exist_ok=True,mode=0o700)
        key=signing/'hosted-apps.jks';passwordfile=signing/'password'
        if key.exists() and not passwordfile.exists(): raise ValueError('Signing password missing; restore backup')
        if not passwordfile.exists(): passwordfile.write_text(secrets.token_urlsafe(40));passwordfile.chmod(0o600)
        password=passwordfile.read_text()
        env.update(FLEET_KEYSTORE=str(key),FLEET_KEY_PASSWORD=password,FLEET_KEY_ALIAS='hostedapps')
        if not key.exists():
            run(['keytool','-genkeypair','-noprompt','-keystore',key,'-alias','hostedapps','-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=Olamide Hosted Apps','-storepass:env','FLEET_KEY_PASSWORD','-keypass:env','FLEET_KEY_PASSWORD'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            key.chmod(0o600)
        counter=args.state/'version-code';version=int(counter.read_text())+1 if counter.exists() else 1
        counter.write_text(str(version));env['APP_VERSION_CODE']=str(version)
        run(['python3',ROOT/'tools/prepare.py'])
        run([gradle,'-p',ROOT,':app:assembleDebug','--no-daemon','--max-workers=2'],env=env)
        run(['python3',ROOT/'tools/package.py'],env=env)
        run(['python3',ROOT/'tools/deploy.py','--bundle',ROOT/'dist/hosted-app-websites.tar.gz','--mapping',args.mapping])
        store_db=Path('/var/lib/africanappsstore/store.sqlite3')
        sync=ROOT.parents[1]/'tools/sync_hosted_catalog.py'
        if store_db.is_file() and sync.is_file():
            run(['python3',sync,'--database',store_db,'--manifest',ROOT/'apps.json'])
        marker.write_text(json.dumps(dict(identity=identity,commit=commit,version=version,deployed_at=int(time.time()))))
        print('DEPLOYED: verified APKs and domain download pages installed')
if __name__=='__main__': main()
