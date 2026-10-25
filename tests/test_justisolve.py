import importlib.util,json,os,sqlite3,tempfile,threading,unittest,urllib.request,hashlib,shutil
from http.server import ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class JustiSolveReleaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();old=os.environ.get('STORE_DATA');os.environ['STORE_DATA']=cls.temp.name;cls.app=module('justisolve_store_under_test',ROOT/'app.py')
  if old is None:os.environ.pop('STORE_DATA',None)
  else:os.environ['STORE_DATA']=old
  cls.app.init();cls.installer=module('justisolve_install_under_test',ROOT/'tools/install_justisolve.py');cls.sync=module('justisolve_sync_under_test',ROOT/'tools/sync_hosted_catalog.py')
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),cls.app.Handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
 def test_apk_get_head_mime_and_checksum(self):
  apk=ROOT/'static/justisolve/justisolve-preview.apk';expected=hashlib.sha256(apk.read_bytes()).hexdigest()
  with urllib.request.urlopen(urllib.request.Request(self.url+'/downloads/justisolve-preview.apk',method='HEAD')) as response:
   self.assertEqual(response.status,200);self.assertEqual(response.headers['Content-Type'],'application/vnd.android.package-archive');self.assertEqual(int(response.headers['Content-Length']),apk.stat().st_size);self.assertEqual(response.read(),b'')
  with urllib.request.urlopen(self.url+'/downloads/justisolve-preview.apk') as response:self.assertEqual(hashlib.sha256(response.read()).hexdigest(),expected)
  with urllib.request.urlopen(self.url+'/downloads/justisolve-preview.apk.sha256') as response:self.assertEqual(response.read().decode().split()[0],expected)
 def test_listing_preserves_visibility_and_survives_generic_sync(self):
  self.installer.install(self.app.DB,ROOT/'static/justisolve')
  with sqlite3.connect(self.app.DB) as c:c.execute("UPDATE hosted_apps SET visible=0 WHERE domain='justisolve.com'")
  self.sync.synchronize(self.app.DB,ROOT/'mobile/fleet/apps.json',Path(self.temp.name)/'missing-downloads')
  self.installer.install(self.app.DB,ROOT/'static/justisolve')
  with sqlite3.connect(self.app.DB) as c:
   metadata,visible=c.execute("SELECT metadata,visible FROM hosted_apps WHERE domain='justisolve.com'").fetchone();record=json.loads(metadata);self.assertEqual(visible,0);self.assertEqual(record['artifact_kind'],'justisolve-preview');self.assertEqual(record['install_url'],'https://justisolve.com/install');self.assertEqual(record['package'],'com.justisolve.mobile.preview');self.assertIn('preview',record['limitations'].lower())
 def test_tampered_apk_cannot_update_listing(self):
  with tempfile.TemporaryDirectory() as tmp:
   static=Path(tmp);shutil.copytree(ROOT/'static/justisolve',static,dirs_exist_ok=True);(static/'justisolve-preview.apk').write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'checksum'):self.installer.install(self.app.DB,static)
