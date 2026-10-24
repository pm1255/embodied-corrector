"""Continuous simulator episodes controlled by external GPT four-field records.

The analytical executor uses simulator object poses (privileged localization).
It is a demonstrator, not the paper's frozen-VLA evaluation protocol. Object
motion always comes from env.step; state assignment is forbidden after reset.
"""
from pathlib import Path
import argparse,json,time,traceback,hashlib,os
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image
import imageio.v2 as imageio
from tensorboard.summary.writer.event_file_writer import EventFileWriter
from tensorboard.compat.proto.event_pb2 import Event
from tensorboard.compat.proto.summary_pb2 import Summary

class Metrics:
 def __init__(self,root):self.writer=EventFileWriter(str(root/'tensorboard'))
 def add(self,values,step):
  self.writer.add_event(Event(wall_time=time.time(),step=step,summary=Summary(value=[Summary.Value(tag=k,simple_value=float(v)) for k,v in values.items()])));self.writer.flush()

class Session:
 def __init__(self,args):
  self.a=args;self.root=Path(args.output);self.root.mkdir(parents=True,exist_ok=True)
  self.commands=self.root/'commands';self.commands.mkdir(exist_ok=True);self.frames=self.root/'frames';self.frames.mkdir(exist_ok=True)
  self.step=0;self.events=[];self.metrics=Metrics(self.root);self.grip=-1.;self.closed=False;self.trace=[]
  self.metrics.add({'status/waiting':0,'status/running':1,'evaluation/completed_episodes':0},0)
  if args.backend=='libero_pro':
   from libero.libero.envs import OffScreenRenderEnv
   self.wrapper=OffScreenRenderEnv(bddl_file_name=str(Path(args.task).resolve()),use_camera_obs=False,camera_heights=512,camera_widths=512,control_freq=20,horizon=args.horizon,ignore_done=True)
   self.wrapper.seed(args.seed);self.obs=self.wrapper.reset();self.env=self.wrapper.env;self.task=self.wrapper.language_instruction;self.camera='agentview';self.arm_frame='world'
  else:
   import robocasa,robosuite
   from robosuite.controllers import load_composite_controller_config
   cfg=load_composite_controller_config(robot='PandaOmron');cfg['body_parts']['right']['input_ref_frame']=getattr(args,'arm_reference','world')
   self.env=robosuite.make(args.task,robots='PandaOmron',controller_configs=cfg,has_renderer=False,has_offscreen_renderer=True,use_camera_obs=False,use_object_obs=True,camera_names=['robot0_agentview_left'],control_freq=20,horizon=args.horizon,ignore_done=True,seed=args.seed,layout_ids=[args.layout],style_ids=[args.style],obj_instance_split='target',obj_registries=('objaverse','lightwheel'),generative_textures=None)
   self.obs=self.env.reset();self.task=self.env.get_ep_meta()['lang'];self.camera='robot0_agentview_left';self.arm_frame='world'
  self.sim=self.env.sim;self.robot=self.env.robots[0]
  sid=self.robot.eef_site_id;self.eef_id=sid['right'] if isinstance(sid,dict) else sid
  self.home=self.eef().copy();self.default_rot=np.array([[-1.,0,0],[0,1,0],[0,0,-1]])
  self.writer=imageio.get_writer(str(self.root/'raw.mp4'),fps=getattr(args,'recording_fps',10),codec='libx264',quality=7,macro_block_size=2)
  self.manifest={'backend':args.backend,'task':self.task,'seed':args.seed,'brain':'GPT proxy (Codex session), not trained RynnBrain','output_schema':['Judge','Cause','Sub','Fine'],'executor':'analytical OSC controller with simulator-state localization','executor_version':'v3-mobile','continuous_episode':True,'reset_after_failure':False,'control_frequency_hz':20,'recording_fps':getattr(args,'recording_fps',10),'task_source':args.task,'camera':self.camera,'action_dim':self.env.action_dim,'initial_model_sha256':hashlib.sha256(self.sim.model.get_xml().encode()).hexdigest()}
  (self.root/'manifest.json').write_text(json.dumps(self.manifest,indent=2,ensure_ascii=False))
  self.snapshot('initial');self.status('ready')
 def eef(self):return self.sim.data.site_xpos[self.eef_id].copy()
 def position(self,name):
  if name.startswith('site:'):return self.sim.data.site_xpos[self.sim.model.site_name2id(name[5:])].copy()
  if name in getattr(self.env,'obj_body_id',{}):return self.sim.data.body_xpos[self.env.obj_body_id[name]].copy()
  # Used only by executor and in explicitly marked instrumented diagnostics.
  if name in getattr(self.env,'objects_dict',{}):obj=self.env.objects_dict[name]
  elif name in getattr(self.env,'objects',{}):obj=self.env.objects[name]
  else:
   try:return self.sim.data.body_xpos[self.sim.model.body_name2id(name)].copy()
   except Exception:raise ValueError('Unknown localized object '+name)
  return self.sim.data.body_xpos[self.sim.model.body_name2id(obj.root_body)].copy()
 def success(self):return bool(self.env._check_success())
 def render(self):return self.sim.render(height=512,width=640,camera_name=self.camera)[::-1].copy()
 def record(self):
  if self.step%2==0:self.writer.append_data(self.render())
 def tick(self,action):
  if self.step>=self.a.horizon:raise RuntimeError('Episode action budget exhausted')
  self.obs,reward,done,info=self.env.step(action);self.step+=1
  # Success comes from the official predicate called by the environment step.
  self.trace.append({'step':self.step,'action':[float(x) for x in action],'reward':float(reward),'done':bool(done)})
  self.record()
  if self.step%40==0:self.metrics.add({'execution/physics_steps':self.step,'evaluation/progress':self.step/self.a.horizon},self.step)
 def action(self,xyz=None,rotation=None,grip=None):
  if grip is not None:self.grip=float(grip)
  a=np.zeros(self.env.action_dim)
  arm=np.concatenate([np.zeros(3) if xyz is None else xyz,np.zeros(3) if rotation is None else rotation])
  if self.a.backend=='libero_pro':a[:6]=arm;a[6]=self.grip
  else:a=self.robot.create_action_vector({'right':arm,'right_gripper':np.array([self.grip]),'base':np.zeros(3),'torso':np.zeros(1),'base_mode':np.array([-1.])})
  return np.asarray(a,dtype=float)
 def move(self,target,grip=None,rotation=None,steps=80,tolerance=.008):
  target=np.array(target,float);rot=self.default_rot if rotation is None else np.array(rotation,float);stable=0
  for i in range(steps):
   err=target-self.eef();cur=self.sim.data.site_xmat[self.eef_id].reshape(3,3);rerr=Rotation.from_matrix(rot@cur.T).as_rotvec()
   stable=stable+1 if np.linalg.norm(err)<tolerance and np.linalg.norm(rerr)<.12 else 0
   if stable>=4:return True
   self.tick(self.action(np.clip(err/.05,-.30,.30),np.clip(rerr/.5,-.5,.5),grip))
  return bool(np.linalg.norm(target-self.eef())<tolerance*2)
 def hold(self,n=12,grip=None):
  p=self.eef();r=self.sim.data.site_xmat[self.eef_id].reshape(3,3).copy()
  for _ in range(n):
   self.tick(self.action(np.clip((p-self.eef())/.05,-.5,.5),np.clip(Rotation.from_matrix(r@self.sim.data.site_xmat[self.eef_id].reshape(3,3).T).as_rotvec()/.5,-.5,.5),grip))
 def execute(self,cmd):
  kind=cmd['action'];feedback={'action':kind}
  if 'yaw_degrees' in cmd:self.default_rot=Rotation.from_euler('z',cmd['yaw_degrees'],degrees=True).as_matrix()@np.diag([-1.,1.,-1.])
  if kind=='move':feedback['reached']=self.move(cmd['position'],cmd.get('grip'),rotation=cmd.get('rotation'),steps=cmd.get('steps',80))
  elif kind=='gripper':self.hold(cmd.get('steps',15),cmd['close']);feedback['completed']=True
  elif kind=='pick':
   obj=cmd['object'];pos=self.position(obj);offset=np.array(cmd.get('offset',[0,0,0]));grasp=pos+offset
   approach=grasp+np.array([0,0,cmd.get('approach_height',.18)]);self.move(approach,-1,steps=100)
   self.move(grasp,-1,steps=100);self.hold(18,1);before=self.position(obj).copy();self.move(grasp+np.array([0,0,cmd.get('lift',.2)]),1,steps=100);after=self.position(obj)
   feedback.update({'object':obj,'object_lift_m':float(after[2]-before[2]),'object_follows_gripper':bool(after[2]-before[2]>.05)})
  elif kind=='base_shift':
   if self.a.backend!='robocasa365':raise ValueError('base_shift requires RoboCasa mobile robot')
   sid=self.sim.model.site_name2id(self.robot.robot_model.base.correct_naming('center'));before=self.sim.data.site_xpos[sid].copy();target=before.copy();target[:2]+=np.array(cmd['delta_world'][:2])
   for _ in range(cmd.get('steps',240)):
    delta=target-self.sim.data.site_xpos[sid]
    if np.linalg.norm(delta[:2])<.008:break
    local=self.sim.data.site_xmat[sid].reshape(3,3).T@delta
    base=np.array([np.clip(local[0]*1.5,-.15,.15),np.clip(local[1]*1.5,-.15,.15),0.])
    action=self.robot.create_action_vector({'right':np.zeros(6),'right_gripper':np.array([self.grip]),'base':base,'torso':np.zeros(1),'base_mode':np.array([1.])});self.tick(np.array(action))
   for _ in range(10):self.tick(self.action())
   after=self.sim.data.site_xpos[sid].copy();feedback.update({'base_displacement_world':(after-before).tolist(),'reached':bool(np.linalg.norm((target-after)[:2])<.02)})
  elif kind=='pull_drawer':
   body=cmd.get('body','wooden_cabinet_1_cabinet_top');bid=self.sim.model.body_name2id(body);rot=self.sim.data.body_xmat[bid].reshape(3,3).copy();handle=self.sim.data.body_xpos[bid]+rot@np.array([-.00278,-.10161,.18393]);self.default_rot=rot@np.diag([-1.,1.,-1.]);joint=cmd.get('joint','wooden_cabinet_1_top_level');before=float(self.sim.data.get_joint_qpos(joint))
   self.move(handle+np.array([0,0,.15]),-1,steps=120);self.move(handle,-1,steps=100);self.hold(20,1);self.move(handle+rot@np.array([0,-cmd.get('distance',.15),0]),1,steps=180);self.hold(20,1);after=float(self.sim.data.get_joint_qpos(joint));self.hold(15,-1);self.move(self.eef()+np.array([0,0,.17]),-1,steps=100);feedback.update({'drawer_before_m':before,'drawer_after_m':after,'drawer_opened_m':before-after})
  elif kind=='place':
   target=self.position(cmd['target'])+np.array(cmd.get('offset',[0,0,.12])) if 'target' in cmd else np.array(cmd['position'])
   if 'object' in cmd:target=target+self.eef()-self.position(cmd['object'])
   self.move(self.eef()+np.array([0,0,.08]),1,steps=60);self.move(target+np.array([0,0,.14]),1,steps=140);self.move(target,1,steps=100);self.hold(18,-1);self.move(target+np.array([0,0,.20]),-1,steps=100);feedback['released']=True
  elif kind=='empty_place':
   target=self.position(cmd['target'])+np.array(cmd.get('offset',[0,0,.12]));self.move(target,-1,steps=100);self.hold(12,-1);self.move(target+np.array([0,0,.18]),-1,steps=80);feedback['released']=True
  elif kind=='wait':self.hold(cmd.get('steps',20));feedback['completed']=True
  elif kind=='finish':self.closed=True;feedback['finished']=True
  else:raise ValueError('Unsupported action '+kind)
  return feedback
 def snapshot(self,name):
  Image.fromarray(self.render()).save(self.frames/(name+'.png'))
  # Private instrumented diagnostics are not conflated with model observations.
  positions={}
  for name in getattr(self.env,'obj_body_id',{}):
   try:positions[name]=self.position(name).tolist()
   except Exception:pass
  return {'eef_position':self.eef().tolist(),'localized_objects':positions}
 def status(self,state,**kw):
  data={'state':state,'task':self.task,'step':self.step,'commands_completed':len(self.events),**kw};temp=self.root/'status.tmp';temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(self.root/'status.json')
 def run(self):
  try:
   for idx in range(100):
    if self.closed:break
    p=self.commands/f'{idx:03d}.json';self.status('waiting_for_gpt',next_command=str(p))
    start=time.time()
    while not p.exists():
     if time.time()-start>1800:raise TimeoutError('No external GPT command for 30 minutes')
     time.sleep(.5)
    cmd=json.loads(p.read_text());fields=cmd.get('brain')
    if fields is not None:
     if list(fields)!=['Judge','Cause','Sub','Fine'] or fields['Judge'] not in ['success','failure'] or any(not isinstance(x,str) or not x.strip() for x in fields.values()):raise ValueError('Expected four nonempty ordered brain fields')
    self.status('executing',command_index=idx);begin=self.step;private_before=self.snapshot(f'{idx:03d}-before')
    feedback=self.execute(cmd);private_after=self.snapshot(f'{idx:03d}-after')
    event={'index':idx,'step_start':begin,'step_end':self.step,'brain':fields,'command':cmd,'feedback':feedback,'official_success':self.success(),'private_controller_diagnostics':{'before':private_before,'after':private_after}}
    self.events.append(event);(self.root/'events.json').write_text(json.dumps(self.events,ensure_ascii=False,indent=2));self.metrics.add({'brain/structured_records':sum(x['brain'] is not None for x in self.events),'execution/completed_commands':len(self.events),'execution/official_success':event['official_success']},self.step)
   result={'success':self.success(),'steps':self.step,'commands':len(self.events),'brain_records':sum(x['brain'] is not None for x in self.events),'termination':'finish_command' if self.closed else 'command_limit'}
   (self.root/'result.json').write_text(json.dumps(result,indent=2));self.metrics.add({'status/running':0,'status/complete':1,'evaluation/completed_episodes':1,'evaluation/success':result['success'],'evaluation/progress':1},self.step);self.status('complete',**result)
  except Exception as exc:
   self.status('failed',error=str(exc));self.metrics.add({'status/running':0,'status/failed':1},self.step);raise
  finally:
   self.writer.close();(self.root/'actions.json').write_text(json.dumps(self.trace));self.env.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--backend',choices=['robocasa365','libero_pro'],required=True);p.add_argument('--task',required=True);p.add_argument('--output',required=True);p.add_argument('--seed',type=int,default=7);p.add_argument('--layout',type=int,default=1);p.add_argument('--style',type=int,default=1);p.add_argument('--horizon',type=int,default=3000)
 args=p.parse_args()
 try:Session(args).run()
 except Exception as exc:
  root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
  if not (root/'status.json').exists():(root/'status.json').write_text(json.dumps({'state':'initialization_failed','error':str(exc),'step':0,'commands_completed':0}))
  raise
