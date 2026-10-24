"""Run four bounded CPU simulator workers and record aggregate TensorBoard progress."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess,os,json,time,sys
root=Path(__file__).resolve().parents[2];os.chdir(root);(root/'logs').mkdir(exist_ok=True)
from tensorboard.summary.writer.event_file_writer import EventFileWriter
from tensorboard.compat.proto.event_pb2 import Event
from tensorboard.compat.proto.summary_pb2 import Summary
writer=EventFileWriter(str(root/'runs/gallery-overview/tensorboard'))
items=json.loads((root/'gallery_manifest.json').read_text());done=[]
def log():
 vals={'gallery/total':len(items),'gallery/completed':len(done),'gallery/progress':len(done)/len(items),'gallery/errors':sum(x['returncode']!=0 for x in done),'status/running':len(done)<len(items)}
 writer.add_event(Event(wall_time=time.time(),step=len(done),summary=Summary(value=[Summary.Value(tag=k,simple_value=float(v)) for k,v in vals.items()])));writer.flush()
def run(item):
 env=dict(os.environ,MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/50_mesa.json',LIBERO_CONFIG_PATH=str(root/'libero-config'),PYTHONPATH=str(root/'vendor/LIBERO-PRO'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LP_NUM_THREADS='2')
 python=root/('.venv-libero' if item['backend']=='libero_pro' else '.venv-robocasa')/'bin/python'
 with (root/'logs'/(item['id']+'.log')).open('w') as f:
  r=subprocess.run([str(python),'scripts/simulations/batch_gallery.py','gallery_manifest.json',item['id']],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 return {'id':item['id'],'returncode':r.returncode}
log()
with ThreadPoolExecutor(max_workers=4) as pool:
 fs={pool.submit(run,i):i for i in items}
 for f in as_completed(fs):
  try:result=f.result()
  except Exception as e:result={'id':fs[f]['id'],'returncode':-1,'error':str(e)}
  done.append(result);print(json.dumps(result),flush=True);(root/'gallery_status.json').write_text(json.dumps(done,indent=2));log()
writer.close()
