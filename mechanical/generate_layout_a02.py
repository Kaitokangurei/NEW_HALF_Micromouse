"""測定した駆動部の外接矩形をA02へ配置する。cadqueryは不要、matplotlibが必要。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

ROOT = Path(__file__).resolve().parent


def main():
    data = json.loads((ROOT / "toraneko-v36-bounds.json").read_text())
    parts = data["parts"]
    tires = [p for p in parts if "ミニッツタイヤ" in p["name"]]
    assert len(tires) == 2
    center_x = sum((p["min_mm"][0]+p["max_mm"][0])/2 for p in tires)/2
    axle_y = sum((p["min_mm"][1]+p["max_mm"][1])/2 for p in tires)/2
    floor_z = min(p["min_mm"][2] for p in tires)
    shift_inward = 0.3
    moved = []
    for p in parts:
        if "足回り" not in p["name"]:
            continue
        side = 1 if "/2:足回り" in p["name"] else -1
        offset = [-center_x + side*shift_inward, 40-axle_y, -floor_z]
        moved.append({"name":p["name"],
                      "min_mm":[a+b for a,b in zip(p["min_mm"],offset)],
                      "max_mm":[a+b for a,b in zip(p["max_mm"],offset)]})
    motors = sorted([p for p in moved if "NFP-D0812" in p["name"]],key=lambda p:p["min_mm"][0])
    wheels = [p for p in moved if "ミニッツタイヤ" in p["name"]]
    width = max(p["max_mm"][0] for p in moved)-min(p["min_mm"][0] for p in moved)
    motor_gap = motors[1]["min_mm"][0]-motors[0]["max_mm"][0]
    tread = abs(sum(wheels[0][k][0] for k in ["min_mm","max_mm"])/2-
                sum(wheels[1][k][0] for k in ["min_mm","max_mm"])/2)
    assert 38.79 < width < 38.81
    assert 0.39 < motor_gap < 0.41
    report = {"source_sha256":data["sha256"],"proposal":"A02; rigid inward shift 0.3 mm per drive group",
              "source_floor_z_mm":floor_z,"source_axle_y_mm":axle_y,
              "drive_width_mm":width,"tread_mm":tread,"motor_end_gap_mm":motor_gap,
              "clearance_to_width_limit_per_side_mm":(39-width)/2,
              "note":"Bounding boxes only; no full collision, tolerance, wiring or structural validation",
              "drive_parts":moved}
    (ROOT / "layout-a02-measurements.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    fig,(ax,sideax)=plt.subplots(1,2,figsize=(12,8),gridspec_kw={"width_ratios":[1,1.6]})
    ax.add_patch(Rectangle((-19.5,0),39,66,fill=False,ls="--",ec="#475569"))
    outline=[(-13,5),(13,5),(17,9),(17,31),(12,31),(12,49),(17,49),(17,57),(13,61),(-13,61),(-17,57),(-17,49),(-12,49),(-12,31),(-17,31),(-17,9)]
    ax.add_patch(Polygon(outline,fc="#dcfce7",ec="#15803d",alpha=.6,label="PCB A01 placeholder (needs revision)"))
    ax.add_patch(Circle((0,18),15,fc="none",ec="#2563eb",ls="--",label="Fan reservation D30 (docs)"))
    ax.add_patch(Circle((0,18),11,fc="#dbeafe",ec="#2563eb",alpha=.7,label="STEP fan shape D22"))
    shown=set()
    for p in moved:
        name=p["name"]
        category=next((s for s in ["ミニッツタイヤ","ホイール","NFP-D0812","Spur Gear (41 teeth)","モータマウント","エンコーダ基板"] if s in name),None)
        if category is None:continue
        label,color={"ミニッツタイヤ":("Tire D14 x 3.5","#0f172a"),"ホイール":("Wheel envelope","#64748b"),"NFP-D0812":("Motor incl. shaft/end features","#dc2626"),"Spur Gear (41 teeth)":("41T gear envelope","#9333ea"),"モータマウント":("Motor mount envelope","#d97706"),"エンコーダ基板":("Encoder board / IC","#0891b2")}[category]
        x,y,z=p["min_mm"];xx,yy,zz=p["max_mm"]
        ax.add_patch(Rectangle((x,y),xx-x,yy-y,fill=False,ec=color,lw=1.3,label=label if category not in shown else None))
        sideax.add_patch(Rectangle((y,z),yy-y,zz-z,fill=False,ec=color,alpha=.8))
        shown.add(category)
    for x in [-12.3,.3]:ax.add_patch(Rectangle((x,33.5),12,25,fill=False,ls="--",ec="#b45309"))
    ax.axhline(40,color="#be123c",ls=":",lw=1)
    ax.set(xlim=(-24,24),ylim=(69,-4),xlabel="X [mm]",ylabel="Y [mm]; front = 0",title="Top: target 66 x 39 mm")
    ax.set_aspect("equal");ax.grid(alpha=.15)
    sideax.add_patch(Rectangle((0,0),66,22,fill=False,ls="--",ec="#475569"))
    # 電池を床から13.5 mmへ仮置き。元のモータマウント上端は約12.69 mm。
    sideax.add_patch(Rectangle((33.5,13.5),25,6,fill=False,ls="--",ec="#b45309"))
    sideax.text(34,20,"Battery: Z=13.5..19.5 (proposed)",fontsize=9)
    sideax.set(xlim=(-2,69),ylim=(-1,25),xlabel="Y [mm]",ylabel="Z [mm]; floor = 0",title="Side: drive envelopes + proposed battery")
    sideax.set_aspect("equal");sideax.grid(alpha=.15)
    ax.legend(loc="upper left",bbox_to_anchor=(1.18,-.11),fontsize=8,ncol=2,frameon=False)
    fig.suptitle("A02 / measured drive layout - NOT FOR MANUFACTURE",fontsize=16)
    fig.text(.49,.23,f"Drive width: {width:.2f} mm; tread: {tread:.2f} mm\nMotor end gap: {motor_gap:.2f} mm; outer margin: {(39-width)/2:.2f} mm/side\nFull 3D collision and tolerance checks pending.\nFan case, wiring and sensor holders are not placed.",fontsize=11)
    fig.subplots_adjust(top=.9,bottom=.2,wspace=.4)
    fig.savefig(ROOT / "layout-a02.svg")
    fig.savefig(ROOT / "layout-a02.png",dpi=150)
    print(json.dumps({k:v for k,v in report.items() if k!="drive_parts"},indent=2))


if __name__ == "__main__":
    main()
