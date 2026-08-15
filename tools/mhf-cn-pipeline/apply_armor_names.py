# -*- coding: utf-8 -*-
"""防具中文化：items 表 5 字符 hid 行（h/b/a/w/l+4hex）→ 防具名称表（中文）→ name_zh。

对齐规则（已验证）：
  防具名称表索引 = int(item_hid[1:], 16)
  - h → dat/armors/head（14594 条）  b → body（13462）  a → arms（13452）
  - w → waist（13708）               l → legs（13514）
  索引超表长 / 占位 → 跳过（兜底日文）。
App 防具查询已 JOIN items（localizeTableColumn("i","name")），写入后自动生效。
"""
import os
import shutil
import sqlite3
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, r"D:\repos\FrontierTextHandler")
import align_items as A
from src import common

GAME_DAT = r"D:\Games\PC\MHF\dat"
HEADERS = r"D:\repos\FrontierTextHandler\headers.json"
ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
CN_DB = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")

SLOT_TABLES = {"h": "head", "b": "body", "a": "arms", "w": "waist", "l": "legs"}


def load_table(slot):
    data = common.load_file_data(os.path.join(GAME_DAT, "mhfdat.bin"))
    cfg = common.read_extraction_config("dat/armors/" + slot, HEADERS)
    es = common.extract_text_data_from_bytes(data, cfg, "zz")
    return [e["text"] for e in es]


def main():
    tables = {p: load_table(s) for p, s in SLOT_TABLES.items()}
    for p, t in tables.items():
        print("%s %-5s 表: %d 条 | [1]=%s" % (p, SLOT_TABLES[p], len(t), t[1][:12]))

    con = sqlite3.connect(ASSETS_DB)
    rows = con.execute(
        "SELECT _id, item_hid, name_ja FROM items "
        "WHERE length(item_hid)=5 AND substr(item_hid,1,1) IN ('h','b','a','w','l')").fetchall()
    print("防具行:", len(rows))

    if "name_zh" not in [r[1] for r in con.execute("PRAGMA table_info(items)")]:
        con.execute("ALTER TABLE items ADD COLUMN name_zh TEXT")

    by_prefix = {p: 0 for p in SLOT_TABLES}
    n_skip_oob = n_skip_ph = 0
    samples = []
    for iid, hid, name_ja in rows:
        p = hid[0]
        try:
            idx = int(hid[1:], 16)
        except ValueError:
            n_skip_oob += 1
            continue
        t = tables[p]
        if not (0 <= idx < len(t)):
            n_skip_oob += 1
            continue
        zh = t[idx]
        if zh is None or zh in ("------", "") or zh == format(idx, "X") or zh == "無裝備":
            n_skip_ph += 1
            continue
        zh_s = A.to_simplified(zh)
        con.execute("UPDATE items SET name_zh=? WHERE _id=?", (zh_s, iid))
        by_prefix[p] += 1
        if len(samples) < 12:
            samples.append((iid, hid, name_ja, zh_s))

    con.commit()
    print("写入:", dict(by_prefix), "| 超表:", n_skip_oob, "| 占位:", n_skip_ph)

    print("\n抽查:")
    for iid, hid, ja, zh in samples:
        print("  %s %s %-18s -> %s" % (iid, hid, ja, zh))

    print("\n指定验证:")
    for hid in ("h0001", "h000A", "h0032", "b0001", "a0001", "w0001", "l0001"):
        r = con.execute("SELECT _id, item_hid, name_ja, name_zh FROM items WHERE item_hid=?",
                        (hid,)).fetchone()
        print("  ", r)
    con.close()

    # 同步 database_cn.db + 两个 zip
    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
