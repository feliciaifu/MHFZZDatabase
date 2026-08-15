# -*- coding: utf-8 -*-
"""用 monster_map.py 的语义匹配结果写库（monsters.name_zh）。"""
import sqlite3
import sys

sys.path.insert(0, r"D:\repos\MHFZZDatabase\tools\mhf-cn-pipeline")
import align_items as A
from monster_map import MONSTER_ZH

DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
con = sqlite3.connect(DB)

rows = con.execute("SELECT _id, name, name_ja FROM monsters").fetchall()
print("DB 怪物:", len(rows), "| 映射表:", len(MONSTER_ZH))

if "name_zh" not in [r[1] for r in con.execute("PRAGMA table_info(monsters)")]:
    con.execute("ALTER TABLE monsters ADD COLUMN name_zh TEXT")

n = 0
unmapped = []
for mid, name_en, name_ja in rows:
    zh = MONSTER_ZH.get(name_ja)
    if zh is None:
        unmapped.append((name_en, name_ja))
        continue
    zh_s = A.to_simplified(zh)
    con.execute("UPDATE monsters SET name_zh=? WHERE _id=?", (zh_s, mid))
    n += 1
con.commit()

print("已写入:", n, "| 未映射:", len(unmapped))
for en, ja in unmapped:
    print("  ? %-22s %s" % (en, ja))

print("\n抽查（前 20）:")
for mid, name_en, name_ja in rows[:20]:
    r = con.execute("SELECT name_zh FROM monsters WHERE _id=?", (mid,)).fetchone()
    print("  %-18s %-14s -> %s" % (name_en, name_ja, r[0]))
con.close()
