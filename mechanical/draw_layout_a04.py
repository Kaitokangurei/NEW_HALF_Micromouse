"""A04の重量集中配置を表示。重心の計算結果ではない。"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle,Circle

ROOT=Path(__file__).resolve().parent
r=json.loads((ROOT/'layout-a04-checks.json').read_text())
fig,(ax,bx)=plt.subplots(1,2,figsize=(12,8),gridspec_kw={'width_ratios':[1,1.45]})
ax.add_patch(Rectangle((-19.5,0),39,66,fill=False,ls='--',ec='#64748b'))
ax.add_patch(Polygon(r['outline_xy_mm'],fc='#dcfce7',ec='#15803d',alpha=.7))
ax.add_patch(Circle((0,16.5),15,fill=False,ls='--',ec='#2563eb',label='D30 fan reservation'))
ax.add_patch(Circle((0,16.5),11,fc='#dbeafe',ec='#2563eb',alpha=.5))
seen=set()
for p in r['parts']:
    n=p['name'];color=None;label=None
    for token,c,l in [('ミニッツタイヤ','#0f172a','Tires'),('NFP-D0812','#dc2626','Drive motors'),
                      ('battery-envelope','#d97706','Batteries (upper level)'),('/11:MK06','#2563eb','Fan motor')]:
        if token in n:color,label=c,l;break
    if not color:continue
    x,y,z=p['min_mm'];xx,yy,zz=p['max_mm']
    alpha=.25 if 'battery' in n else .6
    ax.add_patch(Rectangle((x,y),xx-x,yy-y,fc=color,ec=color,alpha=alpha,label=label if label not in seen else None))
    bx.add_patch(Rectangle((y,z),yy-y,zz-z,fc=color,ec=color,alpha=alpha))
    seen.add(label)
for x,y in r['mount_holes_xy_mm']:ax.add_patch(Circle((x,y),.85,fc='white',ec='#15803d'))
ax.axhline(33,color='#7c3aed',lw=2,label='Axle / length midpoint Y=33')
ax.axvline(0,color='#64748b',ls=':',lw=.8)
for start,end in [(0,33),(33,66)]:
    ax.annotate('',xy=(-22,start),xytext=(-22,end),arrowprops={'arrowstyle':'<->'})
    ax.text(-24,(start+end)/2,'33 mm',rotation=90,ha='center',va='center',fontsize=10)
ax.set(xlim=(-27,23),ylim=(69,-4),xlabel='X [mm]',ylabel='Y [mm]; front = 0',title='Centered axle + batteries')
ax.set_aspect('equal');ax.grid(alpha=.15)
bx.add_patch(Rectangle((0,0),66,22,fill=False,ls='--',ec='#64748b'))
bx.axvline(33,color='#7c3aed',lw=2)
bx.set(xlim=(-2,68),ylim=(-1,25),xlabel='Y [mm]',ylabel='Z [mm]',title='Side projection (parts overlap in projection)')
bx.set_aspect('equal');bx.grid(alpha=.15)
fig.suptitle('A04 / central mass layout - center of gravity NOT yet measured',fontsize=15)
fig.text(.49,.24,'Axle: Y=40 -> 33 mm\nBattery centers: Y=46 -> 33 mm\nFan axis: Y=16.5 mm (proposed)\nDrive motors remain ~7.8 mm behind axle.\nActual masses / wiring / fan case still required.',fontsize=11)
ax.legend(loc='upper left',bbox_to_anchor=(1.14,-.12),fontsize=9,ncol=2,frameon=False)
fig.subplots_adjust(top=.9,bottom=.22,wspace=.35)
fig.savefig(ROOT/'layout-a04.png',dpi=150)
fig.savefig(ROOT/'layout-a04.svg')
