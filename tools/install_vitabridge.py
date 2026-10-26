#!/usr/bin/env python3
import argparse,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database):
 if not Path(database).is_file():raise ValueError('Existing store database missing')
 metadata=json.loads((ROOT/'catalog/vitabridge.json').read_text())
 with sqlite3.connect(database) as c:
  c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(metadata['domain'],json.dumps(metadata),int(time.time())))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--database',required=True);a=p.parse_args();install(a.database)
