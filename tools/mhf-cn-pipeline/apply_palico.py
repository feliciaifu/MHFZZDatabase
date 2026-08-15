# -*- coding: utf-8 -*-
"""猫武器/防具面板中文化：wiki 全部行（92 武器 + 176 防具）直接插入 items/palico 表。

- 名字：有 id 行（十六进制=gao 索引）用 gao 中文名；无 id 行直接用 wiki 名繁→简
- 数值：攻击/会心/属性/锋利度（武器）、防御/耐性（防具）、稀有度
- 描述：gao 日文描述 → description_ja（zh 留空兜底日文）
先清空 palico 表及对应 items 行，再全量重建。
items._id 从 500001 起。
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
sys.path.insert(0, BASE)
sys.path.insert(0, r"D:\repos\FrontierTextHandler")
import align_items as A
from src import common

ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
CN_DB = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")

GAME_DAT = r"D:\Games\PC\MHF\dat"
HEADERS = r"D:\repos\FrontierTextHandler\headers.json"

ITEM_BASE = 500001
ELEMENT_ZH = {"火": "Fire", "水": "Water", "雷": "Thunder", "氷": "Ice", "龍": "Dragon"}


def load_gao_texts(xpath):
    data = common.load_file_data(os.path.join(GAME_DAT, "mhfgao.bin"))
    cfg = common.read_extraction_config(xpath, HEADERS)
    es = common.extract_text_data_from_bytes(data, cfg, "zz")
    return [e["text"] for e in es]


def parse_attack(s):
    """'25 0%' → (25, 0, None, 0)；'70 5%龍 80' → (70, 5, 'Dragon', 80)"""
    m = re.match(r"(\d+)\s*(\d+)%?(?:\s*([火水雷氷龍])\s*(\d+))?", s.strip())
    if not m:
        return 0, 0, None, 0
    return (int(m.group(1)), int(m.group(2)),
            ELEMENT_ZH.get(m.group(3)) if m.group(3) else None,
            int(m.group(4)) if m.group(4) else 0)


def parse_res(s):
    """'火:2水:0雷:0氷:0龍:1' → dict"""
    m = re.search(r"火:(-?\d+)水:(-?\d+)雷:(-?\d+)氷:(-?\d+)龍:(-?\d+)", s.replace(" ", ""))
    if not m:
        return None
    return dict(fire=int(m.group(1)), water=int(m.group(2)), thunder=int(m.group(3)),
                ice=int(m.group(4)), dragon=int(m.group(5)))


def main():
    wiki = json.load(open(os.path.join(CACHE, "neko_wiki.json"), encoding="utf-8"))
    gwn = json.load(open(os.path.join(CACHE, "gao_weapon_names.json"), encoding="utf-8"))
    gah = json.load(open(os.path.join(CACHE, "gao_armor_helm.json"), encoding="utf-8"))
    gam = json.load(open(os.path.join(CACHE, "gao_armor_mail.json"), encoding="utf-8"))
    wdesc = load_gao_texts("gao/weapon_desc")
    adesc = load_gao_texts("gao/armor_desc")

    con = sqlite3.connect(ASSETS_DB)
    cur = con.cursor()

    # 清空重建
    cur.execute("DELETE FROM palico_weapons")
    cur.execute("DELETE FROM palico_armor")
    cur.execute("DELETE FROM items WHERE type IN ('Palico Weapon', 'Palico Armor')")
    nid = ITEM_BASE

    def gao_zh(idx, table):
        if 0 <= idx < len(table) and table[idx] and table[idx] != "無裝備":
            return A.to_simplified(table[idx])
        return None

    n_w = n_a = 0
    # ---- weapons：全部行直接插入 ----
    for sec in wiki["weapon"]:
        for row in sec["rows"]:
            name_wiki = row["name"].strip()
            idx = int(row["id"][1:], 16) if row["id"] else None
            name_zh = gao_zh(idx, gwn) if idx is not None else None
            if not name_zh:
                name_zh = A.to_simplified(name_wiki)
            attack, affinity, elem, elem_val = parse_attack(row["attack"])
            desc = wdesc[idx] if idx is not None and idx < len(wdesc) else ""
            sharp = 5 if (row["sharpness"] or "").endswith("50") else 3
            cur.execute(
                "INSERT INTO items (_id, name, name_ja, name_zh, type, sub_type, rarity, "
                "description, description_ja, description_zh, icon_name, icon_color) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (nid, name_wiki, name_wiki, name_zh, "Palico Weapon", "",
                 int(row["rarity"] or 0), desc, desc, "", "", 0))
            cur.execute(
                "INSERT INTO palico_weapons (_id, creation_cost, attack_melee, attack_ranged, "
                "element, element_melee, element_ranged, defense, sharpness, "
                "affinity_melee, affinity_ranged, blunt, balance) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (nid, 0, attack, attack, elem or "", elem_val, elem_val, 0, sharp,
                 affinity, affinity, 0, 0))
            nid += 1
            n_w += 1

    # ---- armors：全部行直接插入 ----
    for sec in wiki["armor"]:
        is_head = "頭" in sec["section"]
        table = gah if is_head else gam
        for row in sec["rows"]:
            name_wiki = row["name"].strip()
            idx = int(row["id"][1:], 16) if row["id"] else None
            name_zh = gao_zh(idx, table) if idx is not None else None
            if not name_zh:
                name_zh = A.to_simplified(name_wiki)
            res = parse_res(row["res"])
            defense = 0
            if "/" in row["defense"]:
                defense = int(row["defense"].split("/")[0].strip())
            desc = ""
            if idx is not None and idx * 2 + 1 < len(adesc):
                desc = adesc[idx * 2 + (0 if is_head else 1)]
            cur.execute(
                "INSERT INTO items (_id, name, name_ja, name_zh, type, sub_type, rarity, "
                "description, description_ja, description_zh, icon_name, icon_color) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (nid, name_wiki, name_wiki, name_zh, "Palico Armor", "",
                 int(row["rarity"] or 0), desc, desc, "", "", 0))
            cur.execute(
                "INSERT INTO palico_armor (_id, defense, fire_res, thunder_res, dragon_res, "
                "water_res, ice_res, family) VALUES (?,?,?,?,?,?,?,?)",
                (nid, defense,
                 res["fire"] if res else 0, res["thunder"] if res else 0,
                 res["dragon"] if res else 0, res["water"] if res else 0,
                 res["ice"] if res else 0, 0))
            nid += 1
            n_a += 1

    con.commit()
    print("写入: %d 武器, %d 防具; items 至 _id %d" % (n_w, n_a, nid - 1))

    print("\n抽查:")
    for r in cur.execute("SELECT _id, name_zh, type, rarity FROM items "
                         "WHERE _id >= 500000 ORDER BY _id LIMIT 10"):
        print("  ", r)
    print("\n武器数值:")
    for r in cur.execute("SELECT pw._id, i.name_zh, pw.attack_melee, pw.element, "
                         "pw.element_melee, pw.affinity_melee, pw.sharpness "
                         "FROM palico_weapons pw JOIN items i ON i._id = pw._id LIMIT 8"):
        print("  ", r)
    print("\n防具数值:")
    for r in cur.execute("SELECT pa._id, i.name_zh, pa.defense, pa.fire_res, pa.thunder_res, "
                         "pa.dragon_res, pa.water_res, pa.ice_res "
                         "FROM palico_armor pa JOIN items i ON i._id = pa._id LIMIT 8"):
        print("  ", r)
    print("\n总数:", cur.execute("SELECT COUNT(*) FROM palico_weapons").fetchone()[0],
          "武器 /", cur.execute("SELECT COUNT(*) FROM palico_armor").fetchone()[0], "防具")
    con.close()

    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
