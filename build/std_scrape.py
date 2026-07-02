# -*- coding: utf-8 -*-
# 從台南市教育局官方查詢系統抓每校的(行政區,里,鄰)->建權威鄰級對照
import requests, re, json, time, sys

URL = 'https://std.tn.edu.tw/sis/anonyquery/SchoolDistrict.aspx'
SCH = 'ctl00$ContentPlaceHolder1$list_sch'
STAGE = 'ctl00$ContentPlaceHolder1$ddl_stage'

def hidden(html): return dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html))
def options(html): return re.findall(r'<option\s+value="(\d+)">([^<]+)</option>', html)
def stage_vals(html):
    return re.findall(r'name="'+re.escape(STAGE)+r'"[^>]*value="([^"]+)"', html)

def parse_result(html):
    recs=[]
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S):
        cells=[re.sub(r'<[^>]+>','',c).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
        # 流水號,學校,行政區,學區里,學區鄰
        if len(cells)>=5 and cells[0].isdigit():
            recs.append((cells[2], cells[3], cells[4]))  # (行政區,里,鄰)
    return recs

def scrape_stage(S, base_fields, opts, stage_val, tag):
    data_out=[]
    for i,(val,name) in enumerate(opts):
        d=dict(base_fields)
        d['__EVENTTARGET']=SCH; d['__EVENTARGUMENT']=''
        d[SCH]=val; d[STAGE]=stage_val
        for attempt in range(3):
            try:
                r=S.post(URL,data=d,timeout=30); recs=parse_result(r.text)
                if recs: break
            except Exception as e:
                recs=[]
            time.sleep(0.4)
        data_out.append({'school':name.strip(),'val':val,'recs':recs})
        if (i+1)%40==0: print(f"  {tag} {i+1}/{len(opts)}", flush=True)
        time.sleep(0.12)
    return data_out

def main():
    S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0'})
    html=S.get(URL,timeout=30).text
    base=hidden(html); gs_opts=options(html); svals=stage_vals(html)
    print("國小 options:",len(gs_opts),"stage vals:",svals, flush=True)
    gs_stage = svals[0] if svals else ''
    jh_stage = svals[1] if len(svals)>1 else ''
    gs=scrape_stage(S,base,gs_opts,gs_stage,'GS')
    # switch to 國中
    d=dict(base); d['__EVENTTARGET']=STAGE; d['__EVENTARGUMENT']=''; d[STAGE]=jh_stage
    r=S.post(URL,data=d,timeout=30); h2=r.text
    base2=hidden(h2); jh_opts=options(h2)
    print("國中 options:",len(jh_opts), flush=True)
    jh=scrape_stage(S,base2,jh_opts,jh_stage,'JH')
    json.dump({'gs':gs,'jh':jh},open('official_raw.json','w',encoding='utf-8'),ensure_ascii=False)
    print("scraped gs",len(gs),"jh",len(jh),
          "| gs empty:",sum(1 for x in gs if not x['recs']),
          "| jh empty:",sum(1 for x in jh if not x['recs']), flush=True)

if __name__=='__main__': main()
