import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BrowserListingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'store.sqlite3'
        with sqlite3.connect(self.db) as c:
            c.execute('CREATE TABLE hosted_apps(domain TEXT PRIMARY KEY,metadata TEXT,visible INTEGER DEFAULT 1,updated INTEGER)')
            c.execute('INSERT INTO hosted_apps VALUES(?,?,?,?)', ('africanbrowser.com', '{}', 0, 1))
            c.execute('INSERT INTO hosted_apps VALUES(?,?,?,?)', ('example.org', '{"name":"Keep"}', 1, 1))
        self.apk = self.root / 'downloads/android-123/AfricanBrowser.apk'
        self.apk.parent.mkdir(parents=True)
        with zipfile.ZipFile(self.apk, 'w') as z:
            for name in ('AndroidManifest.xml', 'classes.dex', 'lib/arm64-v8a/libchrome.so'):
                z.writestr(name, b'fixture')
        self.info = dict(apk='downloads/android-123/AfricanBrowser.apk', source='a' * 40,
                         sha256=hashlib.sha256(self.apk.read_bytes()).hexdigest())
        (self.root / 'deployment.json').write_text(json.dumps(self.info))
        self.installer = load('install_africanbrowser')

    def test_install_preserves_visibility_other_records_and_fleet_sync(self):
        response = MagicMock(status=200, headers={'Content-Length': str(self.apk.stat().st_size)})
        response.__enter__.return_value = response
        with patch.object(self.installer.urllib.request, 'urlopen', return_value=response):
            self.installer.install(self.db, self.root)
        manifest = self.root / 'apps.json'
        manifest.write_text(json.dumps([dict(domain='africanbrowser.com', slug='africanbrowser-com',
                                            name='Wrapper', category='Tools', package='wrapper', url='https://africanbrowser.com')]))
        load('sync_hosted_catalog').synchronize(self.db, manifest, self.root / 'missing')
        with sqlite3.connect(self.db) as c:
            metadata, visible = c.execute('SELECT metadata,visible FROM hosted_apps WHERE domain=?', ('africanbrowser.com',)).fetchone()
            self.assertEqual(visible, 0)
            self.assertEqual(json.loads(metadata)['package'], 'org.africanbrowser.browser')
            self.assertEqual(c.execute('SELECT metadata FROM hosted_apps WHERE domain=?', ('example.org',)).fetchone()[0], '{"name":"Keep"}')
        self.assertEqual(len(list(self.root.glob('store.sqlite3.before-*'))), 1)

    def test_corrupt_apk_leaves_database_untouched(self):
        self.apk.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.installer.install(self.db, self.root)
        with sqlite3.connect(self.db) as c:
            self.assertEqual(c.execute('SELECT metadata FROM hosted_apps WHERE domain=?', ('africanbrowser.com',)).fetchone()[0], '{}')
        self.assertEqual(list(self.root.glob('store.sqlite3.before-*')), [])

    def test_invalid_path_is_rejected(self):
        self.info['apk'] = '../outside.apk'
        (self.root / 'deployment.json').write_text(json.dumps(self.info))
        with self.assertRaisesRegex(ValueError, 'path'):
            self.installer.install(self.db, self.root)
