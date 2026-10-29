"""A04の参照部品を組み立て、STEP/GLB/独立HTML/PNGを生成する。

参照CADの再配布条件はthird_party/ToraNeko.Mk3.LICENSEを参照。
元の形状を読み込むだけで、参照STEPを変更しない。
"""
import hashlib
import json
from pathlib import Path
import sys

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from cadquery.occ_impl.exporters.assembly import exportGLTF
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import plotly.graph_objects as go

from measure_step import read_parts
from check_layout_a03 import EXPECTED_SHA

ROOT=Path(__file__).resolve().parent
COLORS={
    'pcb':('#23885c','基板候補'), 'battery':('#e8bd38','電池（外形仮置き）'),
    'tire':('#232c36','タイヤ'), 'wheel':('#6c7d8c','ホイール'),
    'motor':('#bac4ce','駆動モータ'), 'gear':('#c59e58','ギア'),
    'mount':('#e3dfcd','駆動部マウント'), 'encoder':('#35a598','エンコーダ基板・IC'),
    'bearing':('#8e9eac','軸受・軸'), 'magnet':('#843c45','磁石'),
    'fan_motor':('#c1cad3','吸引モータ'), 'fan_mount':('#c9c4af','吸引モータマウント'),
    'fan':('#477fbd','羽根（STEP形状Φ22）')}


def exact_bounds(shape):
    # 表示用メッシュの偏差をCAD寸法へ加えない。
    box=Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped,box,False,False)
    return cq.BoundBox(box)


def classify(name):
    for token,category in [('ミニッツタイヤ','tire'),('ホイール','wheel'),('NFP-D0812','motor'),
                           ('Spur Gear','gear'),('モータマウント','mount'),
                           ('エンコーダ基板','encoder'),('磁石','magnet')]:
        if token in name:return category
    return 'bearing'


def make_preview(meshes,cg):
    fig=plt.figure(figsize=(14,7))
    for index,hide_battery in enumerate([False,True],1):
        ax=fig.add_subplot(1,2,index,projection='3d')
        faces=[];colors=[]
        for category,mesh in meshes.items():
            if hide_battery and category=='battery':continue
            v=mesh['vertices'];part_faces=[[v[i] for i in f] for f in mesh['faces']]
            faces.extend(part_faces);colors.extend([COLORS[category][0]]*len(part_faces))
        # 全部品の三角形を一緒に奥行き順で描画し、下の基板が上の部品を隠す誤描画を避ける。
        ax.add_collection3d(Poly3DCollection(faces,facecolors=colors,edgecolors=colors,linewidths=0,shade=True,
                                            lightsource=matplotlib.colors.LightSource(azdeg=300,altdeg=55)))
        ax.set(xlim=(-21,21),ylim=(-1,67),zlim=(0,23),xlabel='X [mm]',ylabel='Y [mm]',zlabel='Z [mm]')
        ax.set_box_aspect((42,68,23));ax.view_init(27,-63)
        ax.set_xticks([-20,0,20]);ax.set_yticks([0,33,66]);ax.set_zticks([0,11,22])
        ax.set_title('A04 / batteries at Y=33' if not hide_battery else 'Battery hidden / drive layout')
    fig.suptitle('NEW HALF - A04 assembly concept',fontsize=20)
    fig.text(.04,.04,'Axle Y=33 mm | Target 66 x 39 x 22 mm | No PCB circuits, ducts, skirt, sensor holders or wiring yet',fontsize=11)
    fig.subplots_adjust(top=.88,bottom=.12,wspace=.02)
    fig.savefig(ROOT/'assembly-a04.png',dpi=140)
    plt.close(fig)


def make_html(meshes,cg):
    fig=go.Figure()
    for category,mesh in meshes.items():
        v=mesh['vertices'];faces=mesh['faces']
        fig.add_trace(go.Mesh3d(x=[p[0] for p in v],y=[p[1] for p in v],z=[p[2] for p in v],
            i=[f[0] for f in faces],j=[f[1] for f in faces],k=[f[2] for f in faces],
            color=COLORS[category][0],name=COLORS[category][1],showlegend=True,
            flatshading=False,lighting=dict(ambient=.55,diffuse=.75,specular=.2,roughness=.7),
            hovertemplate=COLORS[category][1]+'<extra></extra>'))
    # 参照線は物理部品に含めず、HTMLにだけ表示する。
    x=[];y=[];z=[]
    for a,b in [((-19.5,0,0),(19.5,0,0)),((19.5,0,0),(19.5,66,0)),
                ((19.5,66,0),(-19.5,66,0)),((-19.5,66,0),(-19.5,0,0))]:
        x.extend([a[0],b[0],None]);y.extend([a[1],b[1],None]);z.extend([a[2],b[2],None])
    fig.add_trace(go.Scatter3d(x=x,y=y,z=z,mode='lines',line=dict(color='#94a3b8',width=3,dash='dash'),name='目標外形 66×39 mm'))
    fig.add_trace(go.Scatter3d(x=[-19.5,19.5],y=[33,33],z=[7,7],mode='lines',line=dict(color='#7c3aed',width=4,dash='dash'),name='車軸 Y=33（参照線）'))
    fig.add_trace(go.Scatter3d(x=[cg[0]],y=[cg[1]],z=[cg[2]],mode='markers',
        marker=dict(color='#e11d48',size=7,symbol='diamond'),name='概算重心：主要5群各5g',
        hovertemplate='仮定重心 X=%{x:.1f}, Y=%{y:.1f}, Z=%{z:.1f} mm<br>基板等は質量計算に未算入<extra></extra>'))
    categories=list(meshes);n=len(fig.data)
    no_battery=[True]*n;no_battery[categories.index('battery')]=False
    physical=[True]*len(categories)+[False]*3
    fig.update_layout(title=dict(text='A04 組立モデル — 設計検討用',x=.03),
        scene=dict(aspectmode='data',xaxis=dict(title='X [mm]',range=[-22,22]),
                   yaxis=dict(title='Y [mm] 前端=0',range=[-2,68]),zaxis=dict(title='Z [mm] 床=0',range=[0,24]),
                   camera=dict(eye=dict(x=1.5,y=-1.8,z=1.2)),dragmode='orbit'),
        margin=dict(l=0,r=0,t=100,b=0),legend=dict(x=.01,y=.93,bgcolor='rgba(255,255,255,0.8)'),
        updatemenus=[dict(type='buttons',direction='right',x=.02,y=1.05,buttons=[
            dict(label='全表示',method='restyle',args=[{'visible':[True]*n}]),
            dict(label='電池を隠す',method='restyle',args=[{'visible':no_battery}]),
            dict(label='参照線・重心を隠す',method='restyle',args=[{'visible':physical}])])])
    # include_plotlyjs=Trueでネットワーク不要の単独HTMLにする。
    plot=fig.to_html(full_html=False,include_plotlyjs=True,config={'responsive':True,'displaylogo':False},default_height='82vh')
    (ROOT/'assembly-a04.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>A04 3Dモデル</title>'
        '<style>body{margin:0;font-family:sans-serif;background:#f8fafc}aside{padding:12px 24px;font-size:14px;line-height:1.6}</style>'
        '<body><aside>ドラッグで回転、ホイールで拡大。凡例で部品を個別に表示／非表示。<br>'
        '電池は中央配置のままです。赤い重心は主要5グループ各5gという仮定値で、完成機の実測重心ではありません。<br>'
        '未設計：回路・配線・吸引ケース／流路・スカート・センサ支持部。軸受保持器4個は表示省略。製造用確定モデルではありません。<br>'
        '参照CAD：ToraNeko.Mk3 / Copyright (c) 2026 Tokoro0917 / MIT License。詳細は同梱資料を参照。</aside>'+plot+'</body></html>',encoding='utf-8')


def main(source):
    if hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED_SHA:raise ValueError('参照STEPの版が違います')
    layout=json.loads((ROOT/'layout-a04-checks.json').read_text())
    wanted={p['name']:p for p in layout['parts'] if not p['name'].startswith('battery-envelope')}
    raw=dict(read_parts(source))
    items=[];omitted=[]
    for name,p in wanted.items():
        shape=raw[name]
        if 'LF-630_cage' in name:
            omitted.append(name);continue
        if not shape.isValid():raise ValueError('不正な形状: '+name)
        # A04保存済み外接箱から平行移動を復元し、設計座標を二重管理しない。
        b=shape.BoundingBox();offset=tuple(t-s for t,s in zip(p['min_mm'],[b.xmin,b.ymin,b.zmin]))
        shape=shape.translate(offset);b=shape.BoundingBox()
        assert max(abs(t-s) for t,s in zip(p['max_mm'],[b.xmax,b.ymax,b.zmax]))<1e-5
        category=classify(name) if '足回り' in name else ('fan_motor' if '/11:' in name else 'fan_mount' if '/12:' in name else 'fan')
        items.append((name,category,shape))
    board=cq.importers.importStep(str(ROOT/'pcb-a04-concept.step')).val()
    items.append(('new_board_A04','pcb',board))
    for p in layout['parts']:
        if not p['name'].startswith('battery-envelope'):continue
        lo,hi=p['min_mm'],p['max_mm']
        shape=cq.Workplane('XY').box(*(h-l for l,h in zip(lo,hi)),centered=False).val().translate(tuple(lo))
        items.append((p['name'],'battery',shape))
    assert len(items)==66 and len(omitted)==4
    assy=cq.Assembly(name='NEW_HALF_A04')
    meshes={};manifest=[]
    for i,(name,category,shape) in enumerate(items):
        assert shape.isValid()
        h=COLORS[category][0];color=cq.Color(*(int(h[n:n+2],16)/255 for n in (1,3,5)))
        assy.add(shape,name=f'{i:03d}_{category}',color=color)
        vertices,faces=shape.tessellate(.08,.18)
        mesh=meshes.setdefault(category,{'vertices':[],'faces':[]});base=len(mesh['vertices'])
        mesh['vertices'].extend([[p.x,p.y,p.z] for p in vertices])
        mesh['faces'].extend([[index+base for index in face] for face in faces])
        manifest.append({'id':f'{i:03d}_{category}','source_name':name,'category':category,'solids':len(shape.Solids())})
    compound=assy.toCompound();b=exact_bounds(compound)
    print('CAD bounds:',[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],flush=True)
    assert b.xmin>=-19.5-1e-5 and b.xmax<=19.5+1e-5 and b.ymin>=-1e-5 and b.ymax<=66+1e-5 and b.zmin>=-1e-5 and b.zmax<=22+1e-5
    assy.export(str(ROOT/'assembly-a04.step'))
    if not exportGLTF(assy,str(ROOT/'assembly-a04.glb'),binary=True,tolerance=.08,angularTolerance=.18):
        raise RuntimeError('GLB export failed')
    # 書き出したSTEPを読み戻し、形状が失われていないことを確認する。
    restored=cq.importers.importStep(str(ROOT/'assembly-a04.step')).val()
    assert restored.isValid() and len(restored.Solids())==len(compound.Solids())
    rb=exact_bounds(restored)
    assert max(abs(getattr(b,k)-getattr(rb,k)) for k in ['xmin','xmax','ymin','ymax','zmin','zmax'])<1e-4
    cg=json.loads((ROOT/'cg-a04-5g.json').read_text())['cg_mm']
    make_html(meshes,cg);make_preview(meshes,cg)
    summary={'source_sha256':EXPECTED_SHA,'cadquery_version':cq.__version__,'physical_parts':len(items),
             'solid_count':len(compound.Solids()),'step_roundtrip_valid':True,
             'dimensions_xyz_mm':[b.xlen,b.ylen,b.zlen],'bounds_min_mm':[b.xmin,b.ymin,b.zmin],
             'bounds_max_mm':[b.xmax,b.ymax,b.zmax],'omitted_cages':omitted,'parts':manifest,
             'cg_marker_scope':'HTML only; five assumed groups 5g each, not measured complete robot CG',
             'license':'third_party/ToraNeko.Mk3.LICENSE'}
    (ROOT/'assembly-a04-manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['parts','omitted_cages']},ensure_ascii=False,indent=2))


if __name__=='__main__':main(Path(sys.argv[1]))
