"""生成済みA03基板の上面・3Dプレビュー。matplotlib / cadqueryを使用。"""
import json
from pathlib import Path
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path(__file__).resolve().parent
r=json.loads((ROOT/'layout-a03-checks.json').read_text())
fig=plt.figure(figsize=(12,8))
ax=fig.add_subplot(121)
ax.add_patch(Polygon(r['outline_xy_mm'],facecolor='#dcfce7',edgecolor='#15803d',lw=2))
for x,y in r['mount_holes_xy_mm']:
    ax.add_patch(Circle((x,y),r['mount_hole_diameter_mm']/2,facecolor='white',edgecolor='#0f172a'))
    ax.plot([x-1.5,x+1.5],[y,y],color='#64748b',lw=.6)
    ax.plot([x,x],[y-1.5,y+1.5],color='#64748b',lw=.6)
ax.axvline(0,color='#64748b',ls=':',lw=.7)
ax.plot([-19.5,19.5,19.5,-19.5,-19.5],[0,0,66,66,0],color='#94a3b8',ls='--')
ax.annotate('',xy=(-17,3),xytext=(17,3),arrowprops={'arrowstyle':'<->'})
ax.text(0,2,'34 mm',ha='center')
ax.annotate('',xy=(-21,5),xytext=(-21,61),arrowprops={'arrowstyle':'<->'})
ax.text(-22,33,'56 mm',rotation=90,va='center')
ax.annotate('4 x D1.7 (provisional)',xy=(11.6,53.75),xytext=(-16,64),arrowprops={'arrowstyle':'->'},fontsize=10)
ax.text(0,29,'Neck width 26.8',ha='center',fontsize=10)
ax.set(xlim=(-25,24),ylim=(69,-3),xlabel='X [mm]',ylabel='Y [mm], front = 0',title='A03 board outline / 0.6 mm thick')
ax.set_aspect('equal');ax.grid(alpha=.15)
bx=fig.add_subplot(122,projection='3d')
shape=cq.importers.importStep(str(ROOT/'pcb-a03-concept.step')).val()
vertices,faces=shape.tessellate(.05)
polys=[[[vertices[i].x,vertices[i].y,vertices[i].z] for i in f] for f in faces]
bx.add_collection3d(Poly3DCollection(polys,facecolors='#4caa74',edgecolors='none'))
bx.set(xlim=(-20,20),ylim=(0,66),zlim=(0,8),xlabel='X [mm]',ylabel='Y [mm]',zlabel='Z [mm]')
bx.set_box_aspect((40,66,8));bx.view_init(35,-65)
bx.set_zticks([0,4,8])
bx.set_title('Original board concept STEP\nNo circuits, fan opening or sensor mounts yet')
fig.suptitle('A03 / mechanical concept - NOT FOR MANUFACTURE',fontsize=16)
fig.text(.55,.12,'Hole centers: X = +/-11.6 mm\nY = 36.25, 53.75 mm\nNotch: |X| > 13.4, Y = 32..48 mm\nSource: ToraNeko v36 drive mounting axes',fontsize=11)
fig.tight_layout(rect=(0,.08,1,.94))
bx.set_position([.56,.32,.39,.53])
fig.savefig(ROOT/'pcb-a03-preview.png',dpi=150)
fig.savefig(ROOT/'pcb-a03-preview.svg')
