#!/usr/bin/env python3
"""Conservative DRockRadio database auditor.

No database record is changed unless --apply is supplied AND a candidate meets
all safety rules. By default the script only writes an audit report.
"""
import argparse, hashlib, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "stations.json"
REPORT = ROOT / "data" / "audit-report.json"
HISTORY = ROOT / "data" / "health-history.json"
API = "https://de1.api.radio-browser.info"
UA = "DRockRadio-Database-Maintenance/1.0"
TIMEOUT = 8


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def get_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8'))


def stream_ok(url):
    if not url:
        return False
    try:
        req = Request(url, headers={"User-Agent": UA, "Icy-MetaData": "1"})
        with urlopen(req, timeout=TIMEOUT) as r:
            chunk = r.read(4096)
            return bool(chunk)
    except Exception:
        return False


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def similarity(a,b):
    aa=set(norm(a).split()); bb=set(norm(b).split())
    if not aa or not bb: return 0.0
    return 2*len(aa&bb)/(len(aa)+len(bb))


def candidates(st):
    name = quote(st['Name'])
    url = f"{API}/json/stations/search?name={name}&limit=20&hidebroken=true"
    rows = get_json(url)
    out=[]
    for x in rows:
        score=similarity(st['Name'],x.get('name',''))
        if norm(st.get('Website')) and norm(st.get('Website')) in norm(x.get('homepage','')):
            score += 0.35
        if st.get('Country') and norm(st['Country']) == norm(x.get('country','')):
            score += 0.10
        if score < 0.90: continue
        stream=x.get('url_resolved') or x.get('url')
        if not stream: continue
        out.append((score,x,stream))
    out.sort(key=lambda t:t[0], reverse=True)
    return out[:5]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args=ap.parse_args()
    stations=json.loads(DB.read_text(encoding='utf-8'))
    history=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else {}
    audit=[]
    changed=False
    for st in stations:
        ok=stream_ok(st.get('StreamUrl',''))
        sid=st['Id']
        h=history.setdefault(sid,{"consecutive_failures":0,"last_ok":None,"last_check":None})
        if ok:
            h['consecutive_failures']=0; h['last_ok']=now()
        else:
            h['consecutive_failures']=int(h.get('consecutive_failures',0))+1
        h['last_check']=now()
        item={"Id":sid,"Name":st['Name'],"online":ok,"consecutive_failures":h['consecutive_failures']}
        if not ok and h['consecutive_failures'] >= 2:
            try:
                cs=candidates(st)
            except Exception as e:
                cs=[]; item['candidate_error']=str(e)
            verified=[]
            for score,c,stream in cs:
                if stream_ok(stream):
                    verified.append({"score":round(score,3),"name":c.get('name'),"stream":stream,"homepage":c.get('homepage',''),"country":c.get('country',''),"bitrate":c.get('bitrate',0),"codec":c.get('codec','')})
            item['verified_candidates']=verified
            if args.apply and verified and verified[0]['score'] >= 1.15:
                old=st.get('StreamUrl','')
                new=verified[0]['stream']
                if new != old:
                    st['BackupStreamUrl']=old
                    st['StreamUrl']=new
                    if verified[0].get('codec'): st['Codec']=verified[0]['codec']
                    if verified[0].get('bitrate'): st['Bitrate']=f"{verified[0]['bitrate']} kbps"
                    changed=True
                    item['applied_replacement']={"old":old,"new":new}
        audit.append(item)
    HISTORY.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    REPORT.write_text(json.dumps({"GeneratedUtc":now(),"StationCount":len(stations),"Changed":changed,"Results":audit},ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    if changed:
        DB.write_text(json.dumps(stations,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    print(json.dumps({"changed":changed,"online":sum(x['online'] for x in audit),"offline":sum(not x['online'] for x in audit)},ensure_ascii=False))

if __name__=='__main__': main()
