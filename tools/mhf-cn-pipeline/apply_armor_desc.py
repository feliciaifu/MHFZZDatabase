# -*- coding: utf-8 -*-
"""防具描述中文化：items 表 5 字符 hid 行 → equipment/description 表（中文）→ description_zh。

对齐规则（已验证）：
  equipment.description 共 68730 条 = 五段防具描述拼接：
    h(head) 偏移 0       b(body) 偏移 14594   a(arms) 偏移 28056
    w(waist) 偏移 41508  l(legs) 偏移 55216
  描述索引 = 段偏移 + int(item_hid[1:], 16)

文本处理：{j}→换行（与武器描述一致）；‾Cxx 颜色码保留；繁→简（逐字）。
另：把已写入的 name_zh/description_zh 中异体字 䖝 → 绿。
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

# 段偏移（依据各名称表长度：14594/13462/13452/13708/13514）
SLOT_OFFSETS = {"h": 0, "b": 14594, "a": 28056, "w": 41508, "l": 55216}
SLOT_LENS = {"h": 14594, "b": 13462, "a": 13452, "w": 13708, "l": 13514}


def main():
    data = common.load_file_data(os.path.join(GAME_DAT, "mhfdat.bin"))
    cfg = common.read_extraction_config("dat/equipment/description", HEADERS)
    es = common.extract_text_data_from_bytes(data, cfg, "zz")
    texts = [e["text"] for e in es]
    print("equipment.description:", len(texts))

    con = sqlite3.connect(ASSETS_DB)
    rows = con.execute(
        "SELECT _id, item_hid, name_ja FROM items "
        "WHERE length(item_hid)=5 AND substr(item_hid,1,1) IN ('h','b','a','w','l')").fetchall()

    if "description_zh" not in [r[1] for r in con.execute("PRAGMA table_info(items)")]:
        con.execute("ALTER TABLE items ADD COLUMN description_zh TEXT")

    n_write = n_oob = n_ph = 0
    samples = []
    for iid, hid, name_ja in rows:
        p = hid[0]
        try:
            idx = int(hid[1:], 16)
        except ValueError:
            n_oob += 1
            continue
        if not (0 <= idx < SLOT_LENS[p]):
            n_oob += 1
            continue
        off = SLOT_OFFSETS[p] + idx
        zh = texts[off]
        if zh is None or zh in ("------", "") or zh == format(idx, "X") or zh == "什麼都沒有裝備。":
            n_ph += 1
            continue
        zh_s = A.to_simplified(zh.replace("{j}", "\n"))
        con.execute("UPDATE items SET description_zh=? WHERE _id=?", (zh_s, iid))
        n_write += 1
        if len(samples) < 10:
            samples.append((iid, hid, zh_s.replace("\n", " / ")[:44]))

    # 异体字 䖝 → 绿（覆盖此前写入的 name_zh/description_zh）
    n_lv = con.execute("UPDATE items SET name_zh = REPLACE(name_zh, '䖝', '绿') "
                       "WHERE name_zh LIKE '%䖝%'").rowcount
    n_ld = con.execute("UPDATE items SET description_zh = REPLACE(description_zh, '䖝', '绿') "
                       "WHERE description_zh LIKE '%䖝%'").rowcount

    con.commit()
    print("写入描述:", n_write, "| 超表:", n_oob, "| 占位:", n_ph)
    print("䖝→绿: name_zh %d 行, description_zh %d 行" % (n_lv, n_ld))

    print("\n抽查:")
    for iid, hid, zh in samples:
        print("  %s %s %s" % (iid, hid, zh))

    print("\n指定验证:")
    for hid in ("h0001", "h0002", "b0001", "a0001", "w0001", "l0001", "h0032"):
        r = con.execute("SELECT item_hid, substr(description_zh,1,40) FROM items WHERE item_hid=?",
                        (hid,)).fetchone()
        print("  ", r)
    con.close()

    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
