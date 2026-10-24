"""Prepare the exact gallery tasks and seeds; requires installed LIBERO-PRO vendor assets."""
from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parents[2];vendor=root/'vendor/LIBERO-PRO';sys.path.insert(0,str(vendor))
from perturbation import BDDLParser,SwapPerturbator
out=root/'tasks/gallery';out.mkdir(parents=True,exist_ok=True)
lib=[('put_the_bowl_on_the_plate','碗放入盘中','akita_black_bowl_1','plate_1'),('put_the_bowl_on_the_stove','碗移到炉台','akita_black_bowl_1','flat_stove_1'),('put_the_cream_cheese_in_the_bowl','奶酪放入碗中','cream_cheese_1','akita_black_bowl_1'),('put_the_wine_bottle_on_the_rack','酒瓶移到置物架','wine_bottle_1','wine_rack_1'),('put_the_wine_bottle_on_top_of_the_cabinet','酒瓶移到柜顶','wine_bottle_1','wooden_cabinet_1'),('put_the_bowl_on_top_of_the_cabinet','碗移到柜顶','akita_black_bowl_1','wooden_cabinet_1')]
items=[]
for i,(task,title,obj,target) in enumerate(lib):
 for seed in [11,23,37][:2 if i==5 else 3]:
  raw=(vendor/'libero/libero/bddl_files/libero_goal'/(task+'.bddl')).read_text();random.seed(seed)
  content=SwapPerturbator(BDDLParser(raw),str(vendor/'libero_ood/ood_spatial_relation.yaml')).perturb('libero_goal',task)
  assert content!=raw
  id=f'libero-gallery-{i+1:02d}-s{seed}';path=out/(id+'.bddl');path.write_text(content)
  items.append(dict(id=id,backend='libero_pro',suite='LIBERO-PRO',task=str(path),source_task=task,title=title,seed=seed,perturbation='official SwapPerturbator',perturbation_seed=seed,bddl_sha256=hashlib.sha256(content.encode()).hexdigest(),pairs=[[obj,target]]))
rc=[('OrganizeVegetables','蔬菜分盘摆放',[['vegetable1','cutting_board1'],['vegetable2','cutting_board2']]),('ArrangeVegetables','水槽蔬菜移到砧板',[['vegetable1','cutting_board'],['vegetable2','cutting_board']]),('ColorfulSalsa','多食材移到砧板',[[x,'receptacle'] for x in ['avocado','tomato','bell_pepper','onion']]),('ClearCuttingBoard','清理并布置砧板',[['vegetable1','non_vegetable_container'],['vegetable2','non_vegetable_container']]),('SizeSorting','容器按大小堆叠',[['obj_1','obj_0']]),('BowlAndCup','杯子放入碗中',[['cup','bowl']]),('DessertAssembly','甜点与容器摆上托盘',[['dessert1_container','receptacle'],['dessert2','receptacle']]),('MeatTransfer','肉类移入容器',[['meat','container']]),('ArrangeCuttingFruits','冰箱水果移到砧板',[['fruit1','cutting_board'],['fruit2','cutting_board']])]
for i,(task,title,pairs) in enumerate(rc):
 for seed in [11,23,37]:
  items.append(dict(id=f'robocasa-gallery-{i+1:02d}-s{seed}',backend='robocasa365',suite='RoboCasa365',task=task,source_task=task,title=title,seed=seed,layout=2 if task=='BowlAndCup' else 1,style=1,pairs=pairs))
(root/'gallery_manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2));print(len(items))
