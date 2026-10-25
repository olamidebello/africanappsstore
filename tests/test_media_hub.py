import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('media_listing',ROOT/'tools/install_media_hub.py');listing=importlib.util.module_from_spec(spec);spec.loader.exec_module(listing)
class MediaHubListing(unittest.TestCase):
 def test_upsert_preserves_other_apps_and_admin_visibility(self):
  with tempfile.TemporaryDirectory() as temp:
   database=Path(temp)/'store.db'
   with sqlite3.connect(database) as c:
    c.execute('CREATE TABLE hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT NOT NULL,visible INTEGER DEFAULT 1,updated INTEGER)')
    c.execute("INSERT INTO hosted_apps VALUES('other.example','{}',1,0)")
   listing.install(database)
   with sqlite3.connect(database) as c:
    metadata=json.loads(c.execute("SELECT metadata FROM hosted_apps WHERE domain='media.africandroid.world'").fetchone()[0]);self.assertIsNone(metadata['apk_url']);self.assertEqual(metadata['install_url'],'https://media.africandroid.world/install');c.execute("UPDATE hosted_apps SET visible=0 WHERE domain='media.africandroid.world'")
   listing.install(database)
   with sqlite3.connect(database) as c:
    self.assertEqual(c.execute('SELECT count(*) FROM hosted_apps').fetchone()[0],2)
    self.assertEqual(c.execute("SELECT visible FROM hosted_apps WHERE domain='media.africandroid.world'").fetchone()[0],0)
