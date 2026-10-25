import importlib.util,json,os,sqlite3,tempfile,threading,unittest,urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class PostmasterStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();old=os.environ.get('STORE_DATA');os.environ['STORE_DATA']=cls.temp.name
        cls.app=module('store_release_under_test',ROOT/'app.py')
        if old is None:os.environ.pop('STORE_DATA',None)
        else:os.environ['STORE_DATA']=old
        cls.app.init();cls.install=module('hub_listing_under_test',ROOT/'tools/install_postmaster.py')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),cls.app.Handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
    def test_public_apk_head_and_logo(self):
        for path in ['/downloads/postmaster.apk','/downloads/postmaster-logo.png','/downloads/postmaster.apk.sha256']:
            with urllib.request.urlopen(urllib.request.Request(self.url+path,method='HEAD')) as response:self.assertEqual(response.status,200);self.assertGreater(int(response.headers['Content-Length']),10);self.assertEqual(response.read(),b'')
        with urllib.request.urlopen(self.url+'/downloads/postmaster.apk') as response:self.assertTrue(response.read(2)==b'PK')
    def test_listing_preserves_existing_visibility_and_other_apps(self):
        with sqlite3.connect(self.app.DB) as c:c.execute('INSERT OR IGNORE INTO hosted_apps(domain,metadata,updated) VALUES (?,?,?)',('unrelated.example',json.dumps({'name':'Keep me'}),1))
        self.install.install(self.app.DB,ROOT/'static/postmaster')
        with sqlite3.connect(self.app.DB) as c:
            record=json.loads(c.execute('SELECT metadata FROM hosted_apps WHERE domain=?',('postmaster.justisolve.com',)).fetchone()[0]);self.assertEqual(record['package'],'com.justisolve.postmaster')
            self.assertEqual(c.execute('SELECT COUNT(*) FROM hosted_apps WHERE domain=?',('unrelated.example',)).fetchone()[0],1)
            c.execute('UPDATE hosted_apps SET visible=0 WHERE domain=?',('postmaster.justisolve.com',))
        self.install.install(self.app.DB,ROOT/'static/postmaster')
        with sqlite3.connect(self.app.DB) as c:self.assertEqual(c.execute('SELECT visible FROM hosted_apps WHERE domain=?',('postmaster.justisolve.com',)).fetchone()[0],0)
