# -*- coding: utf-8 -*-
# 從官方門牌CSV + kiang里界 建:區碼->區名、(區,里)->鄰set
import json, csv
from collections import defaultdict, Counter

# kiang: 里名 -> 區名 (可能一里多區,故保留set)
vill = json.load(open('cunli2026.json', encoding='utf-8'))
li2dist = defaultdict(set)
for ft in vill['features']:
    p = ft['properties']
    if '南市' in p['COUNTYNAME']:
        li2dist[p['VILLNAME'].strip()].add(p['TOWNNAME'].strip())

# CSV: 每個區碼收集其里名 -> 多數決對應區名
code_li = defaultdict(Counter)          # code -> Counter(里名)
code_li_kin = defaultdict(lambda: defaultdict(set))  # code -> 里 -> set(鄰)
with open('tn_addr.csv', encoding='utf-8-sig', newline='') as f:
    r = csv.reader(f); next(r)
    for row in r:
        code = row[2]; li = row[3].strip(); kin = row[4].strip()
        if not li: continue
        code_li[code][li] += 1
        if kin:
            try: code_li_kin[code][li].add(int(kin))
            except ValueError: pass

# 區碼 -> 區名 (多數決:該碼所有里對到的區,取最多)
code2dist = {}
for code, cnt in code_li.items():
    votes = Counter()
    for li, n in cnt.items():
        for d in li2dist.get(li, ()):
            votes[d] += n
    if votes:
        code2dist[code] = votes.most_common(1)[0][0]

# (區名|里)->鄰list
kin = {}
for code, lis in code_li_kin.items():
    dist = code2dist.get(code)
    if not dist: continue
    for li, kins in lis.items():
        kin[f'{dist}|{li}'] = sorted(kins)

json.dump({'code2dist': code2dist, 'kin': kin},
          open('ref.json', 'w', encoding='utf-8'), ensure_ascii=False)

# report
out = []
out.append(f"區碼數: {len(code2dist)} (應~37)")
out.append("區碼->區名: " + ", ".join(f"{c}={d}" for c,d in sorted(code2dist.items())))
out.append(f"(區,里) 有鄰資料筆數: {len(kin)}")
# sample: 東區 各里鄰數
east = {k:v for k,v in kin.items() if k.startswith('東區|')}
out.append(f"東區里數: {len(east)}")
import random
for k in list(east)[:6]:
    out.append(f"  {k}: 鄰 {east[k][:15]}{'...' if len(east[k])>15 else ''} (共{len(east[k])})")
open('ref_report.txt','w',encoding='utf-8').write("\n".join(out))
print("done: codes", len(code2dist), "kin entries", len(kin))
