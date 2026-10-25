import unittest,tempfile,sqlite3,json,threading,urllib.request,hashlib
from pathlib import Path
import os,importlib.util
from tools.install_aims import install,ROOT
from tools.sync_hosted_catalog import synchronize
class AIMSMobileTest(unittest.TestCase):
 def test_checksum_and_visibility(self):
  with tempfile.TemporaryDirectory() as t:
   db=Path(t)/'store.sqlite3'
   with sqlite3.connect(db) as c:
    c.execute('CREATE TABLE hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT,visible INTEGER DEFAULT 1,updated INTEGER)')
    c.executemany('INSERT INTO hosted_apps VALUES(?,?,?,0)',[('unrelated.test','{}',1),('identity.africandroid.world','{}',0)])
   install(db,ROOT/'static/aims')
   with sqlite3.connect(db) as c:
    self.assertEqual(c.execute('SELECT COUNT(*) FROM hosted_apps').fetchone()[0],2)
    self.assertEqual(c.execute("SELECT visible FROM hosted_apps WHERE domain='identity.africandroid.world'").fetchone()[0],0)
    info=json.loads(c.execute("SELECT metadata FROM hosted_apps WHERE domain='identity.africandroid.world'").fetchone()[0]);self.assertEqual(info['download_status'],'available')
   manifest=Path(t)/'apps.json';manifest.write_text(json.dumps([{'domain':'identity.africandroid.world','slug':'identity-africandroid-world','name':'generic','category':'Tools','package':'generic.test','url':'https://identity.africandroid.world/'}]))
   synchronize(db,manifest,Path(t)/'no-downloads')
   with sqlite3.connect(db) as c:self.assertEqual(json.loads(c.execute("SELECT metadata FROM hosted_apps WHERE domain='identity.africandroid.world'").fetchone()[0])['artifact_kind'],'aims-android-client')
 def test_public_download(self):
  tmp=tempfile.TemporaryDirectory();old=os.environ.get('STORE_DATA');os.environ['STORE_DATA']=tmp.name
  spec=importlib.util.spec_from_file_location('aims_store_test',ROOT/'app.py');app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
  if old is None:os.environ.pop('STORE_DATA',None)
  else:os.environ['STORE_DATA']=old
  app.init();server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   base='http://127.0.0.1:'+str(server.server_port)
   for route in ['/downloads/aims.apk','/downloads/aims.apk.sha256','/downloads/aims-logo.png']:
    with urllib.request.urlopen(base+route) as r:raw=r.read();self.assertEqual(r.status,200)
    with urllib.request.urlopen(urllib.request.Request(base+route,method='HEAD')) as r:self.assertEqual(int(r.headers['Content-Length']),len(raw));self.assertEqual(r.read(),b'')
  finally:server.shutdown();server.server_close();tmp.cleanup()
