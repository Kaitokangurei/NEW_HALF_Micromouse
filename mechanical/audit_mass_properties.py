"""STEP材質設定とA04の体積図心を監査。体積図心を実機重心とは扱わない。"""
import hashlib
import json
from pathlib import Path
import re
import sys
import cadquery as cq
from measure_step import read_parts
from check_layout_a03 import EXPECTED_SHA, PCB_Z, AXLE_SOURCE_Y

ROOT=Path(__file__).resolve().parent


def decode_step(text):
    return re.sub(r'\\X2\\([0-9A-F]+)\\X0\\',lambda m:bytes.fromhex(m[1]).decode('utf-16-be'),text)


def audit(path):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED_SHA:raise ValueError('入力版が異なります')
    records=dict(re.findall(r'#(\d+)\s*=\s*(.*?);',path.read_text(),re.S))
    materials={}
    for value in records.values():
        match=re.fullmatch(r'PROPERTY_DEFINITION_REPRESENTATION\(#(\d+),#(\d+)\)',value.strip())
        if not match:continue
        prop=re.fullmatch(r"PROPERTY_DEFINITION\('material property','(material name|density of part)',#(\d+)\)",records[match[1]].strip())
        if not prop:continue
        product=prop[2]
        name=decode_step(re.findall(r"'([^']*)'",records[product])[1]).replace('\n',' ')
        item_ref=re.search(r'\(#(\d+)\)',records[match[2]])[1]
        item=records[item_ref]
        row=materials.setdefault(product,{'product_definition_id':product,'name':name})
        if prop[1]=='material name':
            row['material']=decode_step(re.findall(r"'([^']*)'",item)[0])
        else:
            density,unit=re.search(r'POSITIVE_RATIO_MEASURE\(([^)]+)\),#(\d+)',item).groups()
            # この入力版の密度単位を、kg × metre^-3の参照連鎖で確認する。
            units=[records[k].strip() for k in re.findall(r'#(\d+)',records[unit])]
            assert len(units)==2
            mass_ref=re.fullmatch(r'DERIVED_UNIT_ELEMENT\(#(\d+),1\.\)',units[0])[1]
            length_ref=re.fullmatch(r'DERIVED_UNIT_ELEMENT\(#(\d+),-3\.\)',units[1])[1]
            assert 'SI_UNIT(.KILO.,.GRAM.)' in records[mass_ref]
            assert 'SI_UNIT($,.METRE.)' in records[length_ref]
            row['density_kg_m3']=float(density)
    geometry=[]
    for name,shape in read_parts(path):
        if not any(t in name for t in ['NFP-D0812','/11:MK06-45','/12:吸引ファンモータマウント','/15:吸引ファン(アクリル) v3/2:SOLID']):continue
        if not shape.isValid():raise ValueError('対象形状が不正: '+name)
        if '足回り' in name:
            dx=13.7 if '/2:足回り' in name else 13.1
            delta=(dx,33-AXLE_SOURCE_Y,PCB_Z)
        else:delta=(13.4,16.5-(AXLE_SOURCE_Y-11.25),PCB_Z)
        shape=shape.translate(delta);c=shape.Center()
        geometry.append({'name':name,'volume_mm3':shape.Volume(),
                         'uniform_density_centroid_mm':[c.x,c.y,c.z],
                         'actual_mass_g':None,'actual_cg_mm':None})
    board=cq.importers.importStep(str(ROOT/'pcb-a04-concept.step')).val();c=board.Center()
    geometry.append({'name':'A04 bare PCB geometry','volume_mm3':board.Volume(),
                     'uniform_density_centroid_mm':[c.x,c.y,c.z],
                     'actual_mass_g':None,'actual_cg_mm':None})
    output={'source_sha256':EXPECTED_SHA,'material_settings':list(materials.values()),
            'a04_geometry':geometry,'conclusion':'CAD density settings unsuitable for actual assembled mass / CG',
            'actual_total_mass_g':None,'actual_whole_robot_cg_mm':None}
    (ROOT/'mass-properties-audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(geometry,ensure_ascii=False,indent=2))


if __name__=='__main__':audit(Path(sys.argv[1]))
