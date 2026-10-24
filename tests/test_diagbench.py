"""Protocol and corruption regression checks; no model downloads or GPU."""
import copy
from types import SimpleNamespace
import json
import zipfile
from pathlib import Path
import pytest
from ec_verl.diagbench import evaluate as e
from ec_verl.diagbench.download import safe_extract
from ec_verl.diagbench.media import sample_indices, to_chat


def record(identifier, role='critic', unit='step', gt='fail'):
    return dict(id=identifier, role=role, unit=unit, source='robocasa', sub='manip',
                videos=['videos/test.mp4'], gt_answer='reference', gt_verdict=gt,
                gt_reason='reason', gt_subtask='pick cup', context=[{'role':'user','content':'question'}],
                **({'traj_id':'episode1','turn_index':int(identifier)} if unit=='traj' else {}))


def scored(r, judge):
    return {k:v for k,v in {**r,'judge':judge,'out':'model output'}.items() if k!='context'}


def test_question_determines_role_even_when_reference_says_failed():
    messages=[{'role':'user','content':'Question: Looking at the current situation, is the overall task complete?'},
              {'role':'assistant','content':'<answer>failed; redo "pick cup"</answer>'}]
    assert e.trajectory_role(messages,1)=='planner'
    messages[0]['content']='Question: Did what the robot just executed succeed?'
    assert e.trajectory_role(messages,1)=='critic'


def test_cause_denominator_and_trajectory_semantics():
    expected=[record('a'), record('b',gt='ok'),record('1','planner','traj'),record('2','planner','traj')]
    rows=[scored(expected[0],dict(verdict='YES',reason='YES')),
          scored(expected[1],dict(verdict='NO',reason='NO')),
          scored(expected[2],dict(action='YES',target='NO')),
          scored(expected[3],dict(action='NO',target='NA'))]
    summary=e.aggregate(rows,expected)
    m={v['metric']:v for v in summary['metrics']}
    assert m['cause_failure_only']['n']==1
    assert m['judge']['percent']==50
    assert m['trajectory_success']['percent']==0
    assert m['trajectory_mean_progress']['percent']==50


def test_rejects_missing_duplicate_tampered_and_invalid_scores():
    expected=[record('a')]; rows=[scored(expected[0],dict(verdict='YES',reason='NO'))]
    for bad in ([],rows+rows):
        with pytest.raises(ValueError):e.aggregate(bad,expected)
    for field,value in [('sub','nav'),('gt_verdict','ok'),('videos',[])]:
        bad=copy.deepcopy(rows);bad[0][field]=value
        with pytest.raises(ValueError):e.aggregate(bad,expected)
    rows[0]['judge']['reason']='MAYBE'
    with pytest.raises(ValueError):e.aggregate(rows,expected)


def test_window_retains_text_and_recent_video_order():
    messages=[dict(role='user',content=f'before {i}<video>after') for i in range(5)]
    clipped,videos=e.window(messages,list('abcde'))
    assert videos==list('cde')
    assert sum(m['content'].count('<video>') for m in clipped)==3
    assert all('before' in m['content'] and 'after' in m['content'] for m in clipped)
    assert messages[0]['content'].count('<video>')==1


def test_no_current_answer_leaks_into_model_prompt(monkeypatch,tmp_path):
    row=record('a'); row['gt_answer']='SECRET_ANSWER'
    captured={}
    monkeypatch.setattr(e,'to_chat',lambda context,*args:context)
    def post(args,chat,*rest):
        captured['chat']=chat
        return 'prediction',{'truncated':False}
    monkeypatch.setattr(e,'post',post)
    e.collect_one(row,SimpleNamespace(root=tmp_path,max_tokens=20))
    assert 'SECRET_ANSWER' not in json.dumps(captured)
    assert 'question' in json.dumps(captured)


def test_video_placeholder_and_path_checks(tmp_path):
    with pytest.raises(ValueError):to_chat([{'role':'user','content':'<video>'}],[])
    with pytest.raises(ValueError):to_chat([{'role':'user','content':'hello'}],['extra'])
    with pytest.raises(ValueError):e.resolve_video('../escape.mp4',tmp_path)
    assert sample_indices(1,0.1)==[0]
    assert len(sample_indices(100,5,max_frames=6))<=6


def test_judge_retries_format_without_coercing_prose(monkeypatch,tmp_path):
    monkeypatch.setattr(e,'image_parts',lambda *a:[])
    outputs=iter(['{"verdict":"NO","reason":"The grasp failed."}',
                  '{"verdict":"NO","reason":"YES"}'])
    calls=[]
    def post(args,chat,*rest,**kwargs):
        calls.append(copy.deepcopy(chat));return next(outputs),{'truncated':False}
    monkeypatch.setattr(e,'post',post)
    row={**record('a'),'out':'prediction'}
    result=e.judge_one(row,SimpleNamespace(root=tmp_path,judge_max_tokens=512))
    assert result['judge']=={'verdict':'NO','reason':'YES'}
    assert result['judge_format_retries']==1
    assert len(result['judge_attempts'])==2
    assert calls[1][:2]==calls[0]
    monkeypatch.setattr(e,'post',lambda *a,**kw:('{"verdict":"NO","reason":"explanation"}',{}))
    with pytest.raises(ValueError,match='after 3 attempts'):
        e.judge_one(row,SimpleNamespace(root=tmp_path,judge_max_tokens=512))


def test_archive_traversal_rejected(tmp_path):
    p=tmp_path/'bad.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','bad')
    with pytest.raises(ValueError):safe_extract(p,tmp_path/'out')
    assert not (tmp_path/'escape').exists()


def test_resume_refuses_changed_settings_and_preserves_predictions(monkeypatch,tmp_path):
    root=tmp_path/'dataset';root.mkdir()
    (root/'step.jsonl').write_text('{}\n');(root/'traj.jsonl').write_text('{}\n')
    (root/'media_manifest.jsonl').write_text('{}\n')
    row=record('a')
    monkeypatch.setattr(e,'jobs',lambda args:([row],{'smoke':True}))
    monkeypatch.setattr(e,'collect_one',lambda r,a:scored(r,{}))
    args=SimpleNamespace(root=root,step_file=root/'step.jsonl',traj_file=root/'traj.jsonl',
                         output=tmp_path/'run',media_overrides=None,stage='collect',model='rynnbrain',
                         api='http://localhost',smoke=True,max_tokens=512,judge_max_tokens=256,
                         resume=False,workers=1,timeout=20)
    class Monitor:
        def status(self,*args):pass
        def scalars(self,*args):pass
    e.run(args,Monitor())
    path=args.output/'predictions.jsonl';before=path.read_bytes()
    with pytest.raises(ValueError,match='already exists'):e.run(args,Monitor())
    args.resume=True;args.max_tokens=100
    with pytest.raises(ValueError,match='settings differ'):e.run(args,Monitor())
    assert path.read_bytes()==before
    args.max_tokens=512
    monkeypatch.setattr(e,'collect_one',lambda *args:pytest.fail('completed request repeated'))
    e.run(args,Monitor())
    assert path.read_bytes()==before


def test_aggregate_refuses_prediction_mutation_after_scoring(tmp_path,monkeypatch):
    import hashlib
    root=tmp_path/'dataset';root.mkdir();out=tmp_path/'run';out.mkdir()
    for name in ('step.jsonl','traj.jsonl','media_manifest.jsonl'):(root/name).write_text('{}\n')
    row=record('a');prediction=scored(row,{})
    prediction.pop('judge')
    (out/'predictions.jsonl').write_text(json.dumps(prediction)+'\n')
    (out/'judged.jsonl').write_text(json.dumps({**prediction,'judge':{'verdict':'YES','reason':'YES'}})+'\n')
    sha=e.digest(root/'step.jsonl')
    metadata=dict(protocol=e.PROTOCOL,smoke=True,step_sha256=sha,traj_sha256=sha,
                  media_manifest_sha256=sha,expected_decisions=1,model='test',
                  predictions_sha256=e.digest(out/'predictions.jsonl'))
    for stage in ('collect','judge'):e.save(out/f'{stage}_metadata.json',metadata)
    args=SimpleNamespace(root=root,step_file=root/'step.jsonl',traj_file=root/'traj.jsonl',
                         output=out,media_overrides=None,stage='aggregate',smoke=True)
    monkeypatch.setattr(e,'jobs',lambda args:([row],{'smoke':True}))
    class Monitor:
        def status(self,*args):pass
        def scalars(self,*args):pass
    e.run(args,Monitor())
    assert json.loads((out/'summary.json').read_text())['complete']
    (out/'predictions.jsonl').write_text(json.dumps({**prediction,'out':'tampered'})+'\n')
    with pytest.raises(ValueError,match='Predictions changed'):e.run(args,Monitor())
