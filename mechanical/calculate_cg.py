"""質量と各グループの重心を入力したCSVから合成重心を求める。標準ライブラリのみ。

python mechanical/calculate_cg.py mechanical/mass-input.csv
未入力を0で埋めない。全行が埋まるまで全体重心は返さない。
不要グループはmass_gに0を明示すれば座標不要。含め忘れは別途点検する。
"""
import csv
import json
import math
from pathlib import Path
import sys


def calculate(rows):
    pending=[];included=[];omitted=[]
    for row in rows:
        group=row['group']
        if not row['mass_g'].strip():
            pending.append({'group':group,'missing':['mass_g']});continue
        mass=float(row['mass_g'])
        if not math.isfinite(mass) or mass<0:raise ValueError(f'{group}: 質量は有限の非負値が必要')
        if mass==0:
            omitted.append(group);continue
        keys=['cg_x_mm','cg_y_mm','cg_z_mm']
        missing=[k for k in keys if not row[k].strip()]
        if missing:
            pending.append({'group':group,'missing':missing});continue
        xyz=[float(row[k]) for k in keys]
        if not all(math.isfinite(x) for x in xyz):raise ValueError(f'{group}: 有限の座標が必要')
        included.append((mass,xyz))
    if pending:return {'status':'incomplete','cg_mm':None,'missing_inputs':pending,'explicit_zero_groups':omitted}
    total=sum(m for m,c in included)
    if total<=0:raise ValueError('正の総質量が必要')
    center=[sum(m*c[i] for m,c in included)/total for i in range(3)]
    return {'status':'calculated_from_supplied_inputs','total_mass_g':total,'cg_mm':center,
            'fore_aft_offset_from_axle_mm':center[1]-33,
            'fore_aft_mass_moment_g_mm':total*(center[1]-33),
            'explicit_zero_groups':omitted,
            'note':'Input accuracy / completeness determines validity; positive Y offset is rearward'}


if __name__=='__main__':
    with Path(sys.argv[1]).open(newline='',encoding='utf-8') as f:result=calculate(list(csv.DictReader(f)))
    print(json.dumps(result,ensure_ascii=False,indent=2))
