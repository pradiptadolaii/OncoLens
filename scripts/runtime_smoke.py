import io,json,os,secrets,subprocess,sys,time
from pathlib import Path
import httpx,psutil
from PIL import Image
root=Path(__file__).resolve().parents[1]
model=Path(os.environ.get('ONCOLENS_MODEL_PATH',root/'models'/'resnet18_audited_experiment_best.pth')).resolve()
env=os.environ.copy();env.update({'ONCOLENS_MODEL_PATH':str(model),'ONCOLENS_USERNAME':'researcher','ONCOLENS_PASSWORD':secrets.token_urlsafe(32),'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','UVICORN_ACCESS_LOG':'false','ONCOLENS_MAX_IMAGE_PIXELS':'4000000'})
log=(root/'.runtime-smoke.log').open('w',encoding='utf-8')
proc=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','0.0.0.0','--port','8765'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
peak=0;start=time.monotonic();client=httpx.Client(base_url='http://127.0.0.1:8765',auth=('researcher',env['ONCOLENS_PASSWORD']),timeout=30)
def sample():
 global peak
 try:
  process=psutil.Process(proc.pid)
  tree=[process]+process.children(recursive=True)
  memories=[item.memory_info() for item in tree]
  linux_peaks=[]
  for item in tree:
   status=Path('/proc')/str(item.pid)/'status'
   if status.is_file():
    for line in status.read_text().splitlines():
     if line.startswith('VmHWM:'):linux_peaks.append(int(line.split()[1])*1024)
  if linux_peaks:peak=max(peak,sum(linux_peaks))
  peak=max(peak,sum(max(m.rss,getattr(m,'peak_wset',0)) for m in memories))
 except psutil.Error:pass
results={'python':sys.version.split()[0],'cloud_tests':'not run'}
try:
 while time.monotonic()-start<180:
  sample()
  if proc.poll() is not None:raise RuntimeError('Server startup failed; inspect local runtime log.')
  try:
   if client.get('/api/health').status_code==200:break
  except httpx.HTTPError:pass
  time.sleep(.25)
 else:raise RuntimeError('Server startup timed out.')
 results['startup_seconds']=round(time.monotonic()-start,2)
 results['health']=client.get('/api/health').json()
 results['dashboard_status']=client.get('/').status_code
 for size in [(224,224),(2000,2000)]:
  data=io.BytesIO();Image.new('RGB',size,(128,128,128)).save(data,format='PNG')
  response=client.post('/api/predict',files={'file':('synthetic.png',data.getvalue(),'image/png')});sample()
  assert response.status_code==200,response.text
  scores=response.json()['scores'];assert set(scores)=={'glioma','meningioma','notumor','pituitary'}
  assert abs(sum(scores.values())-1)<1e-5
  results['synthetic_'+str(size[0])+'_status']=response.status_code
 results['invalid_status']=client.post('/api/predict',files={'file':('invalid.png',b'not an image','image/png')}).status_code
 results['oversized_status']=client.post('/api/predict',files={'file':('large.png',b'x'*(10*1024*1024+1),'image/png')}).status_code
 data=io.BytesIO();Image.new('RGB',(2001,2000),(0,0,0)).save(data,format='PNG')
 results['dimension_status']=client.post('/api/predict',files={'file':('large.png',data.getvalue(),'image/png')}).status_code
 sample();results['server_peak_rss_mib']=round(peak/1024**2,1)
 assert results['dashboard_status']==200 and results['invalid_status']==400 and results['oversized_status']==413 and results['dimension_status']==400
 from importlib.machinery import SourceFileLoader
 artifact=SourceFileLoader('artifact',str(root/'model_artifact.py')).load_module()
 artifact.verify_model(root/'models/resnet18_audited_experiment_best.pth')
 results['checkpoint_sha256']=artifact.EXPECTED_SHA256
 (root/'runtime-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 print(json.dumps(results,indent=2),flush=True)
finally:
 client.close();proc.terminate()
 try:proc.wait(timeout=15)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
 log.close()
