import sys,tempfile,sqlite3,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from sip_downloads import integrate_app,integrate_cards
from install_sip import install
class SipTests(unittest.TestCase):
 def test_router_and_cards_are_idempotent(self):
  for source,fn in [(ROOT/'app.py',integrate_app),(ROOT/'static/app.js',integrate_cards)]:
   text=source.read_text();self.assertEqual(fn(fn(text)),fn(text))
 def test_catalog_preserves_hidden_listing_and_other_apps(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'store.sqlite3'
   with sqlite3.connect(db) as c:
    c.execute('CREATE TABLE hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT,visible INTEGER DEFAULT 1,updated INTEGER)');c.execute('INSERT INTO hosted_apps VALUES(?,?,?,?)',('sip.dobhrap.com','{}',0,0));c.execute('INSERT INTO hosted_apps VALUES(?,?,?,?)',('other.example','{}',1,0))
   install(db)
   with sqlite3.connect(db) as c:
    r=c.execute("SELECT metadata,visible FROM hosted_apps WHERE domain='sip.dobhrap.com'").fetchone();self.assertEqual(r[1],0);self.assertEqual(json.loads(r[0])['artifact_kind'],'olamide-sip-native');self.assertEqual(c.execute('SELECT COUNT(*) FROM hosted_apps').fetchone()[0],2)
