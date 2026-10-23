from pathlib import Path
import sys,json,random,re,hashlib,yaml
root=Path(__file__).resolve().parents[2];vendor=root/'vendor/LIBERO-PRO';sys.path.insert(0,str(vendor));from perturbation import BDDLParser,TaskPerturbator,SwapPerturbator
out=root/'tasks';out.mkdir(exist_ok=True)
choices=[('libero-relational','libero_spatial','pick_up_the_black_bowl_between_the_plate_and_the_ramekin_and_place_it_on_the_plate','task',0),('libero-multiobject','libero_10','LIVING_ROOM_SCENE2_put_both_the_cream_cheese_box_and_the_butter_in_the_basket','swap',17),('libero-articulation','libero_goal','open_the_top_drawer_and_put_the_bowl_inside','task',1)]
manifest=[]
for name,suite,task,kind,seed in choices:
 source=vendor/'libero/libero/bddl_files'/suite/(task+'.bddl');content=source.read_text();parser=BDDLParser(content)
 if kind=='task':content=TaskPerturbator(parser,str(vendor/'libero_ood/ood_task.yaml')).perturb(suite,task,seed)
 else:random.seed(seed);content=SwapPerturbator(parser,str(vendor/'libero_ood/ood_spatial_relation.yaml')).perturb(suite,task)
 assert content!=source.read_text(),'Perturbation did not change '+name
 p=out/(name+'.bddl');p.write_text(content)
 manifest.append({'id':name,'backend':'libero_pro','source_suite':suite,'source_task':task,'perturbation':kind,'perturbation_seed':seed,'environment_seed':7,'instruction':re.search(r'\(:language\s*(.*?)\)',content,re.S).group(1),'bddl_sha256':hashlib.sha256(content.encode()).hexdigest()})
for name,task in [('robocasa-salsa','ColorfulSalsa'),('robocasa-clearing','ClearCuttingBoard'),('robocasa-sorting','SizeSorting')]:manifest.append({'id':name,'backend':'robocasa365','source_task':task,'environment_seed':7,'layout':1,'style':1})
(root/'task_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
config=root/'libero-config';config.mkdir(exist_ok=True);b=vendor/'libero/libero'
(config/'config.yaml').write_text(yaml.safe_dump({'benchmark_root':str(b),'bddl_files':str(b/'bddl_files'),'init_states':str(b/'init_files'),'datasets':str(vendor/'datasets'),'assets':str(b/'assets')}))
print(json.dumps(manifest,ensure_ascii=False,indent=2))
