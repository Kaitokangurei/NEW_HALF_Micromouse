"""A07ベースの上部固定基板を3点支持へ変更。センサ穴は呼出側で生成。"""
import math
import cadquery as cq
from build_fan_mount_a05 import cylinder
Z=1.7869267385966008
TOP=Z+9.1
POINTS=[(0.,8.5),(-11.6,29.25),(11.6,29.25)]

def capsule(a,b,width):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    s=cq.Workplane('XY').box(length,width,.6).val().rotate((0,0,0),(0,0,1),math.degrees(math.atan2(dy,dx)))
    s=s.translate(((a[0]+b[0])/2,(a[1]+b[1])/2,TOP+.3))
    return s.fuse(cylinder(width/2,.6,*a,TOP)).fuse(cylinder(width/2,.6,*b,TOP))

def convert(items):
    source=dict((n,s) for n,c,s in items)
    upper=cylinder(6,.6,0,21.75,TOP)
    for p in POINTS:upper=upper.fuse(capsule((0,21.75),p,3.6))
    upper=upper.cut(cylinder(3.05,1,0,21.75,TOP-.2))
    for x,y in POINTS+[(-4.5,21.75),(4.5,21.75)]:upper=upper.cut(cylinder(.7,1,x,y,TOP-.2))
    upper=upper.clean();assert upper.isValid() and len(upper.Solids())==1
    old=source['front_post_0'];b=old.BoundingBox();delta=(-(b.xmin+b.xmax)/2,8.5-(b.ymin+b.ymax)/2,0)
    post=old.translate(delta)
    # 古い前側2穴を埋め、新しい中央支柱用穴へ変更。
    board=source['063_pcb']
    for x in (-8.9,8.9):board=board.fuse(cylinder(.8,.6,x,12.25,Z))
    board=board.cut(cylinder(.8,1,0,8.5,Z-.2)).clean()
    result=[]
    removed={'upper_plate','front_post_0','front_post_1','front_top_0','front_top_1','front_bottom_0','front_bottom_1'}
    for n,c,s in items:
        if n in removed:continue
        result.append((n,c,board if c=='pcb' else s))
    result.extend([('upper_plate','upper',upper),('center_post','post',post)])
    for name,start,direction in [('center_top',TOP+.6,-1),('center_bottom',Z,1)]:
        if direction==-1:s=cylinder(.7,3,0,8.5,start-3).fuse(cylinder(1.25,.6,0,8.5,start))
        else:s=cylinder(.7,3,0,8.5,start).fuse(cylinder(1.25,.6,0,8.5,start-.6))
        result.append((name,'fastener',s))
    assert len(result)==74
    return result
