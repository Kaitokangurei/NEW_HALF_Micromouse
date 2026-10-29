"""STEPの部品インスタンスを世界座標で測る（cadquery 2.8.0）。

使い方: python measure_step.py input.step output.json
同名の軸受を区別するため、名前だけでなく階層内の番号も記録する。
外接箱は材料寸法や重量を保証しない。元のモデルは変更しない。
"""
import hashlib
import json
from pathlib import Path
import sys

import cadquery as cq
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool


def read_parts(path):
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise ValueError("STEPの読み込みに失敗")
    doc = TDocStd_Document(TCollection_ExtendedString("measurement"))
    if not reader.Transfer(doc):
        raise ValueError("STEPの形状変換に失敗")
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = TDF_LabelSequence()
    tool.GetFreeShapes(roots)

    def label_name(label):
        attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
            return attr.Get().ToExtString()
        return "unnamed"

    def visit(label, location, prefix):
        location = location.Multiplied(tool.GetLocation_s(label))
        if tool.IsReference_s(label):
            ref = TDF_Label()
            tool.GetReferredShape_s(label, ref)
            label = ref
        name = prefix + ":" + label_name(label)
        if tool.IsAssembly_s(label):
            children = TDF_LabelSequence()
            tool.GetComponents_s(label, children)
            for i in range(1, children.Length()+1):
                yield from visit(children.Value(i), location, name+f"/{i}")
        else:
            raw = tool.GetShape_s(label)
            if raw.IsNull():
                raise ValueError(f"形状のない部品: {name}")
            yield name, cq.Shape.cast(raw).moved(cq.Location(location))

    for i in range(1, roots.Length()+1):
        yield from visit(roots.Value(i), TopLoc_Location(), str(i))


def measure(path):
    rows = []
    empty = []
    for name, shape in read_parts(path):
        if not shape.Vertices():
            empty.append(name)
            continue
        b = shape.BoundingBox()
        rows.append({"name": name,
                     "min_mm": [b.xmin,b.ymin,b.zmin],
                     "max_mm": [b.xmax,b.ymax,b.zmax],
                     "size_mm": [b.xlen,b.ylen,b.zlen]})
    return {"source_file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "cadquery_version": cq.__version__,
            "coordinates": "source STEP world coordinates; mm",
            "empty_shapes": empty,
            "parts": rows}


if __name__ == "__main__":
    source, output = map(Path, sys.argv[1:])
    result = measure(source)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{len(result['parts'])} instances -> {output}")
