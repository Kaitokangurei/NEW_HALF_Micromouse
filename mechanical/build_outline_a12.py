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
CONFIG=[('side_left',-7,7.5,-60),('side_right',7,7.5,60),('front_left',-14.0,16.5,-10),('front_right',14.0,16.5,10)]

def transform(s,x,y,a):return s.rotate((0,0,0),(0,0,1),a).translate((x,y,0))
def box(w,d,h,x,y,z):return cq.Workplane('XY').box(w,d,h).val().translate((x,y,z))
def axial(r,length,x,y,z):return cq.Solid.makeCylinder(r,length,cq.Vector(x,y,z),cq.Vector(0,-1,0))

BOUNDS_CACHE={}
def bounds(s):
    key=id(s)
    if key not in BOUNDS_CACHE:BOUNDS_CACHE[key]=(s,exact_bounds(s))
    return BOUNDS_CACHE[key][1]

def check_pair(name,s,old,t):
    a,b=bounds(s),bounds(t)
    lower=math.sqrt(sum(max(0,getattr(a,d+'min')-getattr(b,d+'max'),getattr(b,d+'min')-getattr(a,d+'max'))**2 for d in 'xyz'))
    overlap=all(min(getattr(a,d+'max'),getattr(b,d+'max'))-max(getattr(a,d+'min'),getattr(b,d+'min'))>1e-6 for d in 'xyz')
    volume=s.intersect(t).Volume() if overlap else 0.0
    return dict(a=name,b=old,intersection_mm3=volume,bbox_distance_lower_bound_mm=lower,penetration=volume>1e-5)

def main():
    items=[]
    for path,s in read_parts(ROOT/'assembly-a07.step'):
        name=path.rsplit(':',1)[-1]
        cat=name[4:] if name[:3].isdigit() else 'upper' if name=='upper_plate' else 'post' if name.startswith('front_post') else 'fastener'
        items.append((name,cat,s))
    assert len(items)==77
    from three_point_a11 import convert,POINTS
    items=convert(items)
    board=next(s for _,c,s in items if c=='pcb')
    old_outline=[(-13,5),(13,5),(17,9),(17,25),(13.4,25),(13.4,41),(17,41),(17,57),(13,61),(-13,61),(-17,57),(-17,41),(-13.4,41),(-13.4,25),(-17,25),(-17,9)]
    new_outline=[(-15.5,1),(15.5,1),(18.5,4),(18.5,25),(13.4,25),(13.4,41),(17,41),(17,57),(13,61),(-13,61),(-17,57),(-17,41),(-13.4,41),(-13.4,25),(-18.5,25),(-18.5,4)]
    def outline_solid(points):return cq.Workplane('XY').polyline(points).close().extrude(.6).val().translate((0,0,Z))
    added=outline_solid(new_outline).cut(outline_solid(old_outline))
    board=board.fuse(added).clean();assert board.isValid() and len(board.Solids())==1
    original_board=board
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
    # 3点化で変更した上板・中央支柱・ネジ・メイン基板を全形状へ照合。
    changed={'upper_plate','center_post','center_top','center_bottom','063_pcb'}
    all_parts=items+extras
    mount_checks=[]
    for i,(name,cat,s) in enumerate(all_parts):
        if name not in changed:continue
        for j,(old,oc,t) in enumerate(all_parts):
            if i==j or (old in changed and j<i):continue
            r=check_pair(name,s,old,t)
            intended={name,old} in [{'center_top','center_post'},{'center_bottom','center_post'}]
            r['intended_thread_engagement']=intended
            mount_checks.append(r)
            assert not r['penetration'] or intended,r
    upper=next(s for n,c,s in items if c=='upper')
    contact=[]
    for n,c,s in items:
        if n=='center_post' or c in ['mount','fan_mount']:
            distance=upper.distance(s);contact.append(dict(part=n,distance_mm=distance))
            assert distance<1e-5,(n,distance)
    swept=cylinder(11,4.3812501,0,21.75,2.8181766386)
    swept_checks=[check_pair(n,s,'fan_swept_D22',swept) for n,c,s in extras+[(n,c,t) for n,c,t in items if n in changed]]
    assert not any(r['penetration'] for r in swept_checks)
    sight=[]
    for name,ray in rays:
        hits=[]
        for n,c,s in items+extras:
            if n.startswith(name):continue
            if overlap_boxes(ray,s) and ray.intersect(s).Volume()>1e-5:hits.append(n)
        sight.append(dict(axis=name,length_mm=20,blocked_by=hits))
        assert not hits,sight[-1]
    # 各センサ部品のXY外接矩形ごとに外形との距離を測る。実輪郭より保守的な検査。
    def inside_polygon(p):
        x,y=p;inside=False
        for q,r in zip(new_outline,new_outline[1:]+new_outline[:1]):
            if (q[1]>y)!=(r[1]>y) and x<(r[0]-q[0])*(y-q[1])/(r[1]-q[1])+q[0]:inside=not inside
        return inside
    def point_segment(p,a,b):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
        return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def segment_distance(a,b,c,d):
        if cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0:return 0.
        return min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))
    clearances=[]
    for name,cat,shape in extras:
        bb=bounds(shape);rect=[(bb.xmin,bb.ymin),(bb.xmax,bb.ymin),(bb.xmax,bb.ymax),(bb.xmin,bb.ymax)]
        gap=min(segment_distance(a,b,c,d) for a,b in zip(rect,rect[1:]+rect[:1]) for c,d in zip(new_outline,new_outline[1:]+new_outline[:1]))
        inside=all(inside_polygon(p) for p in rect) and gap>1e-6
        clearances.append(dict(part=name,xy_bbox_mm=[bb.xmin,bb.ymin,bb.xmax,bb.ymax],inside=inside,clearance_lower_bound_mm=gap))
        assert inside and gap>=1.0-1e-6,clearances[-1]
    colors={**COLORS,'upper':('#dbad3e','上部固定基板'),'post':('#d3d8df','支柱'),'fastener':('#384250','ネジ'),
            'sensor_pcb':('#ce9e24','センサ立て基板（新規）'),'ir_emitter':('#c1e5f0','OSI5FU3A11C 簡略形状'),
            'ir_receiver':('#393c48','LTR-209 予約領域・寸法未確認'),'sensor_leads':('#b2b8c1','センサリード')}
    assy=cq.Assembly(name='NEW_HALF_A12');meshes={}
    for name,cat,s in items+extras:
        h=colors[cat][0];assy.add(s,name=name,color=cq.Color(*(int(h[i:i+2],16)/255 for i in (1,3,5))))
        v,f=s.tessellate(.08,.18);m=meshes.setdefault(cat,dict(v=[],f=[]));base=len(m['v']);m['v'].extend([p.toTuple() for p in v]);m['f'].extend([[i+base for i in face] for face in f])
    b=exact_bounds(assy.toCompound());assert b.xmin>=-19.5-1e-5 and b.xmax<=19.5+1e-5 and b.ymin>=0 and b.ymax<=66 and b.zmin>=-1e-5 and b.zmax<=22
    assy.export(str(ROOT/'assembly-a12.step'));assert exportGLTF(assy,str(ROOT/'assembly-a12.glb'),binary=True,tolerance=.08,angularTolerance=.18)
    cq.exporters.export(board,str(ROOT/'pcb-a12-concept.step'))
    cq.exporters.export(upper,str(ROOT/'upper-plate-a12.step'))
    cq.exporters.export(next(s for n,c,s in extras if c=='sensor_pcb'),str(ROOT/'sensor-board-a12.step'))
    restored=cq.importers.importStep(str(ROOT/'assembly-a12.step')).val();assert restored.isValid() and len(restored.Solids())==len(assy.toCompound().Solids())
    fig=go.Figure()
    for cat,m in meshes.items():
        v,f=m['v'],m['f'];fig.add_trace(go.Mesh3d(x=[p[0] for p in v],y=[p[1] for p in v],z=[p[2] for p in v],i=[p[0] for p in f],j=[p[1] for p in f],k=[p[2] for p in f],color=colors[cat][0],name=colors[cat][1],showlegend=True))
    fig.update_layout(title='A12 — センサ全体を基板外形の内側へ（名目隙間1 mm以上）',scene=dict(aspectmode='data',xaxis_title='X [mm]',yaxis_title='Y [mm]',zaxis_title='Z [mm]',camera=dict(eye=dict(x=1.5,y=-1.8,z=1.3))),margin=dict(l=0,r=0,t=60,b=0))
    (ROOT/'assembly-a12.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>A12 センサ立て基板</title><body><p>回転：ドラッグ。凡例で表示切替。センサ本体・リード・立て基板を、外形から名目1 mm以上内側に配置。前側基板外形を拡張し、センサの位置・角度は維持。上部固定基板は前側中央1点＋駆動マウント2点の3点支持。ファンモータマウント自体の2本の固定ネジは維持。ToraNekoのセンサ4組構成を維持。真正面0°。タイヤ寄りの後側：前壁用±10°。機体前方：横壁用±60°。発光・受光を上下配置。黒い受光部はLTR-209の寸法未確認の予約形状（Φ4.2×6）。発光部はOSI5FU3A11Cの簡略形状。基板は差込タブ＋はんだ固定の候補で、回路・パッド・はんだ・接着剤は未モデル化。Φ22ファンは変更なし。製造用確定データではありません。<br>参照CAD: Copyright (c) 2026 Tokoro0917 / MIT License（third_party/ToraNeko.Mk3.LICENSE）。</p>'+fig.to_html(full_html=False,include_plotlyjs=True,default_height='85vh')+'</body></html>')
    report=dict(outline_xy_mm=new_outline,sensor_outline_clearances=clearances,required_outline_gap_mm=1.0,added_pcb_volume_mm3=added.Volume(),support_points_xy_mm=POINTS,mount_checks=mount_checks,support_contact_checks=contact,angle_convention='0 degrees forward (-Y); positive rotates toward +X; side-wall channels at front 60 degrees, front-wall channels near tires 10 degrees',parts=len(items+extras),solids=len(restored.Solids()),step_roundtrip_valid=True,dimensions_xyz_mm=[b.xlen,b.ylen,b.zlen],bounds_min_mm=[b.xmin,b.ymin,b.zmin],bounds_max_mm=[b.xmax,b.ymax,b.zmax],sensor_channels=[dict(name=n,x_mm=x,y_mm=y,rotation_deg=a) for n,x,y,a in CONFIG],optical_axis_heights_mm=dict(emitter=5.4,receiver=10.1),receiver_geometry='UNVERIFIED placeholder diameter 4.2 length 6 mm; lead pitch assumed 2.54',emitter_geometry='datasheet nominal simplified D3, flange D3.9 x .75, length 5.35; tolerances not fully included',slot_support=support,checks=checks,blade_swept_checks=swept_checks,optical_axis_checks=sight,fan_changed=False)
    (ROOT/'sensor-a12-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
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
    fig.suptitle('A12 - Sensors inside PCB outline / nominal edge clearance >= 1 mm',fontsize=16)
    fig.text(.06,.04,'LTR-209 shape is an UNVERIFIED envelope. No pads, solder, wiring or sensor calibration yet. D22 fan unchanged.',fontsize=11)
    fig.savefig(ROOT/'sensor-a12.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,10))
    from matplotlib.patches import Polygon as PolyPatch,Rectangle
    ax.add_patch(PolyPatch(new_outline,facecolor='#d9eee3',edgecolor='#23885c',lw=2))
    for row in clearances:
        x0,y0,x1,y1=row['xy_bbox_mm']
        ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#eeae45',edgecolor='#a36d1f',alpha=.35))
    for name,x,y,a in CONFIG:
        t=math.radians(a);ax.arrow(x,y,8*math.sin(t),-8*math.cos(t),width=.12,head_width=.7,color='#324f82')
    ax.set(xlim=(-21,21),ylim=(64,-3),xlabel='X [mm]',ylabel='Y [mm] / front = 0',title='A12 top view - sensor XY bounding rectangles')
    ax.set_aspect('equal');ax.grid(alpha=.2)
    fig.text(.1,.025,f'Minimum conservative outline gap: {min(r["clearance_lower_bound_mm"] for r in clearances):.3f} mm\nIncludes leads and daughterboards. Receiver envelope unverified.',fontsize=10)
    fig.savefig(ROOT/'sensor-a12-top.png',dpi=150);plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks','blade_swept_checks','optical_axis_checks','slot_support','mount_checks','sensor_outline_clearances']},indent=2))
if __name__=='__main__':main()
