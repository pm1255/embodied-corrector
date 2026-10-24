"""Navigation + manipulation demonstrations with an initialization-only mobile start.

The original OrganizeVegetables predicate is unchanged. Moving the initial base
back from the prep counter is an explicitly disclosed demonstration variant.
No simulator state is assigned after the initial snapshot.
"""
import argparse, hashlib, json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
from smooth_harness import SmoothSession

class MobileRecoverySession(SmoothSession):
    def snapshot(self, name):
        if name == 'initial' and not hasattr(self, 'prep_position'):
            from robocasa.utils.env_utils import set_robot_to_position
            self.prep_position, self.prep_yaw = self.base_pose()
            start = self.prep_position + np.array(self.a.start_offset)
            set_robot_to_position(self.env, start)
            self.sim.forward()
            self.robot.composite_controller.update_state()
            for controller in self.robot.composite_controller.part_controllers.values():
                controller.update(force=True)
            self.robot.composite_controller.reset()
            self.home = self.eef().copy()
            self.manifest.update(
                navigation=True, navigation_and_manipulation=True,
                task_variant='OrganizeVegetables with a disclosed farther mobile-base start',
                initialization_only_base_offset=self.a.start_offset,
                prep_position=self.prep_position.tolist(), prep_yaw=self.prep_yaw,
                camera='fixed whole-robot view with simultaneous counter close-up',
                raw_width=960,raw_height=720)
        d = super().snapshot(name)
        d.update(prep_position=self.prep_position.tolist(),prep_yaw=self.prep_yaw,
                 prep_distance_m=float(np.linalg.norm(np.array(d['base_position'])[:2]-self.prep_position[:2])))
        (self.root/'observation.json').write_text(json.dumps(d,indent=2))
        return d

    def render(self):
        p=self.prep_position
        c=self.sim._render_context_offscreen.cam
        c.type=0;c.lookat[:]=[p[0]-.1,p[1]-.25,.75];c.distance=2.8;c.azimuth=45;c.elevation=-45
        wide=self.sim.render(height=720,width=960,camera_name=None)[::-1].copy()
        close=self.sim.render(height=256,width=320,camera_name='robot0_agentview_left')[::-1].copy()
        # Simultaneous physical cameras, no synthesized motion.
        wide[8:268,632:956]=[160,232,206]
        wide[10:266,634:954]=close
        return wide

    def execute(self, cmd):
        if cmd['action']=='navigate_prep':
            return self.navigate(dict(position=self.prep_position,yaw=self.prep_yaw))
        return super().execute(cmd)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--case',required=True);p.add_argument('--output',required=True);p.add_argument('--baseline',required=True);a=p.parse_args()
    spec=next(x for x in json.loads(Path(a.spec).read_text()) if x['id']==a.case)
    b=Path(a.baseline);assert json.loads((b/'result.json').read_text())['success']
    args=SimpleNamespace(backend='robocasa365',task='OrganizeVegetables',seed=spec['seed'],layout=1,style=1,horizon=15000,output=a.output,baseline=a.baseline,command_timeout=7200,start_offset=spec.get('start_offset',[0,-.8,0]))
    s=MobileRecoverySession(args)
    s.manifest.update(navigation=True,navigation_and_manipulation=True,executor_version='v6-visible-mobile-recovery',source_success_baseline=dict(case=b.name,success=True,trajectory_sha256=hashlib.sha256((b/'trajectory.npz').read_bytes()).hexdigest(),reference_waypoints_sha256=hashlib.sha256((b/'reference_waypoints.json').read_bytes()).hexdigest(),commands_sha256=hashlib.sha256((b/'events.json').read_bytes()).hexdigest(),origin='Newly collected simulator success; mobile start is a disclosed demonstration variant.'))
    s.save_manifest()
    try:s.run()
    finally:s.seal()
