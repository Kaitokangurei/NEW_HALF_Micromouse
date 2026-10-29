"""A04配置を保持したファン固定候補。ネジは占有形状、ねじ山・締結強度は未検証。"""
import json
from pathlib import Path
import cadquery as cq
from cadquery.occ_impl.exporters.assembly import exportGLTF
import plotly.graph_objects as go
from measure_step import read_parts
from build_assembly_a04 import exact_bounds, COLORS
ROOT=Path(__file__).resolve().parent
Y=16.5
PCB_BOTTOM=1.7869267385966008
PCB_TOP=PCB_BOTTOM+.6
MOUNT_TOP=10.886926738596567
BRIDGE_TOP=MOUNT_TOP+1.5

def cylinder(r,h,x,y,z):
    return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))

def main():
    original=list(read_parts(ROOT/'assembly-a04.step'))
    assert len(original)==66
    manifest=json.loads((ROOT/'assembly-a04-manifest.json').read_text())
    items=[]
    for (path,s),p in zip(original,manifest['parts']):
        assert path.endswith(':'+p['id']), (path,p['id'])
        items.append((p['id'],p['category'],s))
    # 一体の門型支持具。上面から既存マウントに接触。中央はモータ逃げ。
    bridge=cq.Workplane('XY').box(30.6,9,1.5).val().translate((0,Y,MOUNT_TOP+.75))
    bridge=bridge.cut(cylinder(3.2,3,0,Y,MOUNT_TOP-.5))
    for x in (-13.5,13.5):
        bridge=bridge.fuse(cylinder(1.8,MOUNT_TOP-PCB_TOP+.3,x,Y,PCB_TOP))
        bridge=bridge.cut(cylinder(.65,4,x,Y,PCB_TOP))  # M1.6用下穴候補、材質・加工依存
    for x in (-4.5,4.5):
        bridge=bridge.cut(cylinder(.8,3,x,Y,MOUNT_TOP-.5))
    bridge=bridge.clean()
    assert bridge.isValid() and len(bridge.Solids())==1
    for i,(name,cat,s) in enumerate(items):
        if cat=='pcb':
            for x in (-13.5,13.5): s=s.cut(cylinder(.85,2,x,Y,PCB_BOTTOM-.5))
            items[i]=(name,cat,s.clean());board=s
    additions=[('fan_bridge','bridge',bridge)]
    # ネジ頭は候補寸法の円筒包絡。工具溝・ねじ山は描かない。
    for side,x in enumerate((-13.5,13.5)):
        screw=cylinder(.8,3,x,Y,PCB_BOTTOM).fuse(cylinder(1.5,1.2,x,Y,PCB_BOTTOM-1.2))
        additions.append((f'pcb_screw_{side}','fastener',screw))
    for side,x in enumerate((-4.5,4.5)):
        screw=cylinder(.7,3,x,Y,BRIDGE_TOP-3).fuse(cylinder(1.3,1,x,Y,BRIDGE_TOP))
        additions.append((f'mount_screw_{side}','fastener',screw))
    # 新部品と全既存部品のチェック。締結部の意図した食い込みのみ別記。
    checks=[]
    for name,cat,s in additions:
        for old,oldcat,t in items:
            volume=s.intersect(t).Volume()
            intended=name.startswith('mount_screw') and oldcat=='fan_mount'
            checks.append(dict(a=name,b=old,volume_mm3=volume,intended_thread_engagement=intended))
            if volume>1e-5 and not intended: raise ValueError(checks[-1])
    for i,(name,cat,s) in enumerate(additions):
        for old,oldcat,t in additions[:i]:
            volume=s.intersect(t).Volume()
            intended=cat=='fastener' and name.startswith('pcb_screw') and oldcat=='bridge'
            checks.append(dict(a=name,b=old,volume_mm3=volume,intended_thread_engagement=intended))
            if volume>1e-5 and not intended:raise ValueError(checks[-1])
    swept=cylinder(11,7.199426738596786-2.8181766385967233,0,Y,2.8181766385967233)
    swept_results=[]
    for name,_,s in additions:
        v=s.intersect(swept).Volume();d=s.distance(swept)
        assert v<1e-5 and d>.49
        swept_results.append(dict(part=name,volume_mm3=v,distance_mm=d))
    colors={**COLORS,'bridge':('#ed8540','ファン支持具（新規）'),'fastener':('#334155','ネジ占有形状（仕様未確定）')}
    assy=cq.Assembly(name='NEW_HALF_A05_FAN_MOUNT');fig=go.Figure()
    for name,category,s in items+additions:
        assert s.isValid()
        h=colors[category][0];assy.add(s,name=name,color=cq.Color(*(int(h[n:n+2],16)/255 for n in (1,3,5))))
    # 表示メッシュをカテゴリごとにまとめる。
    for category in dict.fromkeys(cat for _,cat,_ in items+additions):
        vv=[];ff=[]
        for _,cat,s in items+additions:
            if cat!=category:continue
            v,f=s.tessellate(.08,.18);base=len(vv)
            vv.extend([p.toTuple() for p in v]);ff.extend([[i+base for i in face] for face in f])
        fig.add_trace(go.Mesh3d(x=[p[0] for p in vv],y=[p[1] for p in vv],z=[p[2] for p in vv],
                     i=[f[0] for f in ff],j=[f[1] for f in ff],k=[f[2] for f in ff],color=colors[category][0],
                     name=colors[category][1],showlegend=True,visible='legendonly' if category=='battery' else True))
    fig.update_layout(title='A05 ファン固定候補 — オレンジ：門型支持具',scene=dict(aspectmode='data',
        xaxis_title='X [mm]',yaxis_title='Y [mm]',zaxis_title='Z [mm]',camera=dict(eye=dict(x=1.5,y=-1.8,z=1.3))),
        margin=dict(l=0,r=0,t=60,b=0))
    (ROOT/'assembly-a05.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>A05 ファン固定案</title><body><p>ドラッグで回転、凡例で表示切替。電池は初期非表示。オレンジの支持具は新規設計。ネジは占有形状、既存穴のねじ規格・強度は未確認。Φ22羽根専用案、Φ30には非対応。吸引ケース／流路・配線は未設計。重心は未更新。製造用確定データではありません。<br>参照CAD: ToraNeko.Mk3, Copyright (c) 2026 Tokoro0917, MIT License（third_party/ToraNeko.Mk3.LICENSE同梱）。</p>'+fig.to_html(full_html=False,include_plotlyjs=True,default_height='85vh')+'</body></html>')
    assy.export(str(ROOT/'assembly-a05.step'))
    assert exportGLTF(assy,str(ROOT/'assembly-a05.glb'),binary=True,tolerance=.08,angularTolerance=.18)
    cq.exporters.export(bridge,str(ROOT/'fan-bridge-a05.step'));cq.exporters.export(bridge,str(ROOT/'fan-bridge-a05.stl'))
    cq.exporters.export(board,str(ROOT/'pcb-a05-concept.step'))
    restored=cq.importers.importStep(str(ROOT/'assembly-a05.step')).val();compound=assy.toCompound()
    assert restored.isValid() and len(restored.Solids())==len(compound.Solids())
    b=exact_bounds(restored)
    assert b.xmin>=-19.5-1e-5 and b.xmax<=19.5+1e-5 and b.ymin>=0 and b.ymax<=66 and b.zmin>=-1e-5 and b.zmax<=22
    # 支持具・ネジだけの材料密度仮定。実測質量や25gモデルへの無条件な加算ではない。
    mass=[]
    for name,cat,s in additions:
        density=1.15 if cat=='bridge' else 7.85
        mass.append(dict(part=name,volume_mm3=s.Volume(),assumed_density_g_cm3=density,
                         mass_g=s.Volume()*density/1000,center_mm=list(s.Center().toTuple())))
    report=dict(revision='A05 candidate',parts=len(items+additions),solids=len(compound.Solids()),
        step_roundtrip_valid=True,dimensions_xyz_mm=[b.xlen,b.ylen,b.zlen],
        bridge_mass_assumption='nylon 1.15 g/cm3; screw envelopes steel 7.85; actual material/mass unconfirmed',
        added_mass_estimates=mass,checks=checks,blade_swept_envelope_checks=swept_results,
        pcb_holes=dict(x_mm=[-13.5,13.5],y_mm=Y,diameter_mm=1.7),
        unresolved=['M1.4 thread compatibility in existing diameter 1.221 holes','fastener catalog dimensions and thread strength',
                    'PCB copper keepouts and stiffness','duct and inlet','manufacturing tolerances','actual mass and complete CG'])
    (ROOT/'fan-mount-a05-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    # 固定部だけの見やすいPNG。基板は薄い半透明。
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(11,8));ax=fig.add_subplot(projection='3d');faces=[];cs=[]
    for _,cat,s in items+additions:
        if cat not in ['fan_motor','fan_mount','fan','bridge','fastener']:continue
        v,f=s.tessellate(.07,.2);v=[p.toTuple() for p in v]
        faces.extend([[v[i] for i in a] for a in f]);cs.extend([colors[cat][0]]*len(f))
    ax.add_collection3d(Poly3DCollection(faces,facecolors=cs,edgecolors=cs,linewidths=0,shade=True))
    v,f=board.tessellate(.1,.2);v=[p.toTuple() for p in v]
    ax.add_collection3d(Poly3DCollection([[v[i] for i in a] for a in f],facecolors='#23885c',alpha=.12,linewidths=0))
    ax.set(xlim=(-17,17),ylim=(3,31),zlim=(0,22),xlabel='X [mm]',ylabel='Y [mm]',zlabel='Z [mm]')
    ax.set_box_aspect((34,28,22));ax.view_init(28,-63)
    fig.suptitle('A05 - Fan bridge mounting concept',fontsize=18)
    fig.text(.08,.03,'Orange: one-piece bridge | 2 lower screws + 2 upper screws\nD22 blade only. Screw threads/materials and ducts remain to be verified.',fontsize=11)
    fig.savefig(ROOT/'fan-mount-a05.png',dpi=150);plt.close(fig)
    print(json.dumps({k:report[k] for k in ['parts','solids','dimensions_xyz_mm','added_mass_estimates','blade_swept_envelope_checks']},indent=2))
if __name__=='__main__':main()
