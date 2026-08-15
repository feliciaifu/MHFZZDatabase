# -*- coding: utf-8 -*-
"""武器中文化：items 表 300xxx 武器行 → 武器名表（中文）→ name_zh。

对齐规则（已验证）：
  melee 名表索引 = _id - 300001        （覆盖 _id 300001..317568，含空洞）
  ranged 名表索引 = _id - 317570       （覆盖 _id 317571..321792）
App 武器查询已 JOIN items（i.$column_name AS name），写入后自动生效。
"""
import os
import sqlite3
import sys

sys.path.insert(0, r"D:\repos\MHFZZDatabase\tools\mhf-cn-pipeline")
sys.path.insert(0, r"D:\repos\FrontierTextHandler")
import align_items as A
from src import common

GAME_DAT = r"D:\Games\PC\MHF\dat"
HEADERS = r"D:\repos\FrontierTextHandler\headers.json"
DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"

MELEE_BASE = 300001
RANGED_BASE = 317570


def load_names(xpath):
    data = common.load_file_data(os.path.join(GAME_DAT, "mhfdat.bin"))
    cfg = common.read_extraction_config(xpath, HEADERS)
    es = common.extract_text_data_from_bytes(data, cfg, "zz")
    return [e["text"] for e in es]


def main():
    melee = load_names("dat/weapons/melee/name")
    ranged = load_names("dat/weapons/ranged/name")
    print("melee 名表:", len(melee), "| ranged 名表:", len(ranged))

    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT _id, name_ja FROM items WHERE _id >= 300000 AND _id < 400000").fetchall()
    print("items 武器行:", len(rows))

    if "name_zh" not in [r[1] for r in con.execute("PRAGMA table_info(items)")]:
        con.execute("ALTER TABLE items ADD COLUMN name_zh TEXT")

    n_melee = n_ranged = n_skip = 0
    samples = []
    for wid, name_ja in rows:
        if wid <= 317568:
            idx = wid - MELEE_BASE
            if 0 <= idx < len(melee):
                zh = melee[idx]
                n_melee += 1
            else:
                n_skip += 1
                continue
        else:
            idx = wid - RANGED_BASE
            if 0 <= idx < len(ranged):
                zh = ranged[idx]
                n_ranged += 1
            else:
                n_skip += 1
                continue
        zh_s = A.to_simplified(zh)
        con.execute("UPDATE items SET name_zh=? WHERE _id=?", (zh_s, wid))
        if len(samples) < 12:
            samples.append((wid, name_ja, zh_s))

    con.commit()
    print("melee:", n_melee, "| ranged:", n_ranged, "| 跳过:", n_skip)

    print("\n抽查:")
    for wid, ja, zh in samples:
        print("  %s %-22s -> %s" % (wid, ja, zh))

    # 指定抽查
    print("\n指定验证:")
    for wid in (300002, 300006, 300011, 300013, 305568, 317565, 317568, 317571, 317574, 321792):
        r = con.execute("SELECT _id, name_ja, name_zh FROM items WHERE _id=?", (wid,)).fetchone()
        print("  ", r)
    con.close()


if __name__ == "__main__":
    main()
