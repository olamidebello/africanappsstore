#!/usr/bin/env python3
"""Attach dedicated download includes to exact active HTTPS virtual hosts."""
import argparse,fcntl,json,re,subprocess,time
from pathlib import Path
TOKEN=re.compile(r'#[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{};]|[^\s{};#]+')
def blocks(text):
    tokens=[m for m in TOKEN.finditer(text) if not m.group().startswith('#')]
    stack=[];result=[]
    for i,t in enumerate(tokens):
        if t.group()=='{': stack.append((i,i>0 and tokens[i-1].group()=='server'))
        elif t.group()=='}':
            if not stack: raise ValueError('Unbalanced Nginx configuration')
            start,server=stack.pop()
            if not server: continue
            depth=0;words=[];directives=[]
            for inner in tokens[start+1:i]:
                value=inner.group()
                if value=='{': depth+=1;words=[]
                elif value=='}': depth-=1;words=[]
                elif depth==0:
                    if value==';': directives.append(words);words=[]
                    else: words.append(value.strip('"\''))
            names=[];includes=[];tls=False
            for row in directives:
                if not row: continue
                if row[0]=='server_name': names.extend(row[1:])
                if row[0]=='include': includes.extend(row[1:])
                if row[0]=='listen' and len(row)>1:
                    address=row[1]
                    tls |= (address=='443' or address.endswith(':443')) and 'ssl' in row[2:]
            result.append(dict(close=t.start(),names=names,includes=includes,tls=tls))
    if stack: raise ValueError('Unbalanced Nginx configuration')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--mapping',type=Path,required=True);p.add_argument('--state',type=Path,required=True);args=p.parse_args()
    args.state.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (args.state/'deploy.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        mapping=json.loads(args.mapping.read_text());planned={};reserved={};new=[]
        if len(set(mapping.values()))!=len(mapping): raise ValueError('Each domain needs a distinct include path')
        dump=subprocess.check_output(['nginx','-T'],text=True,stderr=subprocess.PIPE)
        files={Path(x).resolve() for x in re.findall(r'^# configuration file (.+):$',dump,re.M)}
        parsed={f: (f.read_text(),blocks(f.read_text())) for f in files}
        for domain,inc in mapping.items():
            if not re.fullmatch(r'(?:[a-z0-9-]+\.)+[a-z]{2,63}',domain): raise ValueError('Invalid domain')
            path=Path(inc)
            if not re.fullmatch(r'/etc/nginx/mobile-apps/[a-z0-9.-]+\.conf',inc): raise ValueError('Use a dedicated /etc/nginx/mobile-apps/domain.conf include')
            if path.is_symlink(): raise ValueError('Symlink include refused')
            if path.exists() and path.read_text().strip() and not path.read_text().startswith('# Olamide mobile downloads'):
                raise ValueError('Unmanaged include refused: '+inc)
            matches=[(f,b) for f,(_,bs) in parsed.items() for b in bs if b['tls'] and domain in b['names']]
            if len(matches)!=1: raise ValueError(f'{domain}: expected one exact active HTTPS server block, found {len(matches)}; provision or disambiguate its HTTPS website first')
            f,b=matches[0];key=(f,b['close'])
            if key in reserved: raise ValueError('Different domain apps share a server block; split those virtual hosts first')
            reserved[key]=domain
            if inc not in b['includes']: planned.setdefault(f,[]).append((b['close'],'\n    include '+inc+'; # Olamide mobile downloads\n'))
            if not path.exists():new.append(path)
        backups={};saved=args.state/'nginx-backups'/str(time.time_ns())
        try:
            for path in new:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('# Olamide mobile downloads — populated after APK validation\n');path.chmod(0o644)
            if planned:saved.mkdir(parents=True,mode=0o700)
            for i,(f,edits) in enumerate(planned.items()):
                old=parsed[f][0];backups[f]=old
                (saved/(str(i)+'.conf')).write_text(old)
                (saved/(str(i)+'.path')).write_text(str(f))
                updated=old
                for offset,insert in sorted(edits,reverse=True): updated=updated[:offset]+insert+updated[offset:]
                f.write_text(updated)
            subprocess.run(['nginx','-t'],check=True)
            if planned or new: subprocess.run(['systemctl','reload','nginx'],check=True)
        except Exception:
            for f,old in backups.items():f.write_text(old)
            for path in new:path.unlink(missing_ok=True)
            subprocess.run(['nginx','-t'],check=True)
            subprocess.run(['systemctl','reload','nginx'],check=True)
            raise
        print('CONFIGURED' if planned or new else 'UNCHANGED')
if __name__=='__main__':main()
