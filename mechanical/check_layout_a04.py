"""車軸・電池を前後中央へ寄せたA04。元STEPは検査入力のみ。"""
import hashlib
import json
import math
from pathlib import Path
import sys

import cadquery as cq
from measure_step import read_parts
from check_layout_a03 import check_pair, EXPECTED_SHA, PCB_Z, PCB_T, AXLE_SOURCE_Y

ROOT=Path(__file__).resolve().parent
AXLE_Y=33.0
BATTERY_Y=33.0
FAN_Y=16.5
OUTLINE=[(-13,5),(13,5),(17,9),(17,25),(13.4,25),(13.4,41),
         (17,41),(17,57),(13,61),(-13,61),(-17,57),(-17,41),
         (-13.4,41),(-13.4,25),(-17,25),(-17,9)]
HOLES=[(x,y) for x in (-11.6,11.6) for y in (29.25,46.75)]


def bounds(name,shape):
    b=shape.BoundingBox()
    return {'name':name,'min_mm':[b.xmin,b.ymin,b.zmin],
            'max_mm':[b.xmax,b.ymax,b.zmax]}


def verify_invalid_with_bounds(report):
    """不正な保持器形状はBoolean結果を信用せず、保守的な外接箱で分離を確認。"""
    parts={p['name']:p for p in report['parts']}
    evidence=[]
    for row in report['records']:
        if row['b'] not in report['source_invalid_shapes']:continue
        lower=row['bbox_distance_lower_bound_mm']
        if row['a']=='fan-reservation-D30':
            p=parts[row['b']];lo,hi=p['min_mm'],p['max_mm']
            dx=max(lo[0],-hi[0],0)
            dy=max(lo[1]-FAN_Y,FAN_Y-hi[1],0)
            lower=max(lower,math.hypot(dx,dy)-15)
        if lower<=0:raise ValueError('不正形状との分離を外接箱で証明できません')
        evidence.append({'a':row['a'],'b':row['b'],'conservative_gap_lower_bound_mm':lower})
    report['invalid_shape_separation_evidence']=evidence


def main(path):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED_SHA:
        raise ValueError('参照STEPの版が異なります')
    all_parts=list(read_parts(path))
    drive=[];fans=[];invalid=[]
    for name,shape in all_parts:
        if not shape.Vertices():continue
        if '足回り' in name:
            if not shape.isValid():invalid.append(name)
            shift=.3 if '/2:足回り' in name else -.3
            drive.append((name,shape.translate((13.4+shift,AXLE_Y-AXLE_SOURCE_Y,PCB_Z))))
        if any(s in name for s in ['/11:MK06-45','/12:吸引ファンモータマウント','/15:吸引ファン(アクリル) v3/2:SOLID']):
            # 元ファン軸のYは車軸から前方11.25 mm。
            fans.append((name,shape.translate((13.4,FAN_Y-(AXLE_SOURCE_Y-11.25),PCB_Z))))
    assert len(drive)==64 and len(fans)==3
    board=cq.Workplane('XY').polyline(OUTLINE).close().extrude(PCB_T).translate((0,0,PCB_Z))
    for x,y in HOLES:
        board=board.cut(cq.Workplane('XY').center(x,y).circle(.85).extrude(2).translate((0,0,PCB_Z-.5)))
    board=board.val()
    assert board.isValid() and len(board.Solids())==1
    batteries=[(f'battery-envelope-{i}',cq.Workplane('XY').box(12,25,6,centered=False).val().translate((x,BATTERY_Y-12.5,13.5)))
               for i,x in enumerate((-12.3,.3),1)]
    # 文書のΦ30を見込む予約体積。ケース・流路は含まない。
    fan_body=next(s for n,s in fans if '/2:SOLID' in n)
    fb=fan_body.BoundingBox()
    reserve=cq.Workplane('XY').center(0,FAN_Y).circle(15).extrude(fb.zlen).translate((0,0,fb.zmin)).val()
    records=[]
    for n,s in drive:
        records.append(check_pair('pcb-a04',board,n,s))
        for bn,bs in batteries:records.append(check_pair(bn,bs,n,s))
    print('Drive/board/battery checks completed',flush=True)
    for fn,fs in fans:
        records.append(check_pair('pcb-a04',board,fn,fs))
        for bn,bs in batteries:records.append(check_pair(bn,bs,fn,fs))
        for dn,ds in drive:records.append(check_pair(fn,fs,dn,ds))
    for n,s in [('pcb-a04',board)]+batteries+drive:
        records.append(check_pair('fan-reservation-D30',reserve,n,s))
    report={'source_sha256':EXPECTED_SHA,'revision':'A04','axle_y_mm':AXLE_Y,
            'battery_center_y_mm':BATTERY_Y,'fan_center_y_mm':FAN_Y,
            'battery_z_mm':[13.5,19.5],'source_invalid_shapes':invalid,
            'outline_xy_mm':OUTLINE,'mount_holes_xy_mm':HOLES,
            'mount_hole_diameter_mm':1.7,'pcb_thickness_mm':PCB_T,
            'parts':[bounds(n,s) for n,s in drive+batteries+fans],
            'records':records,'intersection_threshold_mm3':1e-5,
            'mass_properties':'Not calculated: actual component masses and mass centers missing',
            'unverified':['fan case/support/duct','wiring/connectors','sensor holders',
                          'fasteners','rotating swept volumes','tolerances','strength','complete mass properties']}
    verify_invalid_with_bounds(report)
    (ROOT/'layout-a04-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    cq.exporters.export(board,str(ROOT/'pcb-a04-concept.step'))
    cq.exporters.export(board,str(ROOT/'pcb-a04-concept.stl'))
    failures=[r for r in records if r['penetration'] or r['distance_inconsistent']]
    print(json.dumps({'checks':len(records),'failures':failures},ensure_ascii=False,indent=2))
    if failures:raise RuntimeError('干渉または距離計算の矛盾を確認してください')


if __name__=='__main__':main(Path(sys.argv[1]))
