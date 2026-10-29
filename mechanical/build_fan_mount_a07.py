"""ToraNekoの上部固定基板・支柱を転用したA07。ファン軸をY=21.75へ移し、電池を左右へ広げる。"""
import hashlib,json
from pathlib import Path
import cadquery as cq
from measure_step import read_parts
from build_assembly_a04 import exact_bounds,COLORS
from build_fan_mount_a05 import cylinder
from cadquery.occ_impl.exporters.assembly import exportGLTF
import plotly.graph_objects as go
ROOT=Path(__file__).resolve().parent
SOURCE=Path('/workspace/library-files/TORANEKO.Mk3_v36.step')
Z=1.7869267385966008; TOP=Z+9.1

def main():
    from check_layout_a03 import EXPECTED_SHA
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA
    raw=dict(read_parts(SOURCE));items=[]
    meta=json.loads((ROOT/'assembly-a04-manifest.json').read_text())
    for (name,s),p in zip(read_parts(ROOT/'assembly-a04.step'),meta['parts']):
        assert name.endswith(':'+p['id'])
        if p['category'] in ['fan','fan_motor','fan_mount']:s=s.translate((0,5.25,0))
        if p['category']=='battery':s=s.translate((-3.2 if s.Center().x<0 else 3.2,0,0))
        items.append((p['id'],p['category'],s))
    offset=(13.4,38.32212318166235,Z)
    upper=next(s for n,s in raw.items() if '上部固定基板' in n).translate(offset)
    # 元設計と同じ前後ピッチへ戻る。左右駆動部を内側へ0.3移した分だけ穴位置を補正。
    for x in (-11.9,11.9):upper=upper.fuse(cylinder(.7,.6,x,29.25,TOP))
    for x in (-11.6,11.6):upper=upper.cut(cylinder(.7,1,x,29.25,TOP-.2))
    # エンコーダ上端の逃げを0.3 mmずつ確保。
    for x in (-8.357,8.357):
        upper=upper.cut(cq.Workplane('XY').box(1.2,8,2).val().translate((x,33.7,TOP+.3)))
    upper=upper.clean()
    posts=[s.translate(offset) for n,s in raw.items() if '支柱 v3' in n]
    assert len(posts)==2
    extras=[('upper_plate','upper',upper)]+[(f'front_post_{i}','post',s) for i,s in enumerate(posts)]
    for i,(name,cat,s) in enumerate(items):
        if cat=='pcb':
            for x in (-8.9,8.9):s=s.cut(cylinder(.8,2,x,12.25,Z-.3))
            s=s.cut(cylinder(4,2,0,21.75,Z-.3))
            items[i]=(name,cat,s.clean());board=s
    # M1.4 x 3相当の占有形状。頭高0.6/径2.5は調達前の仮定。
    for kind,coords,start in [('fan',[(-4.5,21.75),(4.5,21.75)],TOP+.6),
                              ('front_top',[(-8.9,12.25),(8.9,12.25)],TOP+.6),
                              ('drive_top',[(-11.6,29.25),(11.6,29.25)],TOP+.6)]:
        for i,(x,y) in enumerate(coords):
            s=cylinder(.7,3,x,y,start-3).fuse(cylinder(1.25,.6,x,y,start))
            extras.append((f'{kind}_{i}','fastener',s))
    for i,x in enumerate((-8.9,8.9)):
        s=cylinder(.7,3,x,12.25,Z).fuse(cylinder(1.25,.6,x,12.25,Z-.6))
        extras.append((f'front_bottom_{i}','fastener',s))
    checks=[]
    for i,(name,cat,s) in enumerate(extras):
        assert s.isValid() and len(s.Solids())==1,(name,len(s.Solids()))
        for old,oldcat,t in items+extras[:i]:
            v=s.intersect(t).Volume()
            intended=cat=='fastener' and ((name.startswith('fan_') and oldcat=='fan_mount') or
                      (name.startswith('front_') and oldcat=='post') or (name.startswith('drive_') and oldcat=='mount'))
            r=dict(a=name,b=old,volume_mm3=v,intended_thread_engagement=intended);checks.append(r)
            if v>1e-5 and not intended:
                q=exact_bounds(s.intersect(t));print('INTERSECTION',q.xmin,q.xmax,q.ymin,q.ymax,q.zmin,q.zmax,flush=True)
                raise ValueError(r)
    # 移動した吸引部・電池は固定部品だけでなく、既存部品との組合せも再確認。
    moving={'fan','fan_motor','fan_mount','battery'}
    for i,(name,cat,s) in enumerate(items):
        if cat not in moving:continue
        for j,(old,oldcat,t) in enumerate(items):
            if i==j or (oldcat in moving and j<i):continue
            if cat.startswith('fan') and oldcat.startswith('fan'):continue
            v=s.intersect(t).Volume();checks.append(dict(a=name,b=old,volume_mm3=v,intended_thread_engagement=False))
            if v>1e-5:raise ValueError(checks[-1])
    swept=cylinder(11,7.199426738596786-2.8181766385967233,0,21.75,2.8181766385967233)
    blade=[]
    for name,_,s in extras+[(n,c,t) for n,c,t in items if c not in ['fan','fan_motor','fan_mount']]:
        v=s.intersect(swept).Volume();d=s.distance(swept)
        assert v<1e-5 and d>0
        blade.append(dict(part=name,volume_mm3=v,distance_mm=d))
    colors={**COLORS,'upper':('#dbad3e','上部固定基板（ToraNeko改）'),'post':('#d3d8df','支柱（ToraNeko形状）'),'fastener':('#384250','M1.4ネジの占有形状')}
    assy=cq.Assembly(name='NEW_HALF_A07');fig=go.Figure();mesh={}
    for name,cat,s in items+extras:
        h=colors[cat][0];assy.add(s,name=name,color=cq.Color(*(int(h[n:n+2],16)/255 for n in (1,3,5))))
        v,f=s.tessellate(.08,.18);m=mesh.setdefault(cat,dict(v=[],f=[]));base=len(m['v'])
        m['v'].extend([p.toTuple() for p in v]);m['f'].extend([[i+base for i in face] for face in f])
    for cat,m in mesh.items():
        v,f=m['v'],m['f'];fig.add_trace(go.Mesh3d(x=[p[0] for p in v],y=[p[1] for p in v],z=[p[2] for p in v],i=[p[0] for p in f],j=[p[1] for p in f],k=[p[2] for p in f],color=colors[cat][0],name=colors[cat][1],showlegend=True,visible='legendonly' if cat=='battery' else True))
    fig.update_layout(title='A07 — ファン中心を車軸寄りへ：Y=21.75 mm',scene=dict(aspectmode='data',xaxis_title='X [mm]',yaxis_title='Y [mm]',zaxis_title='Z [mm]',camera=dict(eye=dict(x=1.5,y=-1.8,z=1.3))),margin=dict(l=0,r=0,t=60,b=0))
    (ROOT/'assembly-a07.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>A07</title><body><p>回転：ドラッグ／拡大：ホイール。凡例で表示切替。電池は初期非表示。ToraNekoの上部固定基板と前側支柱を使用し、ファン中心をY=16.5→21.75 mmへ移動。電池はY=33を維持し左右へ各3.2 mm移動。Φ22羽根用。ねじ頭・長さは仮定。基板にΦ8吸入口を追加、流路・スカート・電池ホルダーは未設計。重心未更新・製造用未確定。<br>参照CAD: Copyright (c) 2026 Tokoro0917 / MIT License（third_party/ToraNeko.Mk3.LICENSE）。</p>'+fig.to_html(full_html=False,include_plotlyjs=True,default_height='85vh')+'</body></html>')
    assy.export(str(ROOT/'assembly-a07.step'));assert exportGLTF(assy,str(ROOT/'assembly-a07.glb'),binary=True,tolerance=.08,angularTolerance=.18)
    cq.exporters.export(upper,str(ROOT/'upper-plate-a07.step'));cq.exporters.export(board,str(ROOT/'pcb-a07-concept.step'))
    restored=cq.importers.importStep(str(ROOT/'assembly-a07.step')).val()
    assert restored.isValid() and len(restored.Solids())==len(assy.toCompound().Solids())
    b=exact_bounds(restored);assert b.xmin>=-19.5-1e-5 and b.xmax<=19.5+1e-5 and b.zmin>=-1e-5 and b.zmax<=22 and b.ymin>=0 and b.ymax<=66
    result=dict(fan_axis_y_mm=21.75,fan_shift_y_mm=5.25,battery_centers_x_mm=[-9.5,9.5],battery_center_y_mm=33,source_sha256=EXPECTED_SHA,parts=len(items+extras),solids=len(restored.Solids()),step_roundtrip_valid=True,dimensions_xyz_mm=[b.xlen,b.ylen,b.zlen],checks=checks,blade_swept_envelope_checks=blade,upper_plate_volume_mm3=upper.Volume(),upper_plate_assumed_fr4_mass_g=upper.Volume()*1.85/1000,
        note='Source posts preserved. Fan translated +5.25 mm Y; batteries shifted outward 3.2 mm each; upper plate drive holes moved inward 0.3 mm; M1.4 thread engagement exempted, strength unverified. Original cages omitted as in A04.')
    (ROOT/'fan-mount-a07-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(12,8));ax=fig.add_subplot(projection='3d');faces=[];cs=[]
    for cat,m in mesh.items():
        if cat=='battery':continue
        faces.extend([[m['v'][i] for i in face] for face in m['f']]);cs.extend([colors[cat][0]]*len(m['f']))
    ax.add_collection3d(Poly3DCollection(faces,facecolors=cs,edgecolors=cs,linewidths=0,shade=True))
    ax.set(xlim=(-21,21),ylim=(0,63),zlim=(0,22),xlabel='X [mm]',ylabel='Y [mm]',zlabel='Z [mm]');ax.set_box_aspect((42,63,22));ax.view_init(35,-65)
    fig.suptitle('A07 - Fan axis Y=21.75 (5.25 mm toward axle)',fontsize=18)
    fig.text(.08,.04,'Batteries hidden (shifted outward 3.2 mm each) | Fan Y=21.75 | Axle Y=33\nRear ears attach to drive mounts. D22 blade. Duct/skirt and fastener strength not verified.',fontsize=11)
    fig.savefig(ROOT/'fan-mount-a07.png',dpi=150);plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
if __name__=='__main__':main()
