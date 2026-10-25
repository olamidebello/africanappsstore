#!/usr/bin/env python3
import argparse,json,sqlite3,time
from pathlib import Path
INFO={'domain':'sip.dobhrap.com','name':'Olamide SIP','category':'Communication','package':'com.dobhrap.olamide','artifact_kind':'olamide-sip-native','website':'https://sip.dobhrap.com/','install_url':'https://africanappsstore.space/install/sip','description':'Calling, messaging and voicemail with device-aware install and update downloads.','features':['Dedicated Android SIP app','Windows, Linux and Apple Silicon macOS previews','iPhone and iPad browser installation','Device detection with manual platform choice','Check published downloads for updates'],'limitations':'Android is a development APK; desktop previews are unsigned. Native iOS distribution and background push require signing and provider configuration. Browser features depend on device support.','platforms':'Android · iPhone/iPad web app · Windows x64 · Linux x64 · macOS arm64','apk_url':None,'download_status':'device_install_page'}
def install(database):
 with sqlite3.connect(database) as c:
  c.execute('INSERT INTO hosted_apps(domain,metadata,updated) VALUES(?,?,?) ON CONFLICT(domain) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',(INFO['domain'],json.dumps(INFO),int(time.time())))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--database',required=True);install(p.parse_args().database)
