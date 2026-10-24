"""Record smooth, action-driven baselines and perturbation/recovery branches.

Successful baseline waypoints guide the recovery. Simulator poses are privileged;
these are workflow demonstrations, not trained-model benchmark evaluations.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
from interactive_harness import Session


def blend(u):
    return u**3 * (10 - 15*u + 6*u*u)


class SmoothSession(Session):
    def __init__(self, args):
        self.references = []
        self.states = []
        self.previous_arm = np.zeros(6)
        args.recording_fps = 20
        args.arm_reference = 'base' if args.task == 'NavigateKitchen' else 'world'
        super().__init__(args)
        self.initial_state = self.sim.get_state().flatten().copy()
        self.manifest.update(executor_version='v5-minimum-jerk',
            motion_profile='Quintic reference paths, bounded action slew, damped feedback; native 20 fps.',
            arm_reference=args.arm_reference, source_success_baseline=getattr(args,'baseline',None),
            navigation=args.task=='NavigateKitchen')
        if args.task=='NavigateKitchen':
            self.manifest.update(camera='base_following_third_person',target_fixture=self.env.target_fixture.nat_lang,
                target_position=self.env.target_pos.tolist(),target_yaw=float(self.env.target_ori[2]))
        self.save_manifest()

    def save_manifest(self):
        (self.root/'manifest.json').write_text(json.dumps(self.manifest,indent=2))

    def base_pose(self):
        bid=self.sim.model.body_name2id('mobilebase0_base')
        r=self.sim.data.body_xmat[bid].reshape(3,3)
        return self.sim.data.body_xpos[bid].copy(),float(np.arctan2(r[1,0],r[0,0]))

    def render(self):
        if self.a.task=='NavigateKitchen':
            pos,_=self.base_pose();c=self.sim._render_context_offscreen.cam
            c.type=0;c.lookat[:]=[pos[0]-.35,pos[1]+.2,.85];c.distance=2.6;c.azimuth=45;c.elevation=-30
            return self.sim.render(height=512,width=640,camera_name=None)[::-1].copy()
        return super().render()

    def record(self):
        self.writer.append_data(self.render())

    def tick(self, action):
        super().tick(action)
        row=self.trace[-1]
        row.update(eef_position=self.eef().tolist(),eef_rotation=self.sim.data.site_xmat[self.eef_id].tolist())
        ids=self.robot._ref_joint_pos_indexes
        if isinstance(ids,dict):ids=ids['right']
        row['robot_joint_position']=np.asarray(self.sim.data.qpos[ids]).tolist()
        if self.a.backend=='robocasa365':
            pos,yaw=self.base_pose();row.update(base_position=pos.tolist(),base_yaw=yaw)
        self.states.append(self.sim.get_state().flatten().copy())
        if self.step%40==0:
            self.status('executing',command_index=len(self.events))

    def snapshot(self,name):
        d=super().snapshot(name)
        d['eef_rotation']=self.sim.data.site_xmat[self.eef_id].tolist()
        if self.a.backend=='robocasa365':
            pos,yaw=self.base_pose();d.update(base_position=pos.tolist(),base_yaw=yaw)
            if hasattr(self.env,'target_pos'):
                d.update(target_position=self.env.target_pos.tolist(),target_yaw=float(self.env.target_ori[2]),
                    target_distance_m=float(np.linalg.norm(pos[:2]-self.env.target_pos[:2])))
        (self.root/'observation.json').write_text(json.dumps(d,indent=2))
        return d

    def pose_action(self, position, rotation, grip=None):
        err=np.asarray(position)-self.eef()
        cur=self.sim.data.site_xmat[self.eef_id].reshape(3,3)
        rerr=Rotation.from_matrix(np.asarray(rotation)@cur.T).as_rotvec()
        raw=np.r_[np.clip(.75*err/.05,-.24,.24),np.clip(.75*rerr/.5,-.24,.24)]
        arm=self.previous_arm+np.clip(raw-self.previous_arm,-.045,.045)
        self.previous_arm=arm
        return self.action(arm[:3],arm[3:],grip)

    def move(self,target,grip=None,rotation=None,steps=80,tolerance=.008):
        target=np.asarray(target,float);start=self.eef().copy()
        r0=self.sim.data.site_xmat[self.eef_id].reshape(3,3).copy()
        r1=self.default_rot.copy() if rotation is None else np.asarray(rotation,float)
        rv=Rotation.from_matrix(r1@r0.T).as_rotvec()
        seconds=max(.75,1.875*np.linalg.norm(target-start)/.16,1.875*np.linalg.norm(rv)/1.05)
        n=int(math.ceil(seconds*20));begin=self.step
        self.references.append(dict(step=begin,kind='move',position=target.tolist(),rotation=r1.tolist(),grip=grip,duration_steps=n))
        for i in range(1,n+1):
            u=blend(i/n);p=start+(target-start)*u;r=Rotation.from_rotvec(rv*u).as_matrix()@r0
            self.tick(self.pose_action(p,r,grip))
        stable=0
        for _ in range(40):
            cur=self.sim.data.site_xmat[self.eef_id].reshape(3,3)
            good=np.linalg.norm(target-self.eef())<tolerance and np.linalg.norm(Rotation.from_matrix(r1@cur.T).as_rotvec())<.09
            stable=stable+1 if good else 0
            if stable>=5:break
            self.tick(self.pose_action(target,r1,grip))
        return bool(np.linalg.norm(target-self.eef())<max(.015,tolerance*2))

    def hold(self,n=12,grip=None):
        p=self.eef().copy();r=self.sim.data.site_xmat[self.eef_id].reshape(3,3).copy()
        self.references.append(dict(step=self.step,kind='hold',position=p.tolist(),rotation=r.tolist(),grip=grip,duration_steps=n))
        for _ in range(n):self.tick(self.pose_action(p,r,grip))

    def navigate(self,cmd):
        before,yaw0=self.base_pose();target=np.asarray(cmd.get('position',self.env.target_pos if hasattr(self.env,'target_pos') else before),float)
        if 'delta_world' in cmd:target=before+np.asarray(cmd['delta_world'],float)
        yaw=float(cmd.get('yaw',yaw0));dyaw=float(np.arctan2(np.sin(yaw-yaw0),np.cos(yaw-yaw0)))
        seconds=max(1.,1.875*np.linalg.norm(target[:2]-before[:2])/.22,1.875*abs(dyaw)/.6)
        n=int(math.ceil(seconds*20));last=np.zeros(3);start_step=self.step
        ctrl=self.robot.composite_controller.part_controllers['base']
        armctrl=self.robot.composite_controller.part_controllers['right'];old_frame=armctrl.input_ref_frame
        if old_frame!='base':
            self.robot.composite_controller.update_state()
            armctrl.update(force=True)
            armctrl.input_ref_frame='base'
            # reset_goal stores world coordinates; explicitly transform the hold
            # pose when switching to a moving base reference frame.
            armctrl.goal_pos=armctrl.origin_ori.T@(armctrl.ref_pos-armctrl.origin_pos)
            armctrl.goal_ori=armctrl.origin_ori.T@armctrl.ref_ori_mat
        self.references.append(dict(step=self.step,kind='navigate',position=target.tolist(),yaw=yaw,duration_steps=n))
        stable=0
        for i in range(1,n+161):
            u=min(i/n,1.);h=blend(u);dh=30*u*u*(1-u)*(1-u)/seconds if u<1 else 0.
            p,angle=self.base_pose();ref=before+(target-before)*h;angle_ref=yaw0+dyaw*h
            world=(target[:2]-before[:2])*dh+1.2*(ref[:2]-p[:2])
            rate=dyaw*dh+1.5*np.arctan2(np.sin(angle_ref-angle),np.cos(angle_ref-angle))
            axes=np.stack([self.sim.data.xaxis[self.sim.model.joint_name2id('mobilebase0_joint_mobile_'+k)][:2] for k in ['forward','side']],axis=1)
            velocity=np.r_[np.linalg.solve(axes,world),rate]
            # Compensate the actuator's declared Coulomb friction, smoothly near zero.
            desired=velocity+np.array([.25,.25,1/6])*np.tanh(velocity/.018)
            desired=np.clip(desired,-.65,.65);desired=last+np.clip(desired-last,-.022,.022);last=desired
            theta=angle-np.arctan2(ctrl.init_ori[1,0],ctrl.init_ori[0,0]);co,si=np.cos(theta),np.sin(theta)
            base=np.array([co*desired[0]+si*desired[1],-si*desired[0]+co*desired[1],desired[2]])
            a=self.robot.create_action_vector({'right':np.zeros(6),'right_gripper':np.array([self.grip]),'base':base,'torso':np.zeros(1),'base_mode':np.array([1.])})
            self.tick(np.asarray(a))
            p,angle=self.base_pose();err=abs(np.arctan2(np.sin(yaw-angle),np.cos(yaw-angle)))
            good=i>=n and np.linalg.norm(target[:2]-p[:2])<.045 and err<.06
            stable=stable+1 if good else 0
            if stable>=12:break
        for _ in range(20):
            last=last+np.clip(-last,-.022,.022)
            a=self.robot.create_action_vector({'right':np.zeros(6),'right_gripper':np.array([self.grip]),'base':last,'torso':np.zeros(1),'base_mode':np.array([1.])});self.tick(np.asarray(a))
        if old_frame!='base':armctrl.input_ref_frame=old_frame;armctrl.reset_goal()
        p,angle=self.base_pose();err=float(np.arctan2(np.sin(yaw-angle),np.cos(yaw-angle)))
        return dict(action='navigate',base_start=before.tolist(),base_end=p.tolist(),target_distance_m=float(np.linalg.norm(target[:2]-p[:2])),heading_error_rad=err,reached=bool(np.linalg.norm(target[:2]-p[:2])<.15 and abs(err)<.15),steps=self.step-start_step)

    def execute(self,cmd):
        if cmd['action']=='source_reference':
            source=Path(self.a.baseline)/'reference_waypoints.json'
            refs=json.loads(source.read_text())
            first=int(cmd.get('begin',0));last=int(cmd.get('end',len(refs)))
            feedback=[]
            for index in range(first,last):
                ref=refs[index];begin=self.step
                if ref['kind']=='move':
                    reached=self.move(ref['position'],ref.get('grip'),rotation=ref['rotation'])
                elif ref['kind']=='hold':
                    for _ in range(ref['duration_steps']):
                        self.tick(self.pose_action(ref['position'],ref['rotation'],ref.get('grip')))
                    reached=True
                elif ref['kind']=='navigate':
                    reached=self.navigate(dict(position=ref['position'],yaw=ref['yaw']))['reached']
                else:raise ValueError('Unsupported source reference '+ref['kind'])
                feedback.append(dict(source_index=index,kind=ref['kind'],step_start=begin,step_end=self.step,reached=reached))
            return dict(action='source_reference',source_case=Path(self.a.baseline).name,
                source_reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                references=feedback,official_success=self.success())
        if cmd['action'] in ['navigate','base_shift']:return self.navigate(cmd)
        if cmd['action']=='sequence':
            feedback=[]
            for sub in cmd['commands']:
                fb=self.execute(sub);feedback.append(dict(command=sub,feedback=fb,step=self.step,official_success=self.success()))
                if sub['action']=='pick' and not fb.get('object_follows_gripper'):break
            return dict(action='sequence',substeps=feedback,official_success=self.success())
        return super().execute(cmd)

    def seal(self):
        np.savez_compressed(self.root/'trajectory.npz',initial_state=self.initial_state,states=np.asarray(self.states))
        (self.root/'reference_waypoints.json').write_text(json.dumps(self.references,indent=2))


def run_baseline(spec,args):
    s=SmoothSession(args);s.manifest['brain']='none; deterministic successful-trajectory collection';s.manifest['output_schema']=[];s.save_manifest()
    try:
        for cmd in spec['baseline_commands']:
            idx=len(s.events);begin=s.step;before=s.snapshot(f'{idx:03d}-before');s.status('executing')
            fb=s.execute(cmd);after=s.snapshot(f'{idx:03d}-after')
            e=dict(index=idx,step_start=begin,step_end=s.step,brain=None,command=cmd,feedback=fb,official_success=s.success(),private_controller_diagnostics=dict(before=before,after=after))
            s.events.append(e);(s.root/'events.json').write_text(json.dumps(s.events,indent=2))
            s.metrics.add({'baseline/completed_commands':idx+1,'baseline/official_success':s.success()},s.step)
            if cmd['action']=='pick' and not fb.get('object_follows_gripper'):break
        result=dict(success=s.success(),steps=s.step,commands=len(s.events),brain_records=0,termination='baseline_plan')
        (s.root/'result.json').write_text(json.dumps(result,indent=2));s.status('complete',**result)
        s.metrics.add({'status/running':0,'evaluation/completed_episodes':1,'baseline/success':result['success'],'evaluation/progress':1},s.step)
    except Exception as e:s.status('failed',error=str(e));raise
    finally:
        s.writer.close();(s.root/'actions.json').write_text(json.dumps(s.trace));s.seal();s.env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--case',required=True);p.add_argument('--mode',choices=['baseline','recovery'],required=True);p.add_argument('--output',required=True);p.add_argument('--baseline');a=p.parse_args()
    spec=next(x for x in json.loads(Path(a.spec).read_text()) if x['id']==a.case)
    args=SimpleNamespace(backend=spec['backend'],task=spec['task'],seed=spec['seed'],layout=spec.get('layout',1),style=spec.get('style',1),horizon=15000,output=a.output,baseline=a.baseline)
    if a.mode=='baseline':run_baseline(spec,args)
    else:
        b=Path(a.baseline);result=json.loads((b/'result.json').read_text());assert result['success'],'A verified source success is required'
        s=SmoothSession(args);s.manifest['source_success_baseline']=dict(case=b.name,success=True,trajectory_sha256=hashlib.sha256((b/'trajectory.npz').read_bytes()).hexdigest(),reference_waypoints_sha256=hashlib.sha256((b/'reference_waypoints.json').read_bytes()).hexdigest(),commands_sha256=hashlib.sha256((b/'events.json').read_bytes()).hexdigest(),origin='Newly collected simulator success, not a public human demonstration dataset.');s.save_manifest()
        try:s.run()
        finally:s.seal()
