"""Regression: a local store copy must not be mistaken for the public host."""
import contextlib,io,json,socket,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
GUARD=(ROOT/'scripts/publish-kakakin.sh').read_text().split("python3 - <<'PY'\n",1)[1].split('\nPY\n',1)[0]
class StoreHostGuardTests(unittest.TestCase):
 def guard(self,dns,local):
  resolved=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in dns]
  interfaces=json.dumps([{'addr_info':[{'local':ip} for ip in local]}])
  with patch('socket.getaddrinfo',return_value=resolved),patch('subprocess.check_output',return_value=interfaces),contextlib.redirect_stdout(io.StringIO()):exec(compile(GUARD,'store-host-guard','exec'),{})
 def test_rejects_kakakin_machine_for_store_domain(self):
  with self.assertRaisesRegex(SystemExit,'181.214.149.146'):self.guard(['181.214.149.146'],['154.16.170.86','127.0.0.1'])
 def test_accepts_actual_store_host(self):self.guard(['181.214.149.146'],['181.214.149.146','127.0.0.1'])
 def test_does_not_ignore_mismatched_second_address(self):
  with self.assertRaises(SystemExit):self.guard(['181.214.149.146','154.16.170.86'],['181.214.149.146'])
