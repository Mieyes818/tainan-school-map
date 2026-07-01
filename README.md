# 台南國中小學區地圖

互動式台南市（37 區）國民小學／國民中學學區地圖，作為房仲行銷／導覽工具。
**陪你買好房 × 齊家不動產**。

> ⚠️ **學區僅供參考，一律以官方查詢為準。** 本圖以「里」為單位上色；官方學區部分切至「鄰／門牌」，交界處請務必至[台南市教育局學區查詢系統](https://std.tn.edu.tw/sis/anonyquery/SchoolDistrict.aspx)確認。

## 資料來源

- **學區**：115 學年度台南市國民中學／國民小學學區一覽表（台南市教育局公告）
- **村里界**：內政部村里界圖 2026/04（[kiang/taiwan_basecode](https://github.com/kiang/taiwan_basecode)）
- **底圖**：CARTO Voyager / OpenStreetMap

## 精度

里級底圖。覆蓋率：國小 650/650（100%）、國中 646/650（99%）。鄰級切分與共同學區為近似歸主校，交界以官方為準。

## 產生方式

`build/build_geo.py`：解析學區一覽表 PDF（表格抽取）→ 里名正規化＋黏字切分＋共同學區回收 → 對內政部村里界 join → 依校 dissolve → 輸出 `gs.geojson`（國小）/`jh.geojson`（國中）。QA 報表在 `qa/`。

## 技術

單一 `index.html` + Leaflet（Canvas 渲染）。無 build step。GitHub Pages 部署。
