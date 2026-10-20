import hashlib,json,re
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
CONTRACT=str(ROOT/'semver_constraint_lock.py')
SOURCE=json.loads((ROOT/'fixtures/sources.json').read_text())[0]
BODY=(ROOT/'fixtures/package.json').read_text()

def deploy(vm,deployer):
    vm.warp('2026-10-21T00:00:00Z');return deployer(CONTRACT,sdk_version='v0.2.12')
def inputs(dependency='viem'):
    return [{'url':SOURCE['url'],'sha256':SOURCE['sha256'],'package':'genlayer-js','section':'dependencies','dependency':dependency}]
def serve(vm,body=BODY):vm.mock_web(re.escape(SOURCE['url']),{'status':200,'body':body})
def opened(vm,c,dependency='viem'):
    c.open_lock('sdk',json.dumps(inputs(dependency)));serve(vm)
def captured(vm,c,dependency='viem'):
    opened(vm,c,dependency);c.capture('sdk')

def test_real_manifest_capture_and_version_selection(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);captured(direct_vm,c)
    lock=c.get_lock('sdk');assert lock['status']=='READY'
    assert lock['intersection']=={'lower':'2.29.0','lower_inclusive':True,'upper':'3.0.0','upper_inclusive':False}
    assert direct_vm.run_validator() is True
    c.select('sdk','2.30.1',lock['snapshot_sha256'])
    assert c.get_certificate('sdk')['valid'] is True
    assert c.get_certificate('sdk')['selected_version']=='2.30.1'

@pytest.mark.parametrize('version',['2.28.9','3.0.0','2.30.0-beta.1','v2.30.0','02.30.0'])
def test_outside_or_nonstable_candidate_rejected(direct_vm,direct_deploy,version):
    c=deploy(direct_vm,direct_deploy);captured(direct_vm,c)
    with direct_vm.expect_revert():c.select('sdk',version,c.get_lock('sdk')['snapshot_sha256'])
    assert c.get_lock('sdk')['status']=='READY'

def test_zero_major_caret_boundaries(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);captured(direct_vm,c,'typescript-parsec')
    assert c.get_lock('sdk')['intersection']['upper']=='0.4.0'
    with direct_vm.expect_revert('satisfy'):c.select('sdk','0.4.0',c.get_lock('sdk')['snapshot_sha256'])
    c.select('sdk','0.3.4',c.get_lock('sdk')['snapshot_sha256'])

def test_validator_recomputes_range_and_fetch(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);captured(direct_vm,c)
    packet=c.get_lock('sdk')['snapshot'];packet['constraints'][0]['range']='*'
    assert direct_vm.run_validator(leader_result=json.dumps(packet,sort_keys=True,separators=(',',':'))) is False
    direct_vm.clear_mocks();serve(direct_vm,'changed public manifest')
    assert direct_vm.run_validator() is False

def test_compare_and_set_single_selection_and_revoke(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);captured(direct_vm,c)
    with direct_vm.expect_revert('snapshot'):c.select('sdk','2.29.0','00'*32)
    c.select('sdk','2.29.0',c.get_lock('sdk')['snapshot_sha256'])
    with direct_vm.expect_revert('not ready'):c.select('sdk','2.30.0',c.get_lock('sdk')['snapshot_sha256'])
    c.revoke('sdk');assert c.get_certificate('sdk')['valid'] is False
    with direct_vm.expect_revert('not ready'):c.select('sdk','2.29.0',c.get_lock('sdk')['snapshot_sha256'])

def test_owner_only_and_unique_locked_id(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);captured(direct_vm,c)
    from gltest.direct import create_address
    with direct_vm.prank(create_address('outsider')):
        with direct_vm.expect_revert('owner only'):c.select('sdk','2.29.0',c.get_lock('sdk')['snapshot_sha256'])
        with direct_vm.expect_revert('owner only'):c.open_lock('other',json.dumps(inputs()))
    with direct_vm.expect_revert('already locked'):c.open_lock('sdk',json.dumps(inputs()))
    with direct_vm.expect_revert('already captured'):c.capture('sdk')

@pytest.mark.parametrize('ranges,expected',[(['>=2.0.0 <3.0.0','>=3.0.0'],'CONFLICT'),(['~2.29.0','>=2.29.1 <=2.29.5'],'READY'),(['^0.0.4','0.0.5'],'CONFLICT'),(['>2.29.0','<2.29.1'],'CONFLICT'),(['>999999.999999.999999','>=0.0.0'],'CONFLICT')])
def test_intersections_from_explicit_synthetic_manifests(direct_vm,direct_deploy,ranges,expected):
    c=deploy(direct_vm,direct_deploy);sources=[]
    for i,expression in enumerate(ranges):
        body=json.dumps({'name':'synthetic-'+str(i),'version':'1.0.0','dependencies':{'viem':expression}})
        url=SOURCE['url'].replace('/package.json','/synthetic-'+str(i)+'.json')
        sources.append({'url':url,'sha256':hashlib.sha256(body.encode()).hexdigest(),'package':'synthetic-'+str(i),'section':'dependencies','dependency':'viem'})
        direct_vm.mock_web(re.escape(url),{'status':200,'body':body})
    c.open_lock('sdk',json.dumps(sources));c.capture('sdk')
    assert c.get_lock('sdk')['status']==expected
    assert direct_vm.run_validator() is True

def test_unsupported_range_is_never_silently_relaxed(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);body=BODY.replace('^2.29.0','2.x || >=3.0.0')
    sources=inputs();sources[0]['sha256']=hashlib.sha256(body.encode()).hexdigest()
    c.open_lock('sdk',json.dumps(sources));serve(direct_vm,body)
    with direct_vm.expect_revert('unsupported range'):c.capture('sdk')
    assert c.get_lock('sdk')['status']=='OPEN'
