import hashlib,importlib.util,json,sqlite3,sys,tempfile,threading,types,unittest,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class EffortlessTests(unittest.TestCase):
 def test_verified_catalog_and_download(self):
  stub=types.ModuleType('sip_downloads');stub.serve_sip=lambda *args:False;sys.modules.setdefault('sip_downloads',stub)
  spec=importlib.util.spec_from_file_location('store',ROOT/'app.py');store=importlib.util.module_from_spec(spec);spec.loader.exec_module(store)
  spec=importlib.util.spec_from_file_location('installer',ROOT/'tools/install_effortlesssmiles.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
  with tempfile.TemporaryDirectory() as temp:
   store.DB=Path(temp)/'store.sqlite3';store.init()
   with sqlite3.connect(store.DB) as c:
    c.execute('INSERT INTO hosted_apps VALUES (?,?,?,?)',('effortlesssmiles.afribulkhub.com','{}',0,0))
    c.execute('INSERT INTO hosted_apps VALUES (?,?,?,?)',('unrelated.example','{"preserved":true}',1,0))
   result=installer.install(store.DB);self.assertFalse(result['visible'])
   with sqlite3.connect(store.DB) as c:
    self.assertEqual(c.execute("SELECT metadata FROM hosted_apps WHERE domain='unrelated.example'").fetchone()[0],'{"preserved":true}')
    c.execute("UPDATE hosted_apps SET visible=1 WHERE domain='effortlesssmiles.afribulkhub.com'")
   server=store.ThreadingHTTPServer(('127.0.0.1',0),store.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
   try:
    with urllib.request.urlopen(urllib.request.Request(base+'/downloads/effortless-smiles-preview.apk',method='HEAD')) as r:self.assertEqual(r.headers['Content-Type'],'application/vnd.android.package-archive')
    with urllib.request.urlopen(base+'/downloads/effortless-smiles-preview.apk') as r:self.assertEqual(hashlib.sha256(r.read()).hexdigest(),result['sha256'])
    with urllib.request.urlopen(base+'/api/hosted-apps') as r:rows=json.load(r)
    listing=next(x for x in rows if x['domain']=='effortlesssmiles.afribulkhub.com');self.assertFalse(listing['demo_payments_enabled']);self.assertFalse(listing['demo_purchases_enabled'])
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
