# -*- coding: utf-8 -*-
# 鄰級 (區,里,鄰)->學校。綠=基本學區單一校且該鄰不在共同學區;黃=共同/多校/回退;灰=無
import json, re
from collections import defaultdict

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
DIST_RE = re.compile('(?:' + '|'.join(sorted(DISTRICTS, key=len, reverse=True)) + ')')
VARIANT = {'塩':'鹽','晋':'晉','峯':'峰','脚':'腳','曺':'曹','裡':'里'}
ALIAS = {'仁里':'仁里里','科里':'科里里','豐里':'豐里里'}
FW = str.maketrans('０１２３４５６７８９','0123456789')
SUFFIX = '國民小學|國民中學|國中小|國小|國中|實小|附小|高中|完全中學|中學'
SCHOOL_CORE_RE = re.compile(r'([一-鿿]{2,6}(?:'+SUFFIX+'))')
ENTRY_RE = re.compile(r'([一-鿿]{1,4}里)([0-9０-９、,\-–~至鄰\s]*)((?:[（(][^）)]*[）)])*)')
BADLI = ('以上','共同','學區','本市','招收','設籍','實驗','公所','餘')

REF = json.load(open('ref.json', encoding='utf-8'))
DIST_LI_CORE = defaultdict(set)   # 區 -> set of 里core(去里)
for key in REF['kin']:
    d, li = key.split('|', 1)
    DIST_LI_CORE[d].add(li[:-1] if li.endswith('里') else li)

def canon_li(v):
    v = v.replace('[','').replace(']','').strip()
    v = ''.join(VARIANT.get(c,c) for c in v)
    if not v.endswith('里'): v += '里'
    return ALIAS.get(v, v)

def parse_kin(text):
    text = text.translate(FW).replace('鄰','')
    ks = set()
    for part in re.split(r'[、,，]', text):
        part = part.strip()
        m = re.match(r'^(\d+)\s*[-–~至]\s*(\d+)$', part)
        if m: ks.update(range(int(m.group(1)), int(m.group(2))+1)); continue
        m = re.match(r'^(\d+)$', part)
        if m: ks.add(int(m.group(1)))
    return ks

def schools_in(note):
    note = DIST_RE.sub('', note)
    res = []
    for part in re.split(r'[與、,，；;)(（）]', note):
        m = SCHOOL_CORE_RE.search(part)
        if m: res.append(m.group(1))
    return res

def seg_split(core, valid):     # 黏字 DP 切成合法里core
    n=len(core); dp=[None]*(n+1); dp[0]=[]
    for i in range(1,n+1):
        for l in (2,3):
            if i-l>=0 and dp[i-l] is not None and core[i-l:i] in valid:
                dp[i]=dp[i-l]+[core[i-l:i]]; break
    return dp[n]

def parse_gs(body):
    out=[]
    for m in ENTRY_RE.finditer(body):
        li=m.group(1); kintext=m.group(2); note=m.group(3)
        if any(b in li for b in BADLI): continue
        li=canon_li(li)
        kins=parse_kin(kintext)
        out.append((li, kins, len(kins)==0, schools_in(note)))
    return out

def parse_jh(body, dist):
    out=[]
    valid=DIST_LI_CORE.get(dist,set())
    for tok in re.split(r'[，,]', body):
        tok=tok.strip()
        if not tok: continue
        parens=re.findall(r'[（(]([^）)]*)[）)]', tok)
        note=' '.join(parens)
        outside=re.sub(r'[（(][^）)]*[）)]','',tok)
        core=re.sub(r'[0-9０-９、,\-–~至鄰\s]','',outside).strip()
        if not core or any(b in core for b in BADLI): continue
        kins=parse_kin(outside)
        if not kins and note:
            kins=parse_kin(re.split(r'與', note)[0])
        pnames=schools_in(note)
        cores=[core]
        if core not in valid and len(core)>3:
            seg=seg_split(core, valid)
            if seg: cores=seg
        for c in cores:
            out.append((canon_li(c), set(kins), len(kins)==0, pnames))
    return out

def parse_cell(cell, level):
    txt=(cell or '').replace('\n','').replace(' ','').replace('　','')
    txt=txt.replace('東西庄','東庄，西庄')
    ms=list(MARK_RE.finditer(txt)); res=[]
    for i,m in enumerate(ms):
        dist=MARKERS[m.group(1)]
        s=m.end(); e=ms[i+1].start() if i+1<len(ms) else len(txt)
        body=txt[s:e]
        entries = parse_gs(body) if level=='gs' else parse_jh(body, dist)
        for t in entries: res.append((dist,)+t)
    return res

def load(rows_fn, level):
    rows=json.load(open(rows_fn,encoding='utf-8')); schools=[]; home=None
    for r in rows:
        no,dc,nc,basic,common=(r+[None]*5)[:5]
        d=(dc or '').replace('\n','').replace(' ','').strip()
        n=(nc or '').replace('\n','').replace(' ','').strip()
        if d: home=d
        if not n or n in ('學校名稱','學校'):
            if schools and (basic or common):
                schools[-1]['basic']+=parse_cell(basic,level); schools[-1]['common']+=parse_cell(common,level)
            continue
        sn=re.sub(r'[（(][^）)]*[）)]\s*$','',n).strip()   # 去尾註(代用國中)/(國小部),保留完整校名
        schools.append({'home':home or '','school':sn,'basic':parse_cell(basic,level),'common':parse_cell(common,level)})
    return schools

def build(rows_fn, level):
    schools=load(rows_fn, level)
    T=defaultdict(lambda:{'bd':set(),'bk':defaultdict(set),'cd':set(),'ck':defaultdict(set),'hc':False})
    for s in schools:
        sn=s['school']
        for (dist,li,kins,whole,pn) in s['basic']:
            rec=T[f'{dist}|{li}']
            if whole: rec['bd'].add(sn)
            else:
                for k in kins: rec['bk'][k].add(sn)
        for (dist,li,kins,whole,pn) in s['common']:
            rec=T[f'{dist}|{li}']; rec['hc']=True
            claim={sn}|set(pn)
            if whole: rec['cd']|=claim
            else:
                for k in kins: rec['ck'][k]|=claim
    out={}
    for key,rec in T.items():
        out[key]={'bd':sorted(rec['bd']),'bk':{str(k):sorted(v) for k,v in rec['bk'].items()},
                  'cd':sorted(rec['cd']),'ck':{str(k):sorted(v) for k,v in rec['ck'].items()},'hc':rec['hc']}
    return out

def lookup(T, dist, li, kin):
    rec=T.get(f'{dist}|{li}')
    if not rec: return ('grey', [])
    k=str(kin)
    basicK=set(rec['bk'].get(k,[]))
    commonK=set(rec['ck'].get(k,[]))
    if basicK or commonK:
        if len(basicK)==1 and not commonK: return ('green', sorted(basicK))
        return ('yellow', sorted(basicK|commonK))
    # default (whole-里)
    if rec['bd']:
        if len(rec['bd'])==1 and not rec['hc']: return ('green', sorted(rec['bd']))
        return ('yellow', sorted(set(rec['bd'])|set(rec['cd'])))
    if rec['cd']: return ('yellow', sorted(rec['cd']))
    return ('grey', [])

if __name__=='__main__':
    for lvl,fn,out in [('gs','GS_rows.json','gs_nlin.json'),('jh','JH_rows.json','jh_nlin.json')]:
        json.dump(build(fn,lvl),open(out,'w',encoding='utf-8'),ensure_ascii=False)
    gs=json.load(open('gs_nlin.json',encoding='utf-8')); jh=json.load(open('jh_nlin.json',encoding='utf-8'))
    tests=[('國小',gs,'東區','東門里',1),('國小',gs,'東區','東門里',6),('國小',gs,'東區','東門里',7),
           ('國小',gs,'東區','裕農里',5),('國小',gs,'東區','泉南里',1),('國小',gs,'東區','大同里',11),
           ('國小',gs,'東區','大學里',3),('國小',gs,'東區','崇誨里',1),
           ('國中',jh,'東區','大同里',3),('國中',jh,'東區','大同里',6),('國中',jh,'東區','大福里',1),
           ('國中',jh,'南區','溪南里',1)]
    rep=[f"gs 里數 {len(gs)} | jh 里數 {len(jh)}",""]
    for lv,T,d,li,k in tests:
        st,sch=lookup(T,d,li,k); rep.append(f"[{lv}] {d}{li} {k}鄰 -> {st} {sch}")
    open('nlin_test.txt','w',encoding='utf-8').write("\n".join(rep))
    print("done gs",len(gs),"jh",len(jh))
