#!/usr/bin/env python3
"""Upsert the Media Hub listing without changing other apps or visibility."""
import argparse,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install(database):
    database=Path(database)
    if not database.is_file():raise ValueError('Existing store database not found')
    metadata=json.loads((ROOT/'catalog/africa-media-hub.json').read_text())
    if metadata['domain']!='media.africandroid.world' or metadata['apk_url'] is not None:raise ValueError('Unexpected Media Hub listing')
    with sqlite3.connect(database) as c:
        c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(metadata['domain'],json.dumps(metadata),int(time.time())))
    print('Africa Media Hub listing installed with website and device installation page')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',required=True,type=Path);args=parser.parse_args();install(args.database)
