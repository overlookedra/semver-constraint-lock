# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import hashlib
import json
import re
from datetime import datetime,timezone

def _require(ok: bool,message: str) -> None:
    if not ok:raise gl.vm.UserError('[EXPECTED] '+message)
def _now() -> int:
    t=datetime.fromisoformat(gl.message_raw['datetime'].replace('Z','+00:00'))
    if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
    d=t.astimezone(timezone.utc)-datetime(1970,1,1,tzinfo=timezone.utc);return d.days*86400+d.seconds
def _unique(pairs: list) -> dict:
    out={}
    for key,value in pairs:
        _require(key not in out,'duplicate JSON key');out[key]=value
    return out
def _version(text: str) -> tuple:
    _require(isinstance(text,str) and re.fullmatch(r'(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})',text) is not None,'stable complete version required')
    return tuple(int(x) for x in text.split('.'))
def _text(value: tuple) -> str:return '.'.join(str(x) for x in value)
def _combine(bounds: list) -> dict:
    lo=(0,0,0);li=True;hi=None;ui=False
    for b in bounds:
        lower=_version(b['lower']);upper=_version(b['upper']) if b['upper'] is not None else None
        if lower>lo:lo=lower;li=b['lower_inclusive']
        elif lower==lo:li=li and b['lower_inclusive']
        if upper is not None:
            if hi is None or upper<hi:hi=upper;ui=b['upper_inclusive']
            elif upper==hi:ui=ui and b['upper_inclusive']
    return {'lower':_text(lo),'lower_inclusive':li,'upper':_text(hi) if hi is not None else None,'upper_inclusive':ui}
def _bounds(expression: str) -> dict:
    _require(isinstance(expression,str) and 1<=len(expression)<=160 and expression==expression.strip(),'unsupported range')
    parts=expression.split(' ');_require(1<=len(parts)<=4 and all(parts),'unsupported range')
    bounds=[]
    for part in parts:
        match=re.fullmatch(r'(\^|~|>=|<=|>|<|=)?((?:0|[1-9][0-9]{0,5})\.(?:0|[1-9][0-9]{0,5})\.(?:0|[1-9][0-9]{0,5}))',part)
        _require(match is not None,'unsupported range')
        operator=match[1] or '=';v=_version(match[2]);lo=(0,0,0);li=True;hi=None;ui=False
        if operator in ('^','~'):
            lo=v
            if operator=='~':hi=(v[0],v[1]+1,0)
            elif v[0]>0:hi=(v[0]+1,0,0)
            elif v[1]>0:hi=(0,v[1]+1,0)
            else:hi=(0,0,v[2]+1)
            _require(all(x<=999999 for x in hi),'unsupported range overflow')
        elif operator in ('>=','>'):lo=v;li=operator=='>='
        elif operator in ('<=','<'):hi=v;ui=operator=='<='
        else:lo=v;hi=v;ui=True
        bounds.append({'lower':_text(lo),'lower_inclusive':li,'upper':_text(hi) if hi is not None else None,'upper_inclusive':ui})
    return _combine(bounds)
def _empty(bounds: dict) -> bool:
    lo=_version(bounds['lower'])
    if not bounds['lower_inclusive']:
        if lo[2]<999999:lo=(lo[0],lo[1],lo[2]+1)
        elif lo[1]<999999:lo=(lo[0],lo[1]+1,0)
        elif lo[0]<999999:lo=(lo[0]+1,0,0)
        else:return True
    if bounds['upper'] is None:return False
    hi=_version(bounds['upper'])
    return lo>hi or (lo==hi and not bounds['upper_inclusive'])
def _satisfies(version: tuple,bounds: dict) -> bool:
    lo=_version(bounds['lower']);hi=_version(bounds['upper']) if bounds['upper'] is not None else None
    return (version>lo or (version==lo and bounds['lower_inclusive'])) and (hi is None or version<hi or (version==hi and bounds['upper_inclusive']))
def _source(source: dict) -> None:
    _require(isinstance(source,dict) and set(source)=={'url','sha256','package','section','dependency'},'source shape')
    url=source['url']
    match=re.fullmatch(r'https://raw\.githubusercontent\.com/[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}/[0-9a-f]{40}/([A-Za-z0-9_.~/-]+)',url) if isinstance(url,str) and len(url)<=512 else None
    _require(match is not None and all(p not in ('','.','..') for p in url.split('/')[3:]),'commit-pinned manifest required')
    _require(isinstance(source['sha256'],str) and re.fullmatch('[0-9a-f]{64}',source['sha256']) is not None,'invalid digest')
    _require(source['section'] in ('dependencies','devDependencies','peerDependencies'),'unsupported dependency section')
    for key in ('package','dependency'):_require(isinstance(source[key],str) and re.fullmatch(r'(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]{1,100}',source[key]) is not None,'invalid package name')
def _extract(source: dict) -> dict:
    response=gl.nondet.web.get(source['url'],headers={'Accept':'application/json'})
    _require(response.status==200 and response.body is not None and 1<=len(response.body)<=48000 and hashlib.sha256(response.body).hexdigest()==source['sha256'],'SOURCE unavailable, oversized or digest mismatch')
    try:manifest=json.loads(response.body.decode('utf-8'),object_pairs_hook=_unique)
    except Exception:raise gl.vm.UserError('[SOURCE] invalid strict JSON')
    _require(isinstance(manifest,dict) and manifest.get('name')==source['package'],'SOURCE package mismatch')
    _version(manifest.get('version'))
    section=manifest.get(source['section']);_require(isinstance(section,dict) and source['dependency'] in section,'SOURCE dependency absent')
    expression=section[source['dependency']];_bounds(expression)
    return dict(source,manifest_version=manifest['version'],range=expression)
def _snapshot(sources: list) -> str:
    def leader() -> str:
        constraints=[_extract(source) for source in sources]
        intersection=_combine([_bounds(c['range']) for c in constraints])
        return json.dumps({'constraints':constraints,'intersection':intersection,'conflict':_empty(intersection)},sort_keys=True,separators=(',',':'))
    def validator(proposed: gl.vm.Result) -> bool:
        if not isinstance(proposed,gl.vm.Return) or not isinstance(proposed.calldata,str):return False
        try:return leader()==proposed.calldata
        except Exception:return False
    return gl.vm.run_nondet_unsafe(leader,validator)

class SemverConstraintLock(gl.Contract):
    owner: Address
    locks: TreeMap[str,str]
    def __init__(self):self.owner=gl.message.sender_address
    def _owner(self) -> None:_require(gl.message.sender_address==self.owner,'owner only')
    def _get(self,lock_id: str) -> dict:
        _require(lock_id in self.locks,'unknown lock');return json.loads(self.locks[lock_id])
    @gl.public.write
    def open_lock(self,lock_id: str,sources_json: str) -> None:
        self._owner();_require(isinstance(lock_id,str) and re.fullmatch('[A-Za-z0-9_-]{1,64}',lock_id) is not None,'invalid lock ID')
        _require(lock_id not in self.locks,'already locked')
        _require(isinstance(sources_json,str) and len(sources_json)<=8000,'bounded sources required')
        sources=json.loads(sources_json,object_pairs_hook=_unique);_require(isinstance(sources,list) and 1<=len(sources)<=8,'one to eight manifests required')
        for source in sources:_source(source)
        _require(len({s['url'] for s in sources})==len(sources) and len({s['dependency'] for s in sources})==1,'unique sources and one dependency required')
        self.locks[lock_id]=json.dumps({'status':'OPEN','sources':sources,'snapshot':None,'snapshot_sha256':'','intersection':None,'selected_version':'','opened_at':_now(),'captured_at':0,'selected_at':0},sort_keys=True)
    @gl.public.write
    def capture(self,lock_id: str) -> None:
        lock=self._get(lock_id);_require(lock['status']=='OPEN','already captured or revoked')
        canonical=_snapshot(lock['sources']);snapshot=json.loads(canonical)
        lock.update({'status':'CONFLICT' if snapshot['conflict'] else 'READY','snapshot':snapshot,'snapshot_sha256':hashlib.sha256(canonical.encode()).hexdigest(),'intersection':snapshot['intersection'],'captured_at':_now()})
        self.locks[lock_id]=json.dumps(lock,sort_keys=True)
    @gl.public.write
    def select(self,lock_id: str,version: str,expected_snapshot_sha256: str) -> None:
        self._owner();lock=self._get(lock_id);_require(lock['status']=='READY','not ready')
        _require(expected_snapshot_sha256==lock['snapshot_sha256'],'snapshot compare-and-set mismatch')
        candidate=_version(version);_require(_satisfies(candidate,lock['intersection']),'candidate does not satisfy all constraints')
        lock.update({'status':'SELECTED','selected_version':version,'selected_at':_now()});self.locks[lock_id]=json.dumps(lock,sort_keys=True)
    @gl.public.write
    def revoke(self,lock_id: str) -> None:
        self._owner();lock=self._get(lock_id);_require(lock['status']!='REVOKED','already revoked')
        lock['status']='REVOKED';lock['revoked_at']=_now();self.locks[lock_id]=json.dumps(lock,sort_keys=True)
    @gl.public.view
    def get_lock(self,lock_id: str) -> dict:return self._get(lock_id)
    @gl.public.view
    def get_certificate(self,lock_id: str) -> dict:
        lock=self._get(lock_id)
        return {'valid':lock['status']=='SELECTED','status':lock['status'],'dependency':lock['sources'][0]['dependency'],'snapshot_sha256':lock['snapshot_sha256'],'selected_version':lock['selected_version'],'intersection':lock['intersection'],'selected_at':lock['selected_at']}
