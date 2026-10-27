import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('epa',Path(__file__).parents[1]/'tools/install_epa.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ListingTests(unittest.TestCase):
 def test_upsert_preserves_other_apps_and_existing_visibility(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'store.sqlite3'
   with sqlite3.connect(db) as c:
    c.execute('CREATE TABLE hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT,visible INTEGER DEFAULT 1,updated INTEGER)')
    c.execute('INSERT INTO hosted_apps VALUES(?,?,?,?)',('other.example','{}',1,1))
   m.install(db,state=Path(tmp)/'backups')
   with sqlite3.connect(db) as c:c.execute('UPDATE hosted_apps SET visible=0 WHERE domain=?',(m.DOMAIN,))
   m.install(db,state=Path(tmp)/'backups')
   with sqlite3.connect(db) as c:
    self.assertEqual(c.execute('SELECT COUNT(*) FROM hosted_apps').fetchone()[0],2)
    row=c.execute('SELECT metadata,visible FROM hosted_apps WHERE domain=?',(m.DOMAIN,)).fetchone()
    self.assertIsNone(json.loads(row[0])['apk_url']);self.assertEqual(row[1],0)
 def test_ui_patch_is_idempotent(self):
  text=(Path(__file__).parents[1]/'static/app.js').read_text()
  self.assertEqual(m.frontend(text),text)
  self.assertIn('epafestival.africandroid.world',text)
  self.assertGreater(text.find("a.domain==='epafestival.africandroid.world'"),text.find('async function hostedCards'))

class DiscoveryTests(unittest.TestCase):
 def test_effective_process_environment_takes_precedence(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);code=root/'live';(code/'static').mkdir(parents=True);(code/'static/app.js').write_text('')
   proc=root/'proc';(proc/'123').mkdir(parents=True);(proc/'123/cwd').symlink_to(code)
   (proc/'123/environ').write_bytes(b'STORE_DATA=/correct/runtime-data\0PORT=18888\0PRIVATE_SECRET=must-not-print\0')
   props={'WorkingDirectory':str(code),'MainPID':'123','Environment':'STORE_DATA=/wrong PORT=8080'}
   database,resolved,port=m.discover(props.get,proc)
   self.assertEqual(str(database),'/correct/runtime-data/store.sqlite3');self.assertEqual(port,18888);self.assertEqual(resolved,code)
 def test_explicit_publish_changes_only_epa_visibility(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'store.sqlite3'
   with sqlite3.connect(db) as c:
    c.execute('CREATE TABLE hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT,visible INTEGER DEFAULT 1,updated INTEGER)')
    c.execute('INSERT INTO hosted_apps VALUES(?,?,?,?)',('other.example','{}',0,1))
   m.install(db,state=Path(tmp)/'backups',publish=True)
   with sqlite3.connect(db) as c:
    self.assertEqual(c.execute('SELECT visible FROM hosted_apps WHERE domain=?',(m.DOMAIN,)).fetchone()[0],1)
    self.assertEqual(c.execute('SELECT visible FROM hosted_apps WHERE domain=?',('other.example',)).fetchone()[0],0)

if __name__=='__main__':unittest.main()
