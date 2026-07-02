# -*- coding: utf-8 -*-
import json, re
from collections import defaultdict

FW = str.maketrans('０１２３４５６７８９','0123456789')
def canon_li(v):
    v=v.replace('[','').replace(']','').replace('裡','里').strip()
    return v if v.endswith('里') else v+'里'
def parse_kin(text):
    text=text.translate(FW).replace('鄰','')
    ks=set()
    for part in re.split(r'[、,，]', text):
        part=part.strip()
        m=re.match(r'^(\d+)\s*[-–~至]\s*(\d+)$',part)
        if m: ks.update(range(int(m.group(1)),int(m.group(2))+1)); continue
        m=re.match(r'^(\d+)$',part)
        if m: ks.add(int(m.group(1)))
    return ks
def schname(opt):
    return re.split(r'[-－]',opt,1)[-1].strip()
def nd(dist):
    return dist.replace('　','').replace(' ','').strip()

raw=json.load(open('official_raw.json',encoding='utf-8'))

def aggregate(rows):
    # (區|里) -> {'all':set, 'kin':{鄰:set}}
    T=defaultdict(lambda:{'all':set(),'kin':defaultdict(set)})
    unparsed=set()
    for s in rows:
        if '全部' in s['school']: continue
        sn=schname(s['school'])
        for (dist,li,kinspec) in s['recs']:
            dist=nd(dist); li=canon_li(li)
            key=f'{dist}|{li}'; rec=T[key]
            if kinspec.strip() in ('全','全部',''):
                rec['all'].add(sn)
            else:
                ks=parse_kin(kinspec)
                if not ks: unparsed.add(kinspec)
                for k in ks: rec['kin'][k].add(sn)
    out={}
    for key,rec in T.items():
        out[key]={'all':sorted(rec['all']),'kin':{str(k):sorted(v) for k,v in rec['kin'].items()}}
    return out, unparsed

def olookup(T,dist,li,kin):
    rec=T.get(f'{dist}|{li}')
    if not rec: return ('grey',[])
    k=str(kin)
    explicit=rec['kin'].get(k,[])
    if explicit:
        s=sorted(set(explicit))
        return ('green' if len(s)==1 else 'yellow', s)
    if rec['all']:
        return ('green' if len(rec['all'])==1 else 'yellow', rec['all'])
    return ('grey',[])

gsO,gsU=aggregate(raw['gs']); jhO,jhU=aggregate(raw['jh'])
json.dump(gsO,open('gs_nlin.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
json.dump(jhO,open('jh_nlin.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))

# empties
gsE=[s['school'] for s in raw['gs'] if not s['recs']]
jhE=[s['school'] for s in raw['jh'] if not s['recs']]

# 官方版自身綠黃灰分布(覆蓋)
from collections import Counter
ref=json.load(open('ref.json',encoding='utf-8'))['kin']
def tally(O):
    c=Counter()
    for key,kins in ref.items():
        d,li=key.split('|',1)
        for k in kins: c[olookup(O,d,li,k)[0]]+=1
    return c
rep=[]
rep.append(f"官方國小里數:{len(gsO)} 國中里數:{len(jhO)}")
rep.append(f"空校(無學區,多為私立/實驗) 國小({len(gsE)}):{gsE}")
rep.append(f"空校 國中({len(jhE)}):{jhE}")
for name,O in [('國小',gsO),('國中',jhO)]:
    c=tally(O); tot=sum(c.values())
    rep.append(f"{name}: 綠{c['green']}({c['green']*100//tot}%) 黃{c['yellow']}({c['yellow']*100//tot}%) 灰{c['grey']}({c['grey']*100//tot}%)")
open('official_dist.txt','w',encoding='utf-8').write("\n".join(rep))
print("done. gs里",len(gsO),"jh里",len(jhO),"gs空",len(gsE),"jh空",len(jhE))
