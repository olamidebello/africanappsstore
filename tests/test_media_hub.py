import importlib.util,json,sqlite3,tempfile,unittest
from unittest.mock import patch
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
   release=json.loads((ROOT/'static/media/release.json').read_text())
   with patch.object(listing,'ensure_package',return_value=release):listing.install(database)
   with sqlite3.connect(database) as c:
    metadata=json.loads(c.execute("SELECT metadata FROM hosted_apps WHERE domain='media.africandroid.world'").fetchone()[0]);self.assertEqual(metadata['apk_url'],'https://africanappsstore.space/downloads/africa-media-android-debug.apk');self.assertEqual(metadata['install_url'],'https://media.africandroid.world/install');c.execute("UPDATE hosted_apps SET visible=0 WHERE domain='media.africandroid.world'")
   with patch.object(listing,'ensure_package',return_value=release):listing.install(database)
   with sqlite3.connect(database) as c:
    self.assertEqual(c.execute('SELECT count(*) FROM hosted_apps').fetchone()[0],2)
    self.assertEqual(c.execute("SELECT visible FROM hosted_apps WHERE domain='media.africandroid.world'").fetchone()[0],0)

 def test_pinned_archive_and_apk_checksums(self):
  import io,hashlib,zipfile
  release=json.loads((ROOT/'static/media/release.json').read_text())
  zip_path=Path('/tmp/africa-media-phone-tv.zip')
  if not zip_path.is_file():self.skipTest('Verified workflow archive not available locally')
  archive=zip_path.read_bytes()
  self.assertEqual(hashlib.sha256(archive).hexdigest(),release['artifact_sha256'])
  class Response(io.BytesIO):
   def __enter__(self):return self
   def __exit__(self,*args):self.close()
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(listing.urllib.request,'urlopen',return_value=Response(archive)):
    listing.ensure_package(Path(folder))
   apk=Path(folder)/'africa-media-android-debug.apk'
   self.assertEqual(apk.stat().st_size,release['size_bytes'])
   self.assertEqual(hashlib.sha256(apk.read_bytes()).hexdigest(),release['sha256'])
   with patch.object(listing.urllib.request,'urlopen',side_effect=AssertionError('unexpected redownload')):
    listing.ensure_package(Path(folder))
 def test_existing_verified_apk_permissions_are_repaired(self):
  import hashlib,os
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);static=root/'static/media';static.mkdir(parents=True);apk=static/'africa-media-android-debug.apk';raw=b'verified fixture';apk.write_bytes(raw);apk.chmod(0o600);static.chmod(0o700)
   release={'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
   (static/'release.json').write_text(json.dumps(release));(static/'africa-media-android-debug.apk.sha256').write_text(release['sha256']+'  '+apk.name)
   with patch.object(listing,'ROOT',root),patch.object(listing.urllib.request,'urlopen',side_effect=AssertionError('unexpected download')):
    listing.ensure_package(static)
   self.assertEqual(apk.stat().st_mode&0o777,0o644)
   self.assertEqual(static.stat().st_mode&0o777,0o755)
