# -*- coding: utf-8 -*-
import json, re
from collections import defaultdict
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

DISTRICTS = ['七股區','下營區','中西區','仁德區','佳里區','六甲區','北區','北門區','南化區','南區',
 '善化區','大內區','學甲區','安南區','安定區','安平區','官田區','將軍區','山上區','左鎮區',
 '後壁區','新化區','新市區','新營區','東區','東山區','柳營區','楠西區','歸仁區','永康區',
 '玉井區','白河區','西港區','關廟區','鹽水區','麻豆區','龍崎區']
MARKERS = {}
for d in DISTRICTS:
    MARKERS[d] = d
    core = d[:-1] if d.endswith('區') else d
    if len(core) >= 2: MARKERS.setdefault(core, d)
MARK_RE = re.compile('(' + '|'.join(sorted(MARKERS, key=len, reverse=True)) + r')\s*[:：]')

VARIANT = {'塩':'鹽','晋':'晉','峯':'峰','脚':'腳','曺':'曹','裡':'里'}
ALIAS = {  # claim 里名 -> 官方里名 (人工核對後補；同名跨區少見故用名對名)
 '仁里里':'仁里里','仁里':'仁里里','科里':'科里里','豐里':'豐里里',
}
SCHOOL_RE = re.compile(r'[一-鿿]{2,5}(國民小學|國民中學|國中小|國小|國中|實小|附小|高中|完全中學|中學)')
BAD_KW = ('國小','國中','實驗','招收','設籍','學生','學校','共同','學區','附小','實小','高中','中學','以上','本市','。','區公所')

def canon(v):
    v = v.replace('[','').replace(']','').strip()
    v = ''.join(VARIANT.get(c,c) for c in v)
    v = ALIAS.get(v, v)
    return v

def tokens(body):
    b = re.sub(r'（[^）]*）','',body); b = re.sub(r'\([^\)]*\)','',b)
    b = SCHOOL_RE.sub('', b)
    out = []
    for tok in re.split(r'[，,]', b):
        tok = tok.strip()
        if not tok: continue
        if any(k in tok for k in BAD_KW): continue
        partial = ('鄰' in tok) or bool(re.search(r'[0-9０-９]', tok))
        core = re.sub(r'[0-9０-９\-–—、~至\s鄰（）()]','', tok).strip('，,、')
        if not core: continue
        for p in [x for x in core.split('里') if x]:
            if len(p) > 8 or any(k in p for k in BAD_KW): continue
            out.append((canon(p+'里'), not partial))
    return out

def parse_cell(cell):
    txt = (cell or '').replace('\n','').replace(' ','').replace('　','')
    txt = txt.replace('東西庄','東庄，西庄')
    ms = list(MARK_RE.finditer(txt)); res = []
    for i,m in enumerate(ms):
        dist = MARKERS[m.group(1)]
        s = m.end(); e = ms[i+1].start() if i+1 < len(ms) else len(txt)
        for v,w in tokens(txt[s:e]): res.append((dist, v, w))
    return res

def load(rows_fn, level):
    rows = json.load(open(rows_fn, encoding='utf-8')); schools = []; home = None
    for r in rows:
        no,dc,nc,basic,common = (r + [None]*5)[:5]
        d = (dc or '').replace('\n','').replace(' ','').strip()
        n = (nc or '').replace('\n','').replace(' ','').strip()
        if d: home = d
        if not n or n in ('學校名稱','學校'):
            if schools and (basic or common):
                schools[-1]['basic'] += parse_cell(basic); schools[-1]['common'] += parse_cell(common)
            continue
        schools.append({'home':home or '','school':n,'school_id':(home or '')+n,'level':level,
                        'basic':parse_cell(basic),'common':parse_cell(common)})
    return schools

def seg(core, valid):
    n = len(core); dp = [None]*(n+1); dp[0] = []
    for i in range(1, n+1):
        for l in (2,3):
            if i-l >= 0 and dp[i-l] is not None and core[i-l:i] in valid:
                dp[i] = dp[i-l] + [core[i-l:i]]; break
    return dp[n]

def build(level, rows_fn, tainan):
    schools = load(rows_fn, level)
    homeof = {s['school_id']: s['home'] for s in schools}
    claims = defaultdict(list)
    for s in schools:
        for d,v,w in s['basic']:  claims[(d,v)].append((s['school_id'],0,w))
        for d,v,w in s['common']: claims[(d,v)].append((s['school_id'],1,w))
    def resolve(lst):
        return sorted(lst, key=lambda x:(x[1], not x[2]))[0][0]
    off_by_dist = defaultdict(dict)     # dist -> {core: idx}
    for idx, p in tainan:
        off_by_dist[p['TOWNNAME'].strip()][canon(p['VILLNAME'])[:-1]] = idx
    village_school = {}; used = set(); rec = []
    # pass 1: exact
    for idx, p in tainan:
        key = (p['TOWNNAME'].strip(), canon(p['VILLNAME']))
        if key in claims:
            village_school[idx] = resolve(claims[key]); used.add(key)
    # pass 2: concat split (黏字) via official 里名庫
    for (d,cname), lst in list(claims.items()):
        if (d,cname) in used: continue
        valid = off_by_dist.get(d,{})
        parts = seg(cname[:-1], valid)
        if parts and len(parts) > 1:
            sid = resolve(lst)
            for pc in parts:
                village_school.setdefault(valid[pc], sid)
            used.add((d,cname)); rec.append(f"[切分]{d}{cname} -> "+"+".join(p+'里' for p in parts))
    # pass 3: constrained 1-char-diff within district, unique
    rem_off = [(idx,d,core) for d in off_by_dist for core,idx in off_by_dist[d].items() if idx not in village_school]
    rem_claims = defaultdict(list)
    for (d,cname) in claims:
        if (d,cname) in used: continue
        rem_claims[d].append((cname[:-1], resolve(claims[(d,cname)]), (d,cname)))
    for idx,d,ocore in rem_off:
        cands = [(cc,sid,k) for (cc,sid,k) in rem_claims.get(d,[]) if len(cc)==len(ocore) and sum(a!=b for a,b in zip(cc,ocore))==1]
        if len(cands)==1:
            cc,sid,k = cands[0]; village_school[idx]=sid; used.add(k); rec.append(f"[近似]{d}{ocore}里 ~ {cc}里")
    covered = set(village_school)
    uncovered = sorted(f"{p['TOWNNAME']}{p['VILLNAME']}" for i,p in tainan if i not in covered)
    unmatched = sorted(f"{d}{v}" for (d,v) in claims if (d,v) not in used)
    return schools, homeof, village_school, uncovered, unmatched, rec

if __name__ == '__main__':
    d = json.load(open('cunli2026.json', encoding='utf-8'))
    tainan = []; geom = {}
    for i,ft in enumerate(d['features']):
        p = ft['properties']
        if '南市' in p['COUNTYNAME'] and ('臺南' in p['COUNTYNAME'] or '台南' in p['COUNTYNAME']):
            tainan.append((i,p)); geom[i] = ft['geometry']
    total = len(tainan)
    summary = []
    for level, rows_fn, out in [('國小','GS_rows.json','gs'),('國中','JH_rows.json','jh')]:
        schools, homeof, vsch, unc, unmatched, rec = build(level, rows_fn, tainan)
        groups = defaultdict(list)
        for idx, sid in vsch.items(): groups[sid].append(geom[idx])
        feats = []
        E = 0.00028
        for sid, geoms in groups.items():
            try:
                m = unary_union([shape(g).buffer(E, join_style=2, mitre_limit=2.0) for g in geoms])
                m = m.buffer(-E, join_style=2, mitre_limit=2.0)
                merged = m.simplify(0.00006, preserve_topology=True)
            except Exception:
                merged = unary_union([shape(g) for g in geoms]).simplify(0.00006, preserve_topology=True)
            feats.append({'type':'Feature','properties':{'school':sid,'home':homeof.get(sid,''),
                          'level':level,'n_vill':len(geoms)},'geometry':mapping(merged)})
        json.dump({'type':'FeatureCollection','features':feats},
                  open(f'{out}.geojson','w',encoding='utf-8'), ensure_ascii=False)
        cov = len(vsch)
        rep = [f"=== {level} ===",
               f"zones: {len(feats)} / parsed schools {len(schools)}",
               f"里 covered: {cov}/{total} ({cov*100//total}%)  uncovered:{total-cov}",
               f"unmatched claims: {len(unmatched)}",
               f"recovered (切分/近似): {len(rec)}","",
               "-- recovered --", *rec, "",
               "-- uncovered 里 (官方有,學區表未對到) --", *unc, "",
               "-- unmatched claims (學區表有,官方無此里) --", *unmatched, ""]
        open(f'{out}_qa.txt','w',encoding='utf-8').write("\n".join(rep))
        summary.append(f"{level}: zones={len(feats)} covered={cov}/{total}({cov*100//total}%) uncovered={total-cov} unmatched={len(unmatched)}")
    print("\n".join(summary))
