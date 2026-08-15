# -*- coding: utf-8 -*-
"""武器描述中文化：items 表 300xxx 武器行 → 武器描述表（中文）→ description_zh。

对齐规则（与 weapon_names.py 相同，已验证）：
  melee 描述表索引  = _id - 300001        （描述表 16805 条，覆盖 _id 300001..317805）
  ranged 描述表索引 = _id - 317570        （描述表 4223 条，覆盖 _id 317570..321792）
超出描述表长度 → 跳过（保留原有兜底：description_ja → description）

文本处理：
  - {j}  → 换行（游戏文本换行标记，与物品描述中的 \\n 一致）
  - ‾Cxx 颜色码保留（与现有 description_zh 物品管线一致；App 端原样显示）
  - 繁 → 简（逐字，同 align_items.to_simplified）
"""
import os
import shutil
import sqlite3
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"D:\repos\FrontierTextHandler")
import align_items as A
from src import common

GAME_DAT = r"D:\Games\PC\MHF\dat"
HEADERS = r"D:\repos\FrontierTextHandler\headers.json"
ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
CN_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database_cn.db")
CN_ZIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database_cn.db.zip")

MELEE_BASE = 300001
RANGED_BASE = 317570


def load_texts(xpath):
    data = common.load_file_data(os.path.join(GAME_DAT, "mhfdat.bin"))
    cfg = common.read_extraction_config(xpath, HEADERS)
    es = common.extract_text_data_from_bytes(data, cfg, "zz")
    return [e["text"] for e in es]


def clean(text):
    """{j} → \\n，其余（含 ‾Cxx 颜色码）保留。"""
    if not text:
        return text
    return text.replace("{j}", "\n")


def main():
    melee = load_texts("dat/weapons/melee/description")
    ranged = load_texts("dat/weapons/ranged/description")
    print("melee 描述表:", len(melee), "| ranged 描述表:", len(ranged))

    con = sqlite3.connect(ASSETS_DB)
    rows = con.execute(
        "SELECT _id, name_ja FROM items WHERE _id >= 300000 AND _id < 400000").fetchall()
    print("items 武器行:", len(rows))

    if "description_zh" not in [r[1] for r in con.execute("PRAGMA table_info(items)")]:
        con.execute("ALTER TABLE items ADD COLUMN description_zh TEXT")

    n_melee = n_ranged = n_skip = n_placeholder = 0
    samples = []
    for wid, name_ja in rows:
        if wid <= 317568:
            idx = wid - MELEE_BASE
            table = melee
        else:
            idx = wid - RANGED_BASE
            table = ranged
        if not (0 <= idx < len(table)):
            n_skip += 1
            continue
        zh = table[idx]
        if zh is None or zh in ("------", "") or zh == format(idx, "X"):
            n_placeholder += 1
            continue
        zh_s = A.to_simplified(clean(zh))
        con.execute("UPDATE items SET description_zh=? WHERE _id=?", (zh_s, wid))
        if wid <= 317568:
            n_melee += 1
        else:
            n_ranged += 1
        if len(samples) < 10:
            samples.append((wid, name_ja, zh_s))

    con.commit()
    print("melee:", n_melee, "| ranged:", n_ranged, "| 跳过(超表):", n_skip,
          "| 占位:", n_placeholder)

    print("\n抽查:")
    for wid, ja, zh in samples:
        print("  %s %-20s -> %s" % (wid, ja, zh.replace("\n", " / ")[:50]))

    # 指定验证
    print("\n指定验证:")
    for wid in (300002, 300003, 300006, 300009, 317565, 317571, 317572, 317574, 321792):
        r = con.execute("SELECT _id, substr(description_zh,1,40), substr(description_ja,1,30) "
                        "FROM items WHERE _id=?", (wid,)).fetchone()
        print("  ", r)
    con.close()

    # 同步：database_cn.db + 两个 zip（zip 内文件名 database.db）
    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
