"""ToraNekoの4組の発光受光を立て基板へ。LTR-209外形は未確認の予約領域。"""
import json,math
from pathlib import Path
import cadquery as cq
from measure_step import read_parts
from build_assembly_a04 import exact_bounds,COLORS
from build_fan_mount_a05 import cylinder
from check_layout_a03 import overlap_boxes
from cadquery.occ_impl.exporters.assembly import exportGLTF
import plotly.graph_objects as go
ROOT=Path(__file__).resolve().parent
Z=1.7869267385966008; BASE=Z+.6; OPTIC_Z=7.0
CONFIG=[('front_left',-7,7,-45),('front_right',7,7,45),('side_left',-12.6,16.5,-90),('side_right',12.6,16.5,90)]

def transform(s,x,y,a):return s.rotate((0,0,0),(0,0,1),a).translate((x,y,0))
def box(w,d,h,x,y,z):return cq.Workplane('XY').box(w,d,h).val().translate((x,y,z))
def axial(r,length,x,y,z):return cq.Solid.makeCylinder(r,length,cq.Vector(x,y,z),cq.Vector(0,-1,0))

def check_pair(name,s,old,t):
    a,b=exact_bounds(s),exact_bounds(t)
    lower=math.sqrt(sum(max(0,getattr(a,d+'min')-getattr(b,d+'max'),getattr(b,d+'min')-getattr(a,d+'max'))**2 for d in 'xyz'))
    volume=s.intersect(t).Volume() if overlap_boxes(s,t) else 0.0
    return dict(a=name,b=old,intersection_mm3=volume,bbox_distance_lower_bound_mm=lower,penetration=volume>1e-5)

def main():
    items=[]
    for path,s in read_parts(ROOT/'assembly-a07.step'):
        name=path.rsplit(':',1)[-1]
        cat=name[4:] if name[:3].isdigit() else 'upper' if name=='upper_plate' else 'post' if name.startswith('front_post') else 'fastener'
        items.append((name,cat,s))
    assert len(items)==77
    board=next(s for _,c,s in items if c=='pcb');original_board=board
    extras=[];slots=[];support=[];rays=[]
    for name,x,y,a in CONFIG:
        daughter=box(5,.6,10.2,0,0,BASE+5.1)
        for u in (-1.3,1.3):
            daughter=daughter.fuse(box(1.2,.6,.6,u,0,Z+.3))
            local_slot=cq.Workplane('XY').center(u,0).slot2D(1.8,1.0).extrude(1).val().translate((0,0,Z-.2))
            slot=transform(local_slot,x,y,a)
            support.append(dict(channel=name,tab_u_mm=u,slot_intersection_volume_mm3=original_board.intersect(slot).Volume(),expected_mm3=(.8+math.pi*.5**2)*.6))
            assert abs(support[-1]['slot_intersection_volume_mm3']-(.8+math.pi*.5**2)*.6)<1e-5,'slot must be entirely within main PCB'
            board=board.cut(slot);slots.append(slot)
        for zz0 in (5.4,10.1):
            for zz in (zz0-1.27,zz0+1.27):daughter=daughter.cut(axial(.4,2,0,1,zz))
        extras.append((name+'_pcb','sensor_pcb',transform(daughter.clean(),x,y,a)))
        for optic_z,cat in [(5.4,'ir_emitter'),(10.1,'ir_receiver')]:
            u=0
            if cat=='ir_emitter':
                # Φ3、全長5.35、つばΦ3.9×0.75の名目簡略形状。平面カットは省略。
                body=axial(1.5,3.85,u,-.8,optic_z).fuse(cq.Solid.makeSphere(1.5,cq.Vector(u,-4.65,optic_z),cq.Vector(0,-1,0)))
                body=body.fuse(axial(1.95,.75,u,-.8,optic_z))
            else:
                # 受光部の確認済み製品外形ではない。Φ4.2×6の予約円柱で判定。
                body=axial(2.1,6,u,-.8,optic_z)
            leads=[axial(.25,1.8,u,1,zz) for zz in (optic_z-1.27,optic_z+1.27)]
            extras.append((name+'_'+cat,cat,transform(body,x,y,a)))
            extras.append((name+'_'+cat+'_leads','sensor_leads',transform(cq.Compound.makeCompound(leads),x,y,a)))
            # 同じ予約形状で光軸先端から前方20 mmに遮蔽物がないか確認（光学性能ではない）。
            ray=transform(axial(.15,20,u,-6.9,optic_z),x,y,a)
            rays.append((name+'_'+cat,ray))
    items=[(n,c,board.clean() if c=='pcb' else s) for n,c,s in items]
    checks=[]
    for i,(name,cat,s) in enumerate(extras):
        assert s.isValid(),name
        print('Checking',name,flush=True)
        for old,oc,t in items+extras[:i]:
            r=check_pair(name,s,old,t);checks.append(r)
            assert not r['penetration'],r
    swept=cylinder(11,4.3812501,0,21.75,2.8181766386)
    swept_checks=[check_pair(n,s,'fan_swept_D22',swept) for n,c,s in extras]
    assert not any(r['penetration'] for r in swept_checks)
    sight=[]
    for name,ray in rays:
        hits=[]
        for n,c,s in items+extras:
            if n.startswith(name):continue
            if overlap_boxes(ray,s) and ray.intersect(s).Volume()>1e-5:hits.append(n)
        sight.append(dict(axis=name,length_mm=20,blocked_by=hits))
        assert not hits,sight[-1]
    colors={**COLORS,'upper':('#dbad3e','上部固定基板'),'post':('#d3d8df','支柱'),'fastener':('#384250','ネジ'),
            'sensor_pcb':('#ce9e24','センサ立て基板（新規）'),'ir_emitter':('#c1e5f0','OSI5FU3A11C 簡略形状'),
            'ir_receiver':('#393c48','LTR-209 予約領域・寸法未確認'),'sensor_leads':('#b2b8c1','センサリード')}
    assy=cq.Assembly(name='NEW_HALF_A08');meshes={}
    for name,cat,s in items+extras:
        h=colors[cat][0];assy.add(s,name=name,color=cq.Color(*(int(h[i:i+2],16)/255 for i in (1,3,5))))
        v,f=s.tessellate(.08,.18);m=meshes.setdefault(cat,dict(v=[],f=[]));base=len(m['v']);m['v'].extend([p.toTuple() for p in v]);m['f'].extend([[i+base for i in face] for face in f])
    b=exact_bounds(assy.toCompound());assert b.xmin>=-19.5-1e-5 and b.xmax<=19.5+1e-5 and b.ymin>=0 and b.ymax<=66 and b.zmin>=-1e-5 and b.zmax<=22
    assy.export(str(ROOT/'assembly-a08.step'));assert exportGLTF(assy,str(ROOT/'assembly-a08.glb'),binary=True,tolerance=.08,angularTolerance=.18)
    cq.exporters.export(board,str(ROOT/'pcb-a08-concept.step'))
    cq.exporters.export(next(s for n,c,s in extras if c=='sensor_pcb'),str(ROOT/'sensor-board-a08.step'))
    restored=cq.importers.importStep(str(ROOT/'assembly-a08.step')).val();assert restored.isValid() and len(restored.Solids())==len(assy.toCompound().Solids())
    fig=go.Figure()
    for cat,m in meshes.items():
        v,f=m['v'],m['f'];fig.add_trace(go.Mesh3d(x=[p[0] for p in v],y=[p[1] for p in v],z=[p[2] for p in v],i=[p[0] for p in f],j=[p[1] for p in f],k=[p[2] for p in f],color=colors[cat][0],name=colors[cat][1],showlegend=True))
    fig.update_layout(title='A08 — ToraNekoと同じ発光・受光部品を立て基板へ',scene=dict(aspectmode='data',xaxis_title='X [mm]',yaxis_title='Y [mm]',zaxis_title='Z [mm]',camera=dict(eye=dict(x=1.5,y=-1.8,z=1.3))),margin=dict(l=0,r=0,t=60,b=0))
    (ROOT/'assembly-a08.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>A08 センサ立て基板</title><body><p>回転：ドラッグ。凡例で表示切替。ToraNekoの部品型番・4組構成を維持。前斜め±45°／左右側方。発光・受光を上下配置。黒い受光部はLTR-209の寸法未確認の予約形状（Φ4.2×6）。発光部はOSI5FU3A11Cの簡略形状。基板は差込タブ＋はんだ固定の候補で、回路・パッド・はんだ・接着剤は未モデル化。Φ22ファンは変更なし。製造用確定データではありません。<br>参照CAD: Copyright (c) 2026 Tokoro0917 / MIT License（third_party/ToraNeko.Mk3.LICENSE）。</p>'+fig.to_html(full_html=False,include_plotlyjs=True,default_height='85vh')+'</body></html>')
    report=dict(parts=len(items+extras),solids=len(restored.Solids()),step_roundtrip_valid=True,dimensions_xyz_mm=[b.xlen,b.ylen,b.zlen],bounds_min_mm=[b.xmin,b.ymin,b.zmin],bounds_max_mm=[b.xmax,b.ymax,b.zmax],sensor_channels=[dict(name=n,x_mm=x,y_mm=y,rotation_deg=a) for n,x,y,a in CONFIG],optical_axis_heights_mm=dict(emitter=5.4,receiver=10.1),receiver_geometry='UNVERIFIED placeholder diameter 4.2 length 6 mm; lead pitch assumed 2.54',emitter_geometry='datasheet nominal simplified D3, flange D3.9 x .75, length 5.35; tolerances not fully included',slot_support=support,checks=checks,blade_swept_checks=swept_checks,optical_axis_checks=sight,fan_changed=False)
    (ROOT/'sensor-a08-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(14,8))
    for idx,hide in enumerate([False,True],1):
        ax=fig.add_subplot(1,2,idx,projection='3d');faces=[];cs=[]
        for cat,m in meshes.items():
            if hide and cat=='battery':continue
            faces.extend([[m['v'][i] for i in f] for f in m['f']]);cs.extend([colors[cat][0]]*len(m['f']))
        ax.add_collection3d(Poly3DCollection(faces,facecolors=cs,edgecolors=cs,linewidths=0,shade=True))
        ax.set(xlim=(-21,21),ylim=(0,63),zlim=(0,22),xlabel='X [mm]',ylabel='Y [mm]',zlabel='Z [mm]');ax.set_box_aspect((42,63,22));ax.view_init(32,-65);ax.set_title('Complete layout' if not hide else 'Battery hidden')
    fig.suptitle('A08 - 4 upright sensor boards / same emitter and receiver part numbers',fontsize=16)
    fig.text(.06,.04,'LTR-209 shape is an UNVERIFIED envelope. No pads, solder, wiring or sensor calibration yet. D22 fan unchanged.',fontsize=11)
    fig.savefig(ROOT/'sensor-a08.png',dpi=140);plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks','blade_swept_checks','optical_axis_checks','slot_support']},indent=2))
if __name__=='__main__':main()
