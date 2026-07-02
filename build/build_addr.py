# -*- coding: utf-8 -*-
# 官方門牌CSV -> 按區切的地址索引: addr/<區>.json = {li:[...], g:{ "路|巷|弄": [[號key, liIdx, 鄰], ...sorted] }}
import json, csv, os, gzip
from collections import defaultdict

FW = str.maketrans('０１２３４５６７８９','0123456789')
ref = json.load(open('ref.json', encoding='utf-8'))
code2dist = ref['code2dist']

def norm_hao(s):
    s = s.translate(FW).replace('號','').replace('之','-').replace('–','-').replace('~','-').strip()
    return s

def hao_key(s):
    parts = s.split('-')
    try: a = int(parts[0])
    except: return (10**9, 0)
    b = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return (a, b)

# 區 -> {路|巷|弄: {號key_str: (里,鄰)}}
buckets = defaultdict(lambda: defaultdict(dict))
with open('tn_addr.csv', encoding='utf-8-sig', newline='') as f:
    r = csv.reader(f); next(r)
    for row in r:
        code, li, kin, road, area, xiang, nong, hao = row[2], row[3].strip(), row[4].strip(), row[5].strip(), row[6].strip(), row[7].strip(), row[8].strip(), row[9].strip()
        dist = code2dist.get(code)
        if not dist or not li or not hao: continue
        road = road or area or li   # 鄉下無路名時退地區/里
        k = norm_hao(hao)
        if not k or not k[0].isdigit(): continue
        try: kn = int(kin)
        except: kn = 0
        buckets[dist][f'{road}|{xiang}|{nong}'][k] = (li, kn)

os.makedirs('addr', exist_ok=True)
sizes = []
for dist, groups in buckets.items():
    lis = sorted({v[0] for g in groups.values() for v in g.values()})
    liidx = {l:i for i,l in enumerate(lis)}
    g = {}
    for key, hd in groups.items():
        arr = sorted(([k, liidx[v[0]], v[1]] for k,v in hd.items()), key=lambda e: hao_key(e[0]))
        g[key] = arr
    obj = {'li': lis, 'g': g}
    fn = f'addr/{dist}.json'
    data = json.dumps(obj, ensure_ascii=False, separators=(',',':'))
    open(fn,'w',encoding='utf-8').write(data)
    gz = len(gzip.compress(data.encode('utf-8')))
    sizes.append((dist, len(groups), sum(len(v) for v in g.values()), len(data), gz))

sizes.sort(key=lambda x:-x[4])
rep = ["區, 街段組數, 門牌數, raw bytes, gzip bytes"]
tot_raw = tot_gz = 0
for d,ng,nh,raw,gz in sizes:
    rep.append(f"{d}: {ng}組 {nh}門牌 raw={raw//1024}KB gzip={gz//1024}KB")
    tot_raw += raw; tot_gz += gz
rep.append(f"\n總計 raw={tot_raw//1024}KB gzip={tot_gz//1024}KB ; 最大區 gzip={sizes[0][4]//1024}KB ({sizes[0][0]})")
open('addr_sizes.txt','w',encoding='utf-8').write("\n".join(rep))
print("done. districts:", len(sizes), "| total gzip KB:", tot_gz//1024, "| max district gzip KB:", sizes[0][4]//1024)
