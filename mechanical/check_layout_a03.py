"""A03の基板候補を生成し、STEP駆動部との静的干渉を検査する。

python check_layout_a03.py /path/to/TORANEKO.Mk3_v36.step
既存部品間の嵌合は検査対象外。新規基板・左右ユニット間・電池を検査。
"""
import hashlib
import json
import math
from pathlib import Path
import sys

import cadquery as cq
from measure_step import read_parts

ROOT = Path(__file__).resolve().parent
EXPECTED_SHA = "e37a94ba0502e935bd09b7f2973f216830a515db4f88e3210957fa27de5b49ad"
# A02の軸位置・床はSTEPタイヤ外接箱から得た値。
FLOOR_SOURCE_Z = -1.7869267385966008
AXLE_SOURCE_Y = -5.322123082156386
PCB_Z = -FLOOR_SOURCE_Z
PCB_T = 0.6
AXLE_Y = 40.0
INWARD = 0.3
OUTLINE = [(-13,5),(13,5),(17,9),(17,32),(13.4,32),(13.4,48),
           (17,48),(17,57),(13,61),(-13,61),(-17,57),(-17,48),
           (-13.4,48),(-13.4,32),(-17,32),(-17,9)]
# 元STEPのマウント底側ネジ軸と一致。孔径1.7は設計仮定。
HOLES = [(x,y) for x in (-11.6,11.6) for y in (36.25,53.75)]


def overlap_boxes(a,b):
    aa,bb=a.BoundingBox(),b.BoundingBox()
    return all(min(getattr(aa,d+'max'),getattr(bb,d+'max'))-
               max(getattr(aa,d+'min'),getattr(bb,d+'min')) > 1e-6 for d in 'xyz')


def check_pair(name_a,a,name_b,b):
    aa,bb=a.BoundingBox(),b.BoundingBox()
    lower=math.sqrt(sum(max(0,getattr(aa,d+'min')-getattr(bb,d+'max'),
                           getattr(bb,d+'min')-getattr(aa,d+'max'))**2 for d in 'xyz'))
    volume = 0.0
    if overlap_boxes(a,b):
        volume = sum(s.Volume() for s in a.intersect(b).Solids())
    # 遠い部品は外接箱の距離下限で十分。近接部品のみ厳密距離を計算する。
    distance=a.distance(b) if lower<=1.01 else None
    inconsistent=distance is not None and distance+1e-5<lower
    return {"a":name_a,"b":name_b,"intersection_mm3":volume,
            "distance_mm":None if inconsistent else distance,
            "bbox_distance_lower_bound_mm":lower,
            "distance_inconsistent":inconsistent,"penetration":volume>1e-5}


def main(path):
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != EXPECTED_SHA:raise ValueError("参照STEPが測定対象版と異なります")
    left,right=[],[]
    raw_motors=[]
    invalid=[]
    for name,shape in read_parts(path):
        if "足回り" not in name or not shape.Vertices():continue
        if not shape.isValid():invalid.append(name)
        is_left="/2:足回り" in name
        if "NFP-D0812" in name:raw_motors.append((name,shape,is_left))
        delta=(13.4+(INWARD if is_left else -INWARD),AXLE_Y-AXLE_SOURCE_Y,PCB_Z)
        item=(name,shape.translate(delta))
        (left if is_left else right).append(item)
    drive=left+right
    board=(cq.Workplane('XY').polyline(OUTLINE).close().extrude(PCB_T)
           .translate((0,0,PCB_Z)))
    for x,y in HOLES:
        hole=cq.Workplane('XY').center(x,y).circle(.85).extrude(2).translate((0,0,PCB_Z-.5))
        board=board.cut(hole)
    board=board.val()
    assert board.isValid() and len(board.Solids())==1
    batteries=[]
    for i,x in enumerate((-12.3,.3)):
        shape=cq.Workplane('XY').box(12,25,6,centered=False).val().translate((x,33.5,13.5))
        batteries.append((f'battery-envelope-{i+1}',shape))
    records=[]
    for name,shape in drive:
        records.append(check_pair('pcb-a03',board,name,shape))
        for bn,bs in batteries:records.append(check_pair(bn,bs,name,shape))
    # 左右間は広域判定で候補を絞り、最短距離はユニット全体でも求める。
    cross=[]
    for ln,ls in left:
        for rn,rs in right:
            if overlap_boxes(ls,rs):cross.append(check_pair(ln,ls,rn,rs))
    left_shape=cq.Compound.makeCompound([s for n,s in left])
    right_shape=cq.Compound.makeCompound([s for n,s in right])
    scan=[]
    for amount in (0,.2,.3,.4,.5,1.95):
        ms=[s.translate((amount if il else -amount,0,0)) for n,s,il in raw_motors]
        row=check_pair('motor-left',ms[0],'motor-right',ms[1]);row['inward_per_side_mm']=amount
        scan.append(row)
    # マウント底面に近い薄片と基板投影の共通体積から支持面積を測る。
    support=[]
    projection=cq.Workplane('XY').polyline(OUTLINE).close().extrude(PCB_T+.1).translate((0,0,PCB_Z)).val()
    for x,y in HOLES:
        projection=projection.cut(cq.Workplane('XY').center(x,y).circle(.85).extrude(2).translate((0,0,PCB_Z-.5)).val())
    for n,s in drive:
        if 'モータマウント' not in n:continue
        slab=cq.Workplane('XY').box(50,70,.05,centered=False).val().translate((-25,0,PCB_Z+PCB_T+.001))
        foot=s.intersect(slab)
        all_area=sum(v.Volume() for v in foot.Solids())/.05
        supported=sum(v.Volume() for v in foot.intersect(projection).Solids())/.05
        support.append({'name':n,'near_base_section_area_mm2':all_area,
                        'supported_section_area_mm2':supported,'fraction':supported/all_area})
    report={'source_sha256':sha,'method':'Open CASCADE static solid intersection and minimum distance',
            'source_invalid_shapes':invalid,
            'volume_threshold_mm3':1e-5,'drive_parts':len(drive),'pcb_tests':len(drive),
            'battery_tests':2*len(drive),'cross_unit_candidates':cross,
            'cross_unit_distance_mm':left_shape.distance(right_shape),'motor_shift_scan':scan,
            'records':records,'mount_support':support,'pcb_volume_mm3':board.Volume(),
            'pcb_z_mm':PCB_Z,'pcb_thickness_mm':PCB_T,'outline_xy_mm':OUTLINE,
            'mount_holes_xy_mm':HOLES,'mount_hole_diameter_mm':1.7,
            'unverified':['gear rotational swept volume','fan and duct','sensor holders',
                          'screw heads','wiring','manufacturing tolerances','strength','mass target']}
    (ROOT/'layout-a03-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    cq.exporters.export(board,str(ROOT/'pcb-a03-concept.step'))
    cq.exporters.export(board,str(ROOT/'pcb-a03-concept.stl'))
    failed=[r for r in records+cross if r['penetration']]
    print(json.dumps({'penetrations':failed,'cross_unit_distance_mm':report['cross_unit_distance_mm'],
                      'support':support,'scan':scan},ensure_ascii=False,indent=2))


if __name__=='__main__':main(Path(sys.argv[1]))
