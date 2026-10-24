"""Continuous RoboCasa navigation recovery with recorded base-pose evidence.

Uses ordinary environment actions only. Privileged simulator localization is
explicitly disclosed; this is a GPT-proxy demonstration, not model evaluation.
"""
import argparse,json
from pathlib import Path
import numpy as np
from interactive_harness import Session

class NavigationSession(Session):
 def base_pose(self):
  bid=self.sim.model.body_name2id('mobilebase0_base')
  r=self.sim.data.body_xmat[bid].reshape(3,3)
  return self.sim.data.body_xpos[bid].copy(),float(np.arctan2(r[1,0],r[0,0]))
 def render(self):
  if self.a.overview:
   pos,_=self.base_pose()
   c=self.sim._render_context_offscreen.cam;c.type=0;c.lookat[:]=[pos[0]-.35,pos[1]+.2,.85];c.distance=2.6;c.azimuth=45;c.elevation=-30
   return self.sim.render(height=512,width=640,camera_name=None)[::-1].copy()
  return super().render()
 def __init__(self,args):
  super().__init__(args)
  self.manifest.update(camera='base_following_third_person' if args.overview else self.camera,executor_version='v4-navigation',navigation=True,target_fixture=self.env.target_fixture.nat_lang,target_position=self.env.target_pos.tolist(),target_yaw=float(self.env.target_ori[2]),base_controller=type(self.robot.composite_controller.part_controllers['base']).__name__)
  (self.root/'manifest.json').write_text(json.dumps(self.manifest,indent=2))
 def tick(self,action):
  super().tick(action)
  pos,yaw=self.base_pose();self.trace[-1].update(base_position=pos.tolist(),base_yaw=yaw)
 def snapshot(self,name):
  d=super().snapshot(name);pos,yaw=self.base_pose()
  d['base_position']=pos.tolist();d['base_yaw']=yaw
  if hasattr(self.env,'target_pos'):
   d.update(target_position=self.env.target_pos.tolist(),target_yaw=float(self.env.target_ori[2]),target_fixture=self.env.target_fixture.nat_lang,source_fixture=self.env.src_fixture.nat_lang,target_distance_m=float(np.linalg.norm(pos[:2]-self.env.target_pos[:2])))
  (self.root/'navigation_state.json').write_text(json.dumps(d,indent=2))
  return d
 def execute(self,cmd):
  if cmd['action']!='navigate':return super().execute(cmd)
  before,yaw0=self.base_pose();target=np.array(cmd.get('position',self.env.target_pos),float)
  if 'delta_world' in cmd:target=before+np.array(cmd['delta_world'])
  yaw=float(cmd.get('yaw',yaw0));travel=0.;last=before.copy();start=self.step
  controller=self.robot.composite_controller.part_controllers['base']
  for _ in range(cmd.get('steps',600)):
   pos,angle=self.base_pose();delta=target[:2]-pos[:2];dist=np.linalg.norm(delta);err=np.arctan2(np.sin(yaw-angle),np.cos(yaw-angle))
   if dist<cmd.get('tolerance',.08) and abs(err)<.08:break
   desired=np.zeros(3)
   if dist>=cmd.get('tolerance',.08):
    world=delta/dist*np.clip(dist*1.1,.32,.50)
    axes=np.stack([self.sim.data.xaxis[self.sim.model.joint_name2id('mobilebase0_joint_mobile_'+n)][:2] for n in ['forward','side']],axis=1)
    desired[:2]=np.linalg.solve(axes,world)
   elif abs(err)>=.08:desired[2]=np.sign(err)*np.clip(abs(err)*.6,.18,.40)
   init_angle=np.arctan2(controller.init_ori[1,0],controller.init_ori[0,0]);theta=angle-init_angle
   # Invert the controller's documented current-to-initial-frame mapping.
   co,si=np.cos(theta),np.sin(theta)
   if type(controller).__name__=='LegacyMobileBaseJointVelocityController':
    if controller._check_forward_joint_reversed():
     base=np.array([si*desired[0]+co*desired[1],co*desired[0]-si*desired[1],desired[2]])
    else:
     base=np.array([co*desired[0]+si*desired[1],-si*desired[0]+co*desired[1],desired[2]])
   else:base=np.array([co*desired[0]-si*desired[1],si*desired[0]+co*desired[1],desired[2]])
   a=self.robot.create_action_vector({'right':np.zeros(6),'right_gripper':np.array([self.grip]),'base':base,'torso':np.zeros(1),'base_mode':np.array([1.])})
   self.tick(np.array(a));new,_=self.base_pose();travel+=float(np.linalg.norm(new[:2]-last[:2]));last=new
  for _ in range(10):self.tick(self.action())
  after,angle=self.base_pose();remaining=float(np.linalg.norm(target[:2]-after[:2]));heading=float(np.arctan2(np.sin(yaw-angle),np.cos(yaw-angle)))
  return dict(action='navigate',base_start=before.tolist(),base_end=after.tolist(),path_length_m=travel,displacement_m=float(np.linalg.norm(after[:2]-before[:2])),target_distance_m=remaining,heading_error_rad=heading,reached=remaining<.15 and abs(heading)<.15,steps=self.step-start)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--backend',default='robocasa365');p.add_argument('--task',default='NavigateKitchen');p.add_argument('--output',required=True);p.add_argument('--seed',type=int,default=11);p.add_argument('--layout',type=int,default=1);p.add_argument('--style',type=int,default=1);p.add_argument('--horizon',type=int,default=10000);p.add_argument('--overview',action='store_true');a=p.parse_args();NavigationSession(a).run()
