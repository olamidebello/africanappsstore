import unittest,tempfile,sqlite3,json,sys,threading,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from install_cellblock import install
import app
class CellblockMobileTests(unittest.TestCase):
 def test_verified_listing_and_public_downloads(self):
  with tempfile.TemporaryDirectory() as t:
   old=app.DB;app.DB=Path(t)/'store.sqlite3';app.init();install(app.DB);install(app.DB)
   with sqlite3.connect(app.DB) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM hosted_apps WHERE domain=?',('cellblockcatandmouse.africandroid.world',)).fetchone()[0],1)
   h=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=h.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(h.server_port)
   try:
    with urllib.request.urlopen(base+'/api/hosted-apps') as r:self.assertEqual(json.load(r)[0]['name'],'Cellblock Cat & Mouse')
    for path in ['/downloads/cellblock.apk','/downloads/cellblock-logo.webp','/downloads/cellblock-release.json']:
     with urllib.request.urlopen(urllib.request.Request(base+path,method='HEAD')) as r:self.assertEqual(r.status,200);self.assertGreater(int(r.headers['Content-Length']),0)
   finally:h.shutdown();h.server_close();app.DB=old
