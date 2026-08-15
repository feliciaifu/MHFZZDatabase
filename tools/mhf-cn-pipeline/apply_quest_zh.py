# -*- coding: utf-8 -*-
"""任务面板中文化：quests 表 _zh 列 ← mhfinf.bin 任务文本（中文）。

对齐：QUEST_INFO_TBL + 0x2E 处 u16 = quest_id（已验证：idx124-128 → 5001-5005）。
字段（{j} 分隔 8 段）：
  f1 = header\\nname（第一行 ≪…≫ 去括号 → header，其余 → name）
  f2 = goal   f3 = sub_goal_a   f4 = sub_goal_b
  f5/f6 = 达成/失败条件（DB 无对应列，丢弃）
  f7 = hirer  f8 = flavor
只更新 quest_id 匹配到的行；未匹配的跳过（兜底日文）。
"""
import io
import os
import shutil
import sqlite3
import struct
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, r"D:\repos\FrontierTextHandler")
import align_items as A
from src import common
from src.binary_file import BinaryFile
from src.pointer_tables import _read_indirect_count

GAME_DAT = r"D:\Games\PC\MHF\dat"
HEADERS = r"D:\repos\FrontierTextHandler\headers.json"
ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
CN_DB = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")

QUEST_ID_OFFSET = 0x2E
JOIN = "{j}"


def extract_quests():
    data = common.load_file_data(os.path.join(GAME_DAT, "mhfinf.bin"))
    bfile = BinaryFile(_file=io.BytesIO(data), _size=len(data))
    cfg = common.read_extraction_config("inf/quests", HEADERS)
    num_categories = _read_indirect_count(bfile, cfg)
    bfile.seek(int(cfg["begin_pointer"], 16))
    category_table_ptr = bfile.read_int()
    quest_text_offset = int(cfg.get("quest_text_offset", "0x28"), 16)
    text_pointers_count = int(cfg.get("text_pointers_count", 8))

    quests = {}  # quest_id -> [fields]
    for cat_idx in range(num_categories):
        cat_addr = category_table_ptr + cat_idx * 8
        bfile.validate_offset(cat_addr + 7, context="category %d" % cat_idx)
        bfile.seek(cat_addr + 2)
        count = struct.unpack_from("<H", bfile.read(2))[0]
        quest_array_ptr = bfile.read_int()
        if quest_array_ptr == 0 or count == 0:
            continue
        bfile.validate_offset(quest_array_ptr + count * 4 - 1, context="cat %d array" % cat_idx)
        bfile.seek(quest_array_ptr)
        quest_ptrs = struct.unpack("<%dI" % count, bfile.read(count * 4))
        for qp in quest_ptrs:
            if qp == 0:
                continue
            bfile.validate_offset(qp + quest_text_offset + 3, context="text field")
            bfile.seek(qp + quest_text_offset)
            tbp = bfile.read_int()
            if tbp == 0:
                continue
            # quest id
            bfile.seek(qp + QUEST_ID_OFFSET)
            qid = struct.unpack("<H", bfile.read(2))[0]
            # text block
            bfile.seek(tbp)
            str_ptrs = struct.unpack("<%dI" % text_pointers_count,
                                     bfile.read(text_pointers_count * 4))
            fields = []
            for sp in str_ptrs:
                if sp == 0:
                    fields.append("")
                    continue
                bfile.seek(sp)
                raw = b""
                while True:
                    ch = bfile.read(1)
                    if ch == b"\x00" or not ch:
                        break
                    raw += ch
                fields.append(common.decode_game_string(raw))
            if any(fields):
                quests[qid] = fields
    return quests


def split_header_name(f1):
    """f1 = '≪header≫\\nname' → (header, name)；无 \\n 时整个作为 name。"""
    if "\n" in f1:
        first, rest = f1.split("\n", 1)
        header = first.strip("≪≫ \t")
        return header, rest
    return "", f1


def main():
    quests = extract_quests()
    print("mhfinf 提取 quest 数:", len(quests))

    con = sqlite3.connect(ASSETS_DB)
    cur = con.cursor()
    rows = cur.execute("SELECT _id, quest_id, name_ja FROM quests").fetchall()

    n_hit = n_miss = 0
    samples = []
    for iid, qid, name_ja in rows:
        if qid not in quests:
            n_miss += 1
            continue
        f = quests[qid]
        header, name = split_header_name(f[0] if len(f) > 0 else "")
        goal = f[1] if len(f) > 1 else ""
        sub_a = f[2] if len(f) > 2 else ""
        sub_b = f[3] if len(f) > 3 else ""
        hirer = f[6] if len(f) > 6 else ""
        flavor = f[7] if len(f) > 7 else ""
        cur.execute(
            "UPDATE quests SET header_zh=?, name_zh=?, goal_zh=?, sub_goal_a_zh=?, "
            "sub_goal_b_zh=?, hirer_zh=?, flavor_zh=? WHERE _id=?",
            (A.to_simplified(header),
             A.to_simplified(name),
             A.to_simplified(goal),
             A.to_simplified(sub_a),
             A.to_simplified(sub_b),
             A.to_simplified(hirer),
             A.to_simplified(flavor),
             iid))
        n_hit += 1
        if len(samples) < 10:
            samples.append((iid, qid, name_ja, header, name))

    con.commit()
    print("命中:", n_hit, "| 未匹配(跳过):", n_miss)

    print("\n抽查:")
    for iid, qid, ja, header, name in samples:
        print("  %s q%s %-18s | %s | %s" % (iid, qid, ja[:18], header, name))

    print("\n指定验证 (goal/hirer/flavor):")
    for qid in (1, 2, 5001, 5004, 5005):
        r = cur.execute("SELECT quest_id, name_zh, substr(goal_zh,1,20), hirer_zh "
                        "FROM quests WHERE quest_id=?", (qid,)).fetchone()
        print("  ", r)
    con.close()

    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
