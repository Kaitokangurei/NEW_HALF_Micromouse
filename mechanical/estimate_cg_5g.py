"""A04の主要5グループを各5gとする条件付き重心。実測値ではない。

グループ内は一様密度の形状体積で近似。元STEPの材質密度は使わない。
不正な軸受保持器2個と対応する反対側2個を図心近似から除く。
それらの質量を0gと断定するのではなく、各駆動部全体5gを残りの形状へ配分する近似。
"""
import csv
import hashlib
import json
from pathlib import Path
import sys
import cadquery as cq

from calculate_cg import calculate
from measure_step import read_parts
from check_layout_a03 import EXPECTED_SHA, PCB_Z, AXLE_SOURCE_Y

ROOT=Path(__file__).resolve().parent


def main(source):
    if hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED_SHA:raise ValueError('参照版が異なります')
    groups={'left_drive':[],'right_drive':[],'fan_assembly':[]}
    excluded=[]
    for name,shape in read_parts(source):
        if not shape.Vertices():continue
        if '足回り' in name:
            if 'LF-630_cage' in name:
                excluded.append(name);continue
            left='/2:足回り' in name
            group='left_drive' if left else 'right_drive'
            offset=(13.7 if left else 13.1,33-AXLE_SOURCE_Y,PCB_Z)
        elif any(s in name for s in ['/11:MK06-45','/12:吸引ファンモータマウント','/15:吸引ファン(アクリル) v3/2:SOLID']):
            group='fan_assembly'
            offset=(13.4,16.5-(AXLE_SOURCE_Y-11.25),PCB_Z)
        else:continue
        if not shape.isValid():raise ValueError('図心計算対象が不正: '+name)
        shape=shape.translate(offset);c=shape.Center();v=shape.Volume()
        if v<=0:raise ValueError('非正の体積: '+name)
        groups[group].append({'name':name,'volume_mm3':v,'centroid_mm':[c.x,c.y,c.z]})
    assert len(groups['left_drive'])==len(groups['right_drive'])==30
    assert len(groups['fan_assembly'])==3 and len(excluded)==4
    rows=[]
    for group,parts in groups.items():
        volume=sum(p['volume_mm3'] for p in parts)
        center=[sum(p['volume_mm3']*p['centroid_mm'][i] for p in parts)/volume for i in range(3)]
        rows.append({'group':group,'mass_g':'5','cg_x_mm':str(center[0]),'cg_y_mm':str(center[1]),
                     'cg_z_mm':str(center[2]),'notes':'仮定5g・グループ内部は一様密度の体積図心で近似'})
    for group,x in [('battery_left',-6.3),('battery_right',6.3)]:
        rows.append({'group':group,'mass_g':'5','cg_x_mm':str(x),'cg_y_mm':'33','cg_z_mm':'16.5',
                     'notes':'仮定5g・直方体の一様な質量分布を仮定'})
    result=calculate(rows)
    result.update({'scope':'Five assumed groups ONLY; not complete robot','mass_basis':'User scenario 5g each; unmeasured',
                   'cadquery_version':cq.__version__,
                   'input_rows':rows,'centroid_method':'sum of component volume moments, uniform density per group; not STEP material densities',
                   'source_sha256':EXPECTED_SHA,'geometry_components':groups,'centroid_geometry_exclusions':excluded,
                   'not_included':['main PCB and populated components','sensors/holders','battery holder',
                                   'skirt/sliders','additional fan case/support','unmodeled wires/connectors/fasteners']})
    moment=result['fore_aft_mass_moment_g_mm']
    result['battery_pair_translation_to_balance_mm']=-moment/10
    result['balanced_battery_center_y_mm']=33-moment/10
    (ROOT/'cg-a04-5g.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with (ROOT/'mass-scenario-5g.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in result.items() if k not in ['geometry_components','centroid_geometry_exclusions']},ensure_ascii=False,indent=2))


if __name__=='__main__':main(Path(sys.argv[1]))
