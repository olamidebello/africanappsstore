from sip_downloads import serve_sip
import os, sqlite3, json, hashlib, secrets, hmac, time, re, zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).parent
DATA=Path(os.environ.get('STORE_DATA',str(ROOT/'data'))); DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'store.sqlite3'
def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def password(p,s=None):
    s=s or secrets.token_hex(16)
    return s+':'+hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def init():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user');
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),csrf TEXT,expires INTEGER);
        CREATE TABLE IF NOT EXISTS apps(id INTEGER PRIMARY KEY,owner INTEGER REFERENCES users(id),name TEXT NOT NULL,package TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,category TEXT NOT NULL,description TEXT NOT NULL,version TEXT NOT NULL,age INTEGER DEFAULT 3,privacy TEXT NOT NULL,status TEXT DEFAULT 'draft',release_notes TEXT DEFAULT '',downloads INTEGER DEFAULT 0,created INTEGER);
        CREATE TABLE IF NOT EXISTS releases(id INTEGER PRIMARY KEY,app_id INTEGER REFERENCES apps(id),filename TEXT,sha256 TEXT,size INTEGER,created INTEGER);
        CREATE TABLE IF NOT EXISTS wishlist(user_id INTEGER REFERENCES users(id),app_id INTEGER REFERENCES apps(id),PRIMARY KEY(user_id,app_id));
        CREATE TABLE IF NOT EXISTS library(user_id INTEGER REFERENCES users(id),app_id INTEGER REFERENCES apps(id),PRIMARY KEY(user_id,app_id));
        CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),app_id INTEGER REFERENCES apps(id),rating INTEGER CHECK(rating BETWEEN 1 AND 5),body TEXT,reply TEXT DEFAULT '',UNIQUE(user_id,app_id));
        CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),app_id INTEGER REFERENCES apps(id),reason TEXT,status TEXT DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS memberships(user_id INTEGER REFERENCES users(id),app_id INTEGER REFERENCES apps(id),kind TEXT,PRIMARY KEY(user_id,app_id,kind));
        CREATE TABLE IF NOT EXISTS settings(user_id INTEGER PRIMARY KEY REFERENCES users(id),value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),subject TEXT,body TEXT,status TEXT DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER NOT NULL DEFAULT 1,updated INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,object_id INTEGER,created INTEGER);
        ''')
        email=os.environ.get('ADMIN_EMAIL'); pw=os.environ.get('ADMIN_PASSWORD')
        if email and pw and not c.execute('SELECT 1 FROM users WHERE email=?',(email.lower(),)).fetchone():
            if len(pw)<14: raise ValueError('ADMIN_PASSWORD must have at least 14 characters')
            c.execute('INSERT INTO users(email,name,password,role) VALUES(?,?,?,?)',(email.lower(),'Administrator',password(pw),'admin'))
class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): pass
    def send(self,obj,status=200,cookie=None):
        raw=json.dumps(obj).encode(); self.send_response(status); self.headers_out('application/json',len(raw))
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();
        if self.command!='HEAD': self.wfile.write(raw)
    def headers_out(self,kind,length):
        self.send_header('Content-Type',kind); self.send_header('Content-Length',str(length)); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','same-origin'); self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    def do_HEAD(self): self.handle_request()
    def do_GET(self): self.handle_request()
    def do_POST(self): self.handle_request()
    def handle_request(self):
        try:self.route()
        except PermissionError as e:self.send({'error':str(e)},403)
        except (ValueError,KeyError,TypeError,AttributeError,zipfile.BadZipFile,json.JSONDecodeError) as e:self.send({'error':str(e)},400)
        except sqlite3.IntegrityError:self.send({'error':'Duplicate or invalid record'},409)
        except Exception:self.send({'error':'Internal server error'},500)
    def route(self):
        path=urlparse(self.path).path; query=parse_qs(urlparse(self.path).query)
        cellblock_files={'/downloads/cellblock.apk':('cellblock.apk','application/vnd.android.package-archive'),'/downloads/cellblock.apk.sha256':('cellblock.apk.sha256','text/plain'),'/downloads/cellblock-logo.webp':('logo.webp','image/webp'),'/downloads/cellblock-release.json':('release.json','application/json')}
        if self.command in ('GET','HEAD') and path in cellblock_files:
            name,mime=cellblock_files[path];file=ROOT/'static/cellblock'/name
            if not file.is_file():self.send({'error':'Cellblock release not installed'},404);return
            raw=file.read_bytes();self.send_response(200);self.headers_out(mime,len(raw))
            if path.endswith('.apk'):self.send_header('Content-Disposition','attachment; filename="CellblockCatAndMouse.apk"')
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
            return
        # SIP_DEVICE_INSTALL_V1
        if serve_sip(self,path):return
        if self.command in ('GET','HEAD') and path in ('/downloads/postmaster.apk','/downloads/postmaster.apk.sha256','/downloads/postmaster-logo.png','/downloads/postmaster-release.json'):
            names={'/downloads/postmaster.apk':'postmaster.apk','/downloads/postmaster.apk.sha256':'postmaster.apk.sha256','/downloads/postmaster-logo.png':'logo.png','/downloads/postmaster-release.json':'release.json'}
            file=ROOT/'static/postmaster'/names[path]
            if not file.is_file():self.send({'error':'Postmaster release not installed'},404);return
            raw=file.read_bytes();kind='application/vnd.android.package-archive' if path.endswith('.apk') else 'image/png' if path.endswith('.png') else 'application/json' if path.endswith('.json') else 'text/plain'
            self.send_response(200);self.headers_out(kind,len(raw))
            if path.endswith('.apk'):self.send_header('Content-Disposition','attachment; filename="postmaster.apk"')
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
            return
        if self.command in ('GET','HEAD') and path in ('/downloads/africa-credit.apk','/downloads/africa-credit.apk.sha256','/downloads/africa-credit-logo.png'):
            file=ROOT/'static/africacredit'/path.split('/')[-1]
            if not file.is_file():self.send({'error':'Africa Credit download not installed'},404);return
            raw=file.read_bytes()
            kind='application/vnd.android.package-archive' if path.endswith('.apk') else 'image/png' if path.endswith('.png') else 'text/plain'
            self.send_response(200);self.headers_out(kind,len(raw))
            if path.endswith('.apk'):self.send_header('Content-Disposition','attachment; filename="africa-credit.apk"')
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
            return
        aims_downloads={'/downloads/aims.apk':'aims.apk','/downloads/aims.apk.sha256':'aims.apk.sha256','/downloads/aims-logo.png':'logo.png'}
        if self.command in ('GET','HEAD') and path in aims_downloads:
            file=ROOT/'static/aims'/aims_downloads[path]
            if not file.is_file():self.send({'error':'AIMS download not installed'},404);return
            raw=file.read_bytes();kind='application/vnd.android.package-archive' if path.endswith('.apk') else 'image/png' if path.endswith('.png') else 'text/plain'
            self.send_response(200);self.headers_out(kind,len(raw))
            if path.endswith('.apk'):self.send_header('Content-Disposition','attachment; filename="AIMS.apk"')
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
            return
        justisolve_downloads={'/downloads/justisolve-preview.apk':'justisolve-preview.apk','/downloads/justisolve-preview.apk.sha256':'justisolve-preview.apk.sha256','/downloads/justisolve-release.json':'release.json','/downloads/justisolve-icon.png':'justisolve-icon.png'}
        if self.command in ('GET','HEAD') and path in justisolve_downloads:
            file=ROOT/'static/justisolve'/justisolve_downloads[path]
            if not file.is_file():self.send({'error':'JustiSolve download not installed'},404);return
            raw=file.read_bytes();kind='application/vnd.android.package-archive' if path.endswith('.apk') else 'image/png' if path.endswith('.png') else 'application/json' if path.endswith('.json') else 'text/plain'
            self.send_response(200);self.headers_out(kind,len(raw))
            if path.endswith('.apk'):self.send_header('Content-Disposition','attachment; filename="justisolve-preview.apk"')
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
            return
        hub_downloads={'/downloads/africa-bulk-hub.apk':'africa-bulk-hub.apk','/downloads/africa-bulk-hub.apk.sha256':'africa-bulk-hub.apk.sha256','/downloads/africa-bulk-hub-logo.png':'logo.png','/downloads/africa-bulk-hub-banner.png':'banner.png','/downloads/africa-bulk-hub-release.json':'release.json'}
        if self.command in ('GET','HEAD') and path in hub_downloads:
            file=ROOT/'static/afribulkhub'/hub_downloads[path]
            if not file.is_file():self.send({'error':'Africa Bulk Hub download not installed'},404);return
            raw=file.read_bytes();kind='application/vnd.android.package-archive' if path.endswith('.apk') else 'image/png' if path.endswith('.png') else 'application/json' if path.endswith('.json') else 'text/plain'
            self.send_response(200);self.headers_out(kind,len(raw))
            if path.endswith('.apk'):self.send_header('Content-Disposition','attachment; filename="africa-bulk-hub.apk"')
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
            return
        if self.command in ('GET','HEAD') and path in ('/downloads/africa-jobs.apk','/downloads/africa-jobs.apk.sha256','/downloads/africa-jobs-logo.png'):
            file=ROOT/'static/africajobs'/path.split('/')[-1]
            if not file.is_file(): self.send({'error':'Africa Jobs download not installed'},404); return
            kind='application/vnd.android.package-archive' if path.endswith('.apk') else 'image/png' if path.endswith('.png') else 'text/plain'
            raw=file.read_bytes(); self.send_response(200); self.headers_out(kind,len(raw))
            if path.endswith('.apk'): self.send_header('Content-Disposition','attachment; filename="africa-jobs.apk"')
            self.end_headers()
            if self.command!='HEAD': self.wfile.write(raw)
            return
        if self.command in ('GET','HEAD') and path in ('/','/copyright','/terms','/privacy','/static/app.js','/static/style.css','/static/logo.jpg','/static/africa-media-icon.svg'):
            file=ROOT/({'/':'templates/index.html','/copyright':'templates/copyright.html','/terms':'templates/terms.html','/privacy':'templates/privacy.html'}.get(path,path.lstrip('/'))); raw=file.read_bytes(); self.send_response(200); self.headers_out('text/html' if path in ('/','/copyright','/terms','/privacy') else 'text/javascript' if path.endswith('.js') else 'image/svg+xml' if path.endswith('.svg') else 'image/jpeg' if path.endswith('.jpg') else 'text/css',len(raw)); self.end_headers();
            if self.command!='HEAD': self.wfile.write(raw)
            return
        if self.command=='HEAD': self.send({'error':'Not found'},404); return
        with db() as c:
            cookies=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x)
            session=c.execute('SELECT sessions.*,users.name,users.email,users.role FROM sessions JOIN users ON users.id=user_id WHERE token=? AND expires>?',(cookies.get('session',''),time.time())).fetchone()
            uid=session['user_id'] if session else None
            body={}
            if self.command=='POST':
                length=int(self.headers.get('Content-Length','0'))
                if length<0: raise ValueError('Invalid content length')
                if length>25*1024*1024: self.send({'error':'Upload limit is 25 MiB'},413); return
                if path not in ('/api/login','/api/register') and (not session or not hmac.compare_digest(self.headers.get('X-CSRF',''),session['csrf'])): raise PermissionError('Sign in again or refresh the page')
                raw=self.rfile.read(length)
                if self.headers.get('Content-Type','').startswith('application/json'):
                    body=json.loads(raw)
                    if not isinstance(body,dict): raise ValueError('Expected a JSON object')
            def require(role=None):
                if not session or (role and session['role'] not in role):raise PermissionError('Access denied')
            def app(aid):
                a=c.execute('SELECT * FROM apps WHERE id=?',(aid,)).fetchone()
                if not a:raise ValueError('App not found')
                return a
            def owner(a):
                require()
                if a['owner']!=uid and session['role']!='admin':raise PermissionError('Access denied')
            if path=='/api/hosted-apps' and self.command=='GET':
                self.send([dict(json.loads(r['metadata']),visible=bool(r['visible'])) for r in c.execute('SELECT metadata,visible FROM hosted_apps WHERE visible=1 ORDER BY domain')]); return
            if path=='/api/admin/hosted-apps':
                require(['admin'])
                if self.command=='POST':
                    domain=str(body['domain']); visible=int(bool(body['visible']))
                    if not c.execute('SELECT 1 FROM hosted_apps WHERE domain=?',(domain,)).fetchone():raise ValueError('Unknown domain')
                    c.execute('UPDATE hosted_apps SET visible=?,updated=? WHERE domain=?',(visible,int(time.time()),domain))
                    c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(uid,'hosted visibility '+domain+' '+str(visible),int(time.time())))
                self.send([dict(json.loads(r['metadata']),visible=bool(r['visible'])) for r in c.execute('SELECT metadata,visible FROM hosted_apps ORDER BY domain')]);return
            if path=='/api/admin/users':
                require(['admin'])
                if self.command=='POST':
                    target=int(body['id']); role=body['role']
                    if role not in ('user','admin'):raise ValueError('Invalid role')
                    if target==uid and role!='admin':raise ValueError('Cannot remove your own administrator access')
                    if not c.execute('SELECT 1 FROM users WHERE id=?',(target,)).fetchone():raise ValueError('Unknown user')
                    c.execute('UPDATE users SET role=? WHERE id=?',(role,target))
                    c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
                    c.execute('INSERT INTO audit(actor,action,object_id,created) VALUES(?,?,?,?)',(uid,'set role '+role,target,int(time.time())))
                self.send([dict(r) for r in c.execute('SELECT id,email,name,role FROM users ORDER BY id LIMIT 500')]);return
            if path=='/api/admin/tickets' and self.command=='POST':
                require(['admin']); status=body['status']
                if status not in ('open','closed'):raise ValueError('Invalid status')
                target=int(body['id'])
                if not c.execute('SELECT 1 FROM tickets WHERE id=?',(target,)).fetchone():raise ValueError('Ticket not found')
                c.execute('UPDATE tickets SET status=? WHERE id=?',(status,target))
                c.execute('INSERT INTO audit(actor,action,object_id,created) VALUES(?,?,?,?)',(uid,'ticket '+status,target,int(time.time())))
                self.send({'ok':True});return
            if path=='/api/health': self.send({'status':'ok'}); return
            if path=='/api/me':self.send({k:session[k] for k in ('user_id','name','email','role','csrf')} if session else None); return
            if path in ('/api/register','/api/login') and self.command=='POST':
                email=str(body['email']).strip().lower(); pw=str(body['password'])
                if path.endswith('register'):
                    if len(pw)<12 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):raise ValueError('Valid email and password of 12+ characters required')
                    name=str(body['name']).strip()
                    if not name: raise ValueError('Full name is required')
                    c.execute('INSERT INTO users(email,name,password) VALUES(?,?,?)',(email,name[:100],password(pw)))
                u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                if not u or not hmac.compare_digest(password(pw,u['password'].split(':')[0]),u['password']):raise PermissionError('Invalid credentials')
                token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24); c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token,u['id'],csrf,int(time.time())+86400))
                self.send({'ok':True},cookie=f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'+ ('; Secure' if os.environ.get('COOKIE_SECURE')=='1' else '')); return
            if path=='/api/logout' and self.command=='POST':c.execute('DELETE FROM sessions WHERE token=?',(session['token'],)); self.send({'ok':True},cookie='session=; Path=/; Max-Age=0'); return
            if path=='/api/apps' and self.command=='GET':
                sql="SELECT apps.*,users.name developer,COALESCE((SELECT AVG(rating) FROM reviews WHERE app_id=apps.id),0) rating FROM apps JOIN users ON users.id=owner WHERE "
                mode=query.get('mode',[''])[0]; params=[]
                if mode=='mine': require(); sql+='owner=?'; params=[uid]
                elif mode=='moderate':require(['admin']); sql+='1=1'
                elif mode in ('wishlist','library'):
                    require(); sql+=f"status='published' AND apps.id IN (SELECT app_id FROM {mode} WHERE user_id=?)"; params=[uid]
                else:sql+="status='published'"
                q=query.get('q',[''])[0]; sql+=' AND (apps.name LIKE ? OR description LIKE ? OR users.name LIKE ?)'; params+=['%'+q+'%']*3
                kind=query.get('kind',[''])[0]
                if kind:sql+=' AND kind=?';params.append(kind)
                category=query.get('category',[''])[0]
                if category:sql+=' AND category=?';params.append(category)
                sql+=' ORDER BY '+('downloads DESC' if query.get('sort',[''])[0]=='popular' else 'created DESC')+' LIMIT 200'
                self.send([dict(a) for a in c.execute(sql,params)]);return
            if path=='/api/apps' and self.command=='POST':
                require(); package=str(body['package'])
                if not re.fullmatch(r'[A-Za-z]\w*(\.[A-Za-z]\w*)+',package):raise ValueError('Invalid Android package name')
                if body['kind'] not in ('Apps','Games','Books'):raise ValueError('Invalid content type')
                privacy=str(body['privacy'])
                if urlparse(privacy).scheme!='https' or not urlparse(privacy).hostname:raise ValueError('Valid HTTPS privacy policy required')
                for key in ('name','category','description','version'):
                    if not str(body[key]).strip(): raise ValueError(key.capitalize()+' is required')
                if not 0<=int(body.get('age',3))<=18: raise ValueError('Minimum age must be between 0 and 18')
                cur=c.execute('INSERT INTO apps(owner,name,package,kind,category,description,version,age,privacy,created) VALUES(?,?,?,?,?,?,?,?,?,?)',(uid,str(body['name'])[:100],package,body['kind'],str(body['category'])[:80],str(body['description'])[:20000],str(body['version'])[:50],int(body.get('age',3)),privacy,int(time.time())))
                self.send({'id':cur.lastrowid}); return
            m=re.fullmatch(r'/api/apps/(\d+)(?:/(\w+))?',path)
            if m:
                aid=int(m[1]); action=m[2]; a=app(aid)
                if a['status']!='published': owner(a)
                if self.command=='GET' and not action:
                    out=dict(a);out['reviews']=[dict(r) for r in c.execute('SELECT reviews.*,users.name FROM reviews JOIN users ON users.id=user_id WHERE app_id=?',(aid,))];out['releases']=[dict(r) for r in c.execute('SELECT id,app_id,sha256,size,created FROM releases WHERE app_id=? ORDER BY id DESC',(aid,))];self.send(out);return
                if self.command=='GET' and action=='download':
                    require()
                    if a['status']!='published':raise PermissionError('App is not published')
                    r=c.execute('SELECT * FROM releases WHERE app_id=? ORDER BY id DESC LIMIT 1',(aid,)).fetchone()
                    if not r:raise ValueError('No APK available')
                    raw=(DATA/r['filename']).read_bytes(); c.execute('INSERT OR IGNORE INTO library VALUES(?,?)',(uid,aid)); c.execute('UPDATE apps SET downloads=downloads+1 WHERE id=?',(aid,));self.send_response(200);self.headers_out('application/vnd.android.package-archive',len(raw));self.send_header('Content-Disposition',f'attachment; filename="{a["package"]}.apk"');self.end_headers();self.wfile.write(raw);return
                if self.command!='POST':self.send({'error':'Not found'},404);return
                require()
                if action=='upload':
                    owner(a)
                    if not raw.startswith(b'PK'):raise ValueError('Expected APK ZIP container')
                    import zipfile,io
                    with zipfile.ZipFile(io.BytesIO(raw)) as z:
                        if 'AndroidManifest.xml' not in z.namelist():raise ValueError('APK manifest missing')
                    digest=hashlib.sha256(raw).hexdigest();name=secrets.token_hex(20)+'.apk';(DATA/name).write_bytes(raw)
                    c.execute('INSERT INTO releases(app_id,filename,sha256,size,created) VALUES(?,?,?,?,?)',(aid,name,digest,len(raw),int(time.time())));c.execute("UPDATE apps SET status='draft' WHERE id=?",(aid,))
                elif action=='submit':
                    owner(a)
                    if not c.execute('SELECT 1 FROM releases WHERE app_id=?',(aid,)).fetchone():raise ValueError('Upload an APK before submission')
                    c.execute("UPDATE apps SET status='pending' WHERE id=?",(aid,))
                elif action=='moderate':
                    require(['admin']);status=body['status']
                    if status not in ('published','rejected','suspended'):raise ValueError('Invalid status')
                    if status=='published' and a['status']!='pending':raise ValueError('Only pending submissions can be published')
                    c.execute('UPDATE apps SET status=? WHERE id=?',(status,aid));c.execute('INSERT INTO audit(actor,action,object_id,created) VALUES(?,?,?,?)',(uid,status,aid,int(time.time())))
                elif action=='wishlist':
                    if c.execute('SELECT 1 FROM wishlist WHERE user_id=? AND app_id=?',(uid,aid)).fetchone():c.execute('DELETE FROM wishlist WHERE user_id=? AND app_id=?',(uid,aid))
                    else:c.execute('INSERT INTO wishlist VALUES(?,?)',(uid,aid))
                elif action=='review':
                    if not c.execute('SELECT 1 FROM library WHERE user_id=? AND app_id=?',(uid,aid)).fetchone():raise PermissionError('Download the app before reviewing')
                    c.execute('INSERT INTO reviews(user_id,app_id,rating,body) VALUES(?,?,?,?) ON CONFLICT(user_id,app_id) DO UPDATE SET rating=excluded.rating,body=excluded.body',(uid,aid,int(body['rating']),str(body['body'])[:4000]))
                elif action=='delete_review':c.execute('DELETE FROM reviews WHERE user_id=? AND app_id=?',(uid,aid))
                elif action=='reply':owner(a);c.execute('UPDATE reviews SET reply=? WHERE id=? AND app_id=?',(str(body['reply'])[:4000],int(body['review_id']),aid))
                elif action=='report':c.execute('INSERT INTO reports(user_id,app_id,reason) VALUES(?,?,?)',(uid,aid,str(body['reason'])[:4000]))
                elif action in ('beta','preregister'):
                    if body.get('leave'):c.execute('DELETE FROM memberships WHERE user_id=? AND app_id=? AND kind=?',(uid,aid,action))
                    else:c.execute('INSERT OR IGNORE INTO memberships VALUES(?,?,?)',(uid,aid,action))
                else:raise ValueError('Unknown action')
                self.send({'ok':True});return
            if path=='/api/settings':
                require()
                if self.command=='POST':c.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET value=excluded.value',(uid,json.dumps(body)))
                r=c.execute('SELECT value FROM settings WHERE user_id=?',(uid,)).fetchone();self.send(json.loads(r[0]) if r else {});return
            if path=='/api/tickets':
                require()
                if self.command=='POST':c.execute('INSERT INTO tickets(user_id,subject,body) VALUES(?,?,?)',(uid,str(body['subject'])[:200],str(body['body'])[:5000]))
                self.send([dict(t) for t in c.execute('SELECT * FROM tickets WHERE user_id=?',(uid,))]);return
            if path=='/api/admin':
                require(['admin']);self.send({t:[dict(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY id DESC LIMIT 200')] for t in ('reports','tickets','audit')});return
            self.send({'error':'Not found'},404)
if __name__=='__main__':
    init(); ThreadingHTTPServer((os.environ.get('BIND','127.0.0.1'),int(os.environ.get('PORT','8080'))),Handler).serve_forever()


