# -*- coding: utf-8 -*-
import json, re
from collections import defaultdict
from shapely.geometry import shape, Point

SITE = r'H:\我的雲端硬碟\SW_Agent\school-district-map\site'

def norm(n):
    n = n.strip()
    for p in ['臺南市立','台南市立','臺南市','台南市','市立','私立','縣立','國立','附設']:
        n = n.replace(p,'')
    n = n.replace('國民小學','國小').replace('國民中學','國中').replace('國中小','國中')
    n = re.sub(r'[（(].*?[）)]','',n)
    return n.strip()

osm = json.load(open('osm_schools.json', encoding='utf-8'))
by_name = defaultdict(list)
for e in osm['elements']:
    t = e.get('tags',{}); nm = t.get('name')
    if not nm: continue
    lat = e.get('lat') or (e.get('center') or {}).get('lat')
    lon = e.get('lon') or (e.get('center') or {}).get('lon')
    if lat is None: continue
    by_name[norm(nm)].append((lat,lon))

points = {}; exact = 0; fb = 0; unmatched = []
for fn,lvl in [('gs.geojson','國小'),('jh.geojson','國中')]:
    d = json.load(open(fr'{SITE}\{fn}', encoding='utf-8'))
    for f in d['features']:
        sid = f['properties']['school']; home = f['properties']['home']
        core = norm(sid[len(home):] if sid.startswith(home) else sid)
        cands = by_name.get(core, [])
        geom = shape(f['geometry'])
        pt = None
        if len(cands) == 1:
            pt = cands[0]; exact += 1
        elif len(cands) > 1:
            inside = [c for c in cands if geom.contains(Point(c[1],c[0]))]
            if inside: pt = inside[0]
            else:
                cen = geom.representative_point()
                pt = min(cands, key=lambda c:(c[0]-cen.y)**2+(c[1]-cen.x)**2)
            exact += 1
        if pt is None:
            cen = geom.representative_point(); pt = (cen.y, cen.x); fb += 1; unmatched.append(sid)
        points[sid] = [round(pt[0],5), round(pt[1],5)]

json.dump(points, open('school_points.json','w',encoding='utf-8'), ensure_ascii=False, separators=(',',':'))
import os
open('match_report.txt','w',encoding='utf-8').write(
    f"總校 {len(points)}  OSM精確 {exact}  中心點補 {fb}  size {os.path.getsize('school_points.json')}\n"
    + "補中心點(OSM無):\n" + "、".join(unmatched))
print("done. schools",len(points),"exact",exact,"fallback",fb)
