import hashlib,importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('catalog_sync',Path(__file__).resolve().parents[1]/'tools/sync_hosted_catalog.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class CatalogSyncTests(unittest.TestCase):
 def test_verified_downloads_and_visibility_survive_sync(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);manifest=root/'apps.json';database=root/'store.db';downloads=root/'downloads';domain='example.com';slug='example-com'
   manifest.write_text(json.dumps([dict(domain=domain,slug=slug,name='Example',category='Tools',package='world.example.app',url='https://example.com/')]))
   module.synchronize(database,manifest,downloads)
   with sqlite3.connect(database) as c:
    row=c.execute('SELECT metadata FROM hosted_apps').fetchone();self.assertIsNone(json.loads(row[0])['apk_url']);c.execute('UPDATE hosted_apps SET visible=0')
   folder=downloads/domain;folder.mkdir(parents=True);apk=folder/(slug+'.apk');apk.write_bytes(b'verified-build-fixture');checksum=hashlib.sha256(apk.read_bytes()).hexdigest();apk.with_name(apk.name+'.sha256').write_text(checksum+'  '+apk.name)
   module.synchronize(database,manifest,downloads)
   with sqlite3.connect(database) as c:
    row=c.execute('SELECT metadata,visible FROM hosted_apps').fetchone();self.assertEqual(row[1],0);self.assertTrue(json.loads(row[0])['apk_url'])
   apk.write_bytes(b'tampered')
   with self.assertRaises(ValueError):module.synchronize(database,manifest,downloads)
