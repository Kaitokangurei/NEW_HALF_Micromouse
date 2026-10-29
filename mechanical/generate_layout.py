"""配置検討A01をSVGに出力する。標準ライブラリのみ。製造用図面ではない。"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).with_name("layout-a01.svg")
SCALE = 8
ORIGIN_X = 260
ORIGIN_Y = 110


def point(x, y):
    return ORIGIN_X + SCALE * x, ORIGIN_Y + SCALE * y


def text(x, y, value, size=15, color="#263746"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(value)}</text>'


def rect(x, y, width, height, fill, stroke, dash=""):
    px, py = point(x, y)
    return (f'<rect x="{px}" y="{py}" width="{width*SCALE}" height="{height*SCALE}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-dasharray="{dash}"/>')


def line(x1, y1, x2, y2, color="#64748b", dash=""):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="1.5" stroke-dasharray="{dash}"/>')


def generate():
    # この検査は概略の外接枠だけ。未配置部品の干渉や機体の成立性は検証しない。
    assert 32 + 5 <= 39
    assert 18 - 15 >= 0 and 18 + 15 <= 66
    assert 46 - 12.5 >= 0 and 46 + 12.5 <= 66
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="760" viewBox="0 0 1000 760">',
             '<rect width="1000" height="760" fill="#f8fafc"/>',
             '<g font-family="sans-serif">',
             text(35, 36, "NEW HALF / 配置検討 A01", 24),
             text(35, 63, "単位 mm・上面図 ／ 仮配置・製造不可 ／ 前方は上", 15),
             rect(-19.5, 0, 39, 66, "none", "#475569", "7 5")]
    # 新規の基板候補。車輪部分では幅24 mmまで切り欠く。
    outline = [(-13,5),(13,5),(17,9),(17,31),(12,31),(12,49),
               (17,49),(17,57),(13,61),(-13,61),(-17,57),(-17,49),
               (-12,49),(-12,31),(-17,31),(-17,9)]
    coords = " ".join(f"{point(x,y)[0]},{point(x,y)[1]}" for x,y in outline)
    parts.append(f'<polygon points="{coords}" fill="#dcfce7" stroke="#15803d" stroke-width="2"/>')
    cx, cy = point(0,18)
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="120" fill="#dbeafe" fill-opacity="0.75" stroke="#2563eb" stroke-width="2"/>')
    parts += [text(cx-48,cy-8,"ファン Φ30",16),text(cx-48,cy+15,"中心 Y=18",13)]
    for x in (-18.5,13.5):
        parts.append(rect(x,33,5,14,"#334155","#0f172a"))
    for x in (-12.3,0.3):
        parts.append(rect(x,33.5,12,25,"#fef3c7","#d97706","4 3"))
    parts += [text(182,490,"電池 12×25×6 ×2",16),text(185,514,"上段・駆動部の上",14)]
    parts.append(line(*point(-19.5,40),*point(19.5,40),"#be123c","5 4"))
    parts.append(line(*point(0,0),*point(0,66),"#64748b","3 4"))
    # 外接寸法線。
    parts += [line(104,87,416,87),line(104,80,104,104),line(416,80,416,104),text(220,81,"39 mm",16),
              line(70,110,70,638),line(63,110,97,110),line(63,638,97,638),text(12,380,"66 mm",15),
              text(180,665,"後方 ／ 外接枠は完成機の目標",14)]
    for start,end in [((-12,8),(-16,3)),((12,8),(16,3)),((-13,24),(-19,24)),((13,24),(19,24))]:
        parts.append(line(*point(*start),*point(*end),"#9333ea"))
    notes = [
        ("寸法の根拠",22,"#0f172a"),
        ("目標外形：66 × 39 × 22 mm / 23 g",17,"#0f172a"),
        ("基板候補：最大幅34 × 長さ56 mm",17,"#15803d"),
        ("車軸：Y=40、トレッド32（仮）",17,"#be123c"),
        ("車輪：Φ14、幅5（幅は未測定）",17,"#334155"),
        ("タイヤを含む幅：37 mm（上記仮定）",16,"#334155"),
        ("電池：中心X=±6.3、Y=46（仮）",16,"#b45309"),
        ("青：ファン単体 / 黄破線：上段電池",16,"#263746"),
        ("紫：センサ測距方向の候補",16,"#9333ea"),
        ("未配置・要検証",22,"#0f172a"),
        ("モータ・ギア・エンコーダ・軸受",17,"#b91c1c"),
        ("ファンケース・支持部・吸排気流路",17,"#b91c1c"),
        ("センサ本体・ホルダー・取り付け穴",17,"#b91c1c"),
        ("コネクタ・配線・部品高さ・重量",17,"#b91c1c"),
        ("高さ22 mmの成立性は未確認",17,"#b91c1c"),
        ("図形の重なりは上下層の想定を含む。",15,"#475569"),
        ("干渉がないことを示す図ではありません。",15,"#475569")]
    for i,(label,size,color) in enumerate(notes):
        parts.append(text(475,128+i*30,label,size,color))
    parts += [text(35,715,"参照：ToraNeko.Mk3 724d4f4 / type6 6e151e0 / 大会寸法はユーザー提供",14),
              text(35,739,"詳細・出典・未解決事項：docs/layout-a01.md",14),'</g></svg>']
    OUT.write_text("\n".join(parts)+"\n",encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    generate()
