"""Continuous, state-assisted demonstration collection for distinct tasks.

These are authored perturbation/recovery demonstrations, not model evaluations.
Only env.step changes the simulation after initialization.
"""
import argparse
import hashlib
import json
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from smooth_harness import SmoothSession


def scene_xml_hash(xml):
    root = ET.fromstring(xml)
    # MuJoCo adds this redundant MIME hint when reloading an OBJ mesh. Keep all
    # geometry, dynamics, assets and explicit MIME choices in the comparison.
    for mesh in root.findall('./asset/mesh'):
        if mesh.get('file', '').lower().endswith('.obj') and 'content_type' not in mesh.attrib:
            mesh.set('content_type', 'model/obj')
        # The XML writer may omit the identity reference quaternion on reload.
        # Its declared MuJoCo default is the same physical mesh orientation.
        if 'refquat' not in mesh.attrib:
            mesh.set('refquat', '1 0 0 0')
    canonical = ET.canonicalize(ET.tostring(root, encoding='unicode'))
    return hashlib.sha256(canonical.encode()).hexdigest()


class DistinctSession(SmoothSession):
    def __init__(self, args):
        # Some third-party asset samplers use global RNGs in addition to env.seed.
        random.seed(args.seed)
        np.random.seed(args.seed)
        scene_source = getattr(args, 'initial_scene', None) or getattr(args, 'baseline', None)
        if args.backend == 'robocasa365' and scene_source:
            meta = json.loads((Path(scene_source)/'manifest.json').read_text())
            args.initial_ep_meta = meta.get('episode_metadata')
            model_path = Path(scene_source)/'initial_model.xml'
            if model_path.exists():
                args.initial_model_xml = model_path.read_text()
        super().__init__(args)

    def snapshot(self, name):
        if name == 'initial' and self.a.backend == 'robocasa365' and not hasattr(self, 'initialized_posture'):
            self.initialized_posture = True
            scene_source = getattr(self.a, 'initial_scene', None) or getattr(self.a, 'baseline', None)
            if scene_source:
                baseline = Path(scene_source)
                baseline_meta = json.loads((baseline/'manifest.json').read_text())
                same = baseline_meta['initial_model_sha256'] == self.manifest['initial_model_sha256']
                source_xml = baseline/'initial_model.xml'
                if not same and source_xml.exists():
                    same = scene_xml_hash(source_xml.read_text()) == scene_xml_hash(self.sim.model.get_xml())
                    if same:
                        self.manifest['source_model_verification'] = 'Exact canonical XML match; OBJ MIME hints and default mesh reference quaternions normalized'
                if not same:
                    (self.root/'initialization_model_mismatch.xml').write_text(self.sim.model.get_xml())
                    raise RuntimeError('Source scene model differs; refuse to replay source waypoints')
                # This is the episode's initialization, before its first action.
                self.sim.set_state_from_flattened(np.load(baseline/'trajectory.npz')['initial_state'])
                self.sim.forward()
                self.manifest['initial_state_origin'] = baseline.name
            torso = getattr(self.a, 'initial_torso', None)
            if torso is not None:
                joint = next(n for n in self.sim.model.joint_names if n and n.endswith('joint_torso_height'))
                self.sim.data.set_joint_qpos(joint, torso)
            self.sim.forward()
            self.robot.composite_controller.update_state()
            for controller in self.robot.composite_controller.part_controllers.values():
                controller.update(force=True)
            self.robot.composite_controller.reset()
            self.home = self.eef().copy()
            pos, _ = self.base_pose()
            self.wide_center = pos.copy()
            self.manifest.update(initialization_only_torso_height=torso,
                episode_metadata=self.env.get_ep_meta(),
                task_variant='Original task predicate; disclosed initialization-only torso posture for state-assisted demonstrations',
                camera='fixed wide camera with simultaneous arm view', raw_width=960, raw_height=720)
            (self.root/'initial_model.xml').write_text(self.sim.model.get_xml())
        d = super().snapshot(name)
        d['joints'] = {
            n: np.asarray(self.sim.data.get_joint_qpos(n)).tolist()
            for n in self.sim.model.joint_names
            if n and not n.startswith(('robot', 'gripper', 'mobilebase'))
        }
        d['sites'] = {
            n: self.sim.data.site_xpos[self.sim.model.site_name2id(n)].tolist()
            for n in self.sim.model.site_names
            if n and any(t in n for t in ['cabinet', 'microwave', 'stove', 'bowl', 'handle', 'button', 'knob', 'caddy', 'mug'])
        }
        d['bodies'] = {
            n: dict(position=self.sim.data.body_xpos[i].tolist(), rotation=self.sim.data.body_xmat[i].tolist())
            for i, n in enumerate(self.sim.model.body_names)
            if n and any(t in n for t in ['cabinet', 'microwave', 'stove', 'bowl', 'handle', 'caddy', 'mug'])
        }
        d['official_success'] = self.success()
        d['robot_joints'] = {n: np.asarray(self.sim.data.get_joint_qpos(n)).tolist()
                             for n in self.sim.model.joint_names
                             if n and n.startswith(('robot', 'gripper', 'mobilebase'))}
        d['contacts'] = [dict(a=self.sim.model.geom_id2name(c.geom1),
                              b=self.sim.model.geom_id2name(c.geom2), distance=float(c.dist))
                         for c in self.sim.data.contact[:self.sim.data.ncon]]
        if self.a.backend == 'robocasa365':
            d['object_geometry'] = {}
            for object_name, obj in self.env.objects.items():
                body_id = self.sim.model.body_name2id(obj.root_body)
                d['object_geometry'][object_name] = dict(
                    root_body=obj.root_body,
                    rotation=self.sim.data.body_xmat[body_id].tolist(),
                    sites={n: self.sim.data.site_xpos[i].tolist()
                           for i, n in enumerate(self.sim.model.site_names)
                           if n and n.startswith(object_name + '_')})
            from robocasa.utils.env_utils import compute_robot_base_placement_pose
            d['fixtures'] = {}
            for key, value in self.env.fixture_refs.items():
                fixture = value[0] if isinstance(value, tuple) else value
                try:
                    pos, ori = compute_robot_base_placement_pose(self.env, ref_fixture=fixture)
                    d['fixtures'][key] = dict(name=fixture.name, position=list(fixture.pos),
                        dock_position=list(pos), dock_yaw=float(ori[2]))
                except Exception as exc:
                    d['fixtures'][key] = dict(name=fixture.name, error=str(exc))
                if hasattr(fixture, 'get_state'):
                    try:
                        d['fixtures'][key]['state'] = fixture.get_state()
                    except TypeError:
                        pass
        (self.root/'observation.json').write_text(json.dumps(d, indent=2))
        return d

    def render(self):
        if self.a.backend != 'robocasa365' or not hasattr(self, 'wide_center'):
            return super().render()
        context = self.sim._render_context_offscreen
        if not getattr(self, '_render_quality_configured', False):
            # This affects the framebuffer only. Restore the model's visual
            # property so source XML verification and all physics stay intact.
            samples = context.model.vis.quality.offsamples
            try:
                context.model.vis.quality.offsamples = 0
                if context.con.offWidth < 960 or context.con.offHeight < 720:
                    context.update_offscreen_size(960, 720)
                else:
                    context.con.free()
                    context._set_mujoco_context_and_buffers()
            finally:
                context.model.vis.quality.offsamples = samples
            self._render_quality_configured = True
            self.manifest['framebuffer_multisamples'] = 0
        c=context.cam
        # Fixed oblique view verified against this collection's layout 1.
        # Looking straight down the room puts a wall between camera and robot.
        centers = {'PrepareCoffee': ([.85, -.70, .95], 2.8),
                   'LoadDishwasher': ([2.05, -.75, .80], 3.2),
                   'FoodCleanup': ([2.1, -.70, 1.0], 3.4)}
        center, distance = centers.get(self.a.task, ([2.7, -.55, .85], 4.7))
        c.type=0;c.lookat[:]=center;c.distance=distance;c.azimuth=45;c.elevation=-40
        if self.a.task == 'PrepareCoffee':
            c.azimuth = 135
            c.elevation = -30
        wide=self.sim.render(height=720,width=960,camera_name=None)[::-1].copy()
        close=self.sim.render(height=256,width=320,camera_name=self.camera)[::-1].copy()
        wide[8:268,632:956]=[160,232,206]
        wide[10:266,634:954]=close
        return wide

    def record(self):
        # Sources retain every physical state and action. Only recovery episodes
        # need a video; source snapshots still use the actual simulator camera.
        if not getattr(self.a, 'trajectory_only', False):
            super().record()

    def tick(self, action):
        super().tick(action)
        self.trace[-1]['localized_objects'] = {
            name: self.position(name).tolist() for name in self.env.obj_body_id
        }

    def pose_action(self, position, rotation, grip=None):
        if not hasattr(self, '_contact_position_limit'):
            return super().pose_action(position, rotation, grip)
        from scipy.spatial.transform import Rotation
        error = np.asarray(position) - self.eef()
        current = self.sim.data.site_xmat[self.eef_id].reshape(3, 3)
        rotation_error = Rotation.from_matrix(np.asarray(rotation) @ current.T).as_rotvec()
        raw = np.r_[np.clip(.75 * error / .05, -self._contact_position_limit, self._contact_position_limit),
                    np.clip(.75 * rotation_error / .5, -.24, .24)]
        arm = self.previous_arm + np.clip(raw - self.previous_arm, -.045, .045)
        self.previous_arm = arm
        return self.action(arm[:3], arm[3:], grip)

    def execute(self, cmd):
        if cmd['action'] == 'contact_move':
            controller = self.robot.composite_controller.part_controllers['right']
            original_kp, original_kd = controller.kp.copy(), controller.kd.copy()
            kp = float(cmd.get('kp', 800))
            limit = float(cmd.get('position_limit', .8))
            if not (150 <= kp <= 800 and .24 <= limit <= .8):
                raise ValueError('Contact control must stay within the declared controller bounds')
            start_reference = len(self.references)
            try:
                # Controller stiffness only: physical actuator limits, gripper
                # force, joint friction, and all scene dynamics stay unchanged.
                controller.kp[:3] = kp
                controller.kd[:3] = 2 * np.sqrt(kp)
                self._contact_position_limit = limit
                reached = self.move(cmd['position'], cmd.get('grip', 1), rotation=cmd.get('rotation'))
                self.references[start_reference]['contact_control'] = dict(kp=kp, position_limit=limit)
            finally:
                controller.kp, controller.kd = original_kp, original_kd
                del self._contact_position_limit
            return dict(reached=reached, position_stiffness=kp, position_action_limit=limit,
                        physical_actuator_limits_unchanged=True)
        if cmd['action'] == 'verify_held':
            name = cmd['object'] + '_'
            fingers = set()
            for contact in self.sim.data.contact[:self.sim.data.ncon]:
                pair = [self.sim.model.geom_id2name(contact.geom1) or '',
                        self.sim.model.geom_id2name(contact.geom2) or '']
                if not any(geom.startswith(name) for geom in pair):
                    continue
                for finger in (1, 2):
                    if any(f'finger{finger}_pad_collision' in geom for geom in pair):
                        fingers.add(finger)
            return dict(held=len(fingers)==2, contacting_finger_pads=sorted(fingers),
                object_position=self.position(cmd['object']).tolist())
        if cmd['action'] == 'swing_handle':
            from scipy.spatial.transform import Rotation
            joint = self.sim.model.joint_name2id(cmd['joint'])
            anchor = self.sim.data.xanchor[joint].copy()
            axis = self.sim.data.xaxis[joint].copy()
            before = float(self.sim.data.get_joint_qpos(cmd['joint']))
            handle = self.position('site:' + cmd['handle_site']) + np.asarray(cmd.get('handle_offset', [0, 0, 0]))
            rotation = np.asarray(cmd.get('rotation', self.default_rot))
            self.move(handle + np.asarray(cmd.get('approach_delta', [0, -.12, 0])), -1, rotation=rotation)
            self.move(handle, -1, rotation=rotation)
            self.hold(25, 1)
            for angle in np.linspace(before, cmd.get('target_angle', 0), cmd.get('segments', 8)+1)[1:]:
                turn = Rotation.from_rotvec(axis*(angle-before)).as_matrix()
                self.move(anchor+turn@(handle-anchor), 1,
                    rotation=turn@rotation if cmd.get('rotate_with_handle', False) else rotation)
            self.hold(20, -1)
            self.move(self.eef()+np.asarray(cmd.get('retreat_delta', [0, -.20, 0])), -1, rotation=rotation)
            actual = float(self.sim.data.get_joint_qpos(cmd['joint']))
            return dict(joint_before=before, joint_after=actual,
                reached=abs(actual-cmd.get('target_angle', 0)) < .08)
        if cmd['action'] == 'torso':
            return self.lift_torso(cmd['height'])
        if cmd['action'] == 'navigate_fixture':
            from robocasa.utils.env_utils import compute_robot_base_placement_pose
            fixture = self.env.get_fixture(cmd['fixture'])
            pos, ori = compute_robot_base_placement_pose(self.env, ref_fixture=fixture, offset=cmd.get('offset'))
            return self.navigate(dict(position=list(pos), yaw=float(ori[2])))
        if cmd['action'] == 'move_relative':
            return dict(reached=self.move(self.eef()+np.asarray(cmd['delta']), cmd.get('grip'), rotation=cmd.get('rotation')))
        if cmd['action'] == 'move_object':
            return dict(reached=self.move(self.position(cmd['object'])+np.asarray(cmd.get('offset',[0,0,0])), cmd.get('grip'), rotation=cmd.get('rotation')))
        if cmd['action'] == 'move_held':
            target = np.asarray(cmd['position']) + self.eef() - self.position(cmd['object'])
            rotation = cmd.get('rotation')
            if isinstance(rotation, str) and rotation == 'current':
                rotation = self.sim.data.site_xmat[self.eef_id].reshape(3, 3).copy()
            return dict(reached=self.move(target, cmd.get('grip', 1), rotation=rotation))
        if cmd['action'] == 'orient_held_upright':
            from scipy.spatial.transform import Rotation
            body = self.env.obj_body_id[cmd['object']]
            obj_rotation = self.sim.data.body_xmat[body].reshape(3, 3).copy()
            eef_rotation = self.sim.data.site_xmat[self.eef_id].reshape(3, 3).copy()
            yaw = np.arctan2(obj_rotation[1, 0], obj_rotation[0, 0])
            upright = Rotation.from_euler('z', cmd.get('yaw_radians', yaw)).as_matrix()
            offset = obj_rotation.T @ (self.eef()-self.position(cmd['object']))
            target = np.asarray(cmd.get('position', self.position(cmd['object']))) + upright @ offset
            reached = self.move(target, 1, rotation=upright@obj_rotation.T@eef_rotation)
            actual = self.sim.data.body_xmat[body].reshape(3, 3)
            return dict(reached=reached, object_up_alignment=float(actual[2, 2]))
        if cmd['action'] == 'withdraw_object_axis':
            body = self.env.obj_body_id[cmd['object']]
            axis = self.sim.data.body_xmat[body].reshape(3, 3)[:, cmd.get('axis', 2)]
            return dict(reached=self.move(self.eef()+axis*cmd['distance'], -1, rotation=cmd.get('rotation')))
        return super().execute(cmd)

    def lift_torso(self, height):
        joint = next(n for n in self.sim.model.joint_names if n and n.endswith('joint_torso_height'))
        controller = self.robot.composite_controller.part_controllers['torso']
        arm = self.robot.composite_controller.part_controllers['right']
        old_frame = arm.input_ref_frame
        self.robot.composite_controller.update_state(); arm.update(force=True)
        arm.input_ref_frame = 'base'
        arm.goal_pos = arm.origin_ori.T @ (arm.ref_pos - arm.origin_pos)
        arm.goal_ori = arm.origin_ori.T @ arm.ref_ori_mat
        self.references.append(dict(step=self.step, kind='torso', height=height))
        scale = float(np.asarray(controller.scale_action(np.ones(1)))[0])
        for _ in range(240):
            error = height - float(self.sim.data.get_joint_qpos(joint))
            delta = np.clip(error, -.012, .012) / scale
            action = self.robot.create_action_vector(dict(right=np.zeros(6), right_gripper=np.array([self.grip]),
                base=np.zeros(3), torso=np.array([delta]), base_mode=np.array([1.])))
            self.tick(action)
            if abs(error) < .003: break
        arm.input_ref_frame = old_frame; arm.reset_goal()
        actual = float(self.sim.data.get_joint_qpos(joint))
        return dict(height=actual, reached=abs(height-actual) < .01)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--spec', required=True)
    p.add_argument('--case', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--baseline')
    p.add_argument('--initial-scene', help='Reuse only a recorded original scene initialization for a new source attempt')
    p.add_argument('--trajectory-only', action='store_true')
    a = p.parse_args()
    if a.baseline and a.trajectory_only:
        raise ValueError('Recovery episodes must record every video frame')
    if a.baseline and a.initial_scene:
        raise ValueError('Recovery initialization must come from its successful baseline')
    spec = next(x for x in json.loads(Path(a.spec).read_text()) if x['id']==a.case)
    if (Path(a.output)/'manifest.json').exists():
        raise RuntimeError('Every attempt requires a new output directory')
    args = SimpleNamespace(backend=spec['backend'], task=spec['task'], seed=spec.get('seed',7),
        layout=spec.get('layout',1), style=spec.get('style',1), horizon=18000,
        output=a.output, baseline=a.baseline, initial_scene=a.initial_scene,
        command_timeout=7200, initial_torso=spec.get('initial_torso'), trajectory_only=a.trajectory_only)
    try:
        s = DistinctSession(args)
    except Exception as exc:
        out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
        (out/'status.json').write_text(json.dumps(dict(state='initialization_failed', step=0, error=str(exc))))
        raise
    s.manifest.update(collection='distinct-two-perturbations', task_id=spec['id'],
        recording_mode='trajectory-only source' if a.trajectory_only else 'continuous native video',
        planned_perturbations=spec['perturbations'], decision_origin='GPT-authored, simulator-state-assisted demonstration')
    if a.baseline:
        b = Path(a.baseline)
        if not json.loads((b/'result.json').read_text())['success']:
            raise RuntimeError('A verified successful source trajectory is required')
        s.manifest['source_success_baseline'] = dict(case=b.name, success=True,
            reference_waypoints_sha256=hashlib.sha256((b/'reference_waypoints.json').read_bytes()).hexdigest(),
            commands_sha256=hashlib.sha256((b/'events.json').read_bytes()).hexdigest(),
            origin='Newly collected, state-assisted simulator success; not trained-model inference')
    s.save_manifest()
    try:
        s.run()
    finally:
        s.seal()
