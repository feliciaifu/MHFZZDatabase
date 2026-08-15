# -*- coding: utf-8 -*-
"""狩猎笛旋律数据：解析 mhfdat.bin hunting_horn 指南文本 → horn_songs 表。

格式：
  段落标题（《自我強化》/「旋律表（團隊）」）→ 分类
  名称行 → 旋律名；♪ 行 → 音符序列（~Cxx 颜色码 → 音名；「後」分隔多个变体）
"""
import os
import re
import shutil
import sqlite3
import struct
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import align_items as A

DB = r"app/src/main/assets/databases/database.db"
CN = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"

GAME_DAT = r"D:\Games\PC\MHF\dat"
data = open(os.path.join(GAME_DAT, "mhfdat_dec.bin"), "rb").read()

COLOR_NOTE = {
    "00": "W", "02": "R", "03": "O", "04": "Y",
    "05": "G", "07": "P", "20": "B", "01": "A",
}


def read_cstr(off, maxlen=1500):
    end = data.find(b"\x00", off)
    if end < 0 or end - off > maxlen:
        return None
    return data[off:end].decode("shift_jis", errors="replace")


def read_table(ptrs_off, count):
    out = []
    for i in range(count):
        p = struct.unpack_from("<I", data, ptrs_off + i * 4)[0]
        out.append(read_cstr(p))
    return out


def parse_notes(seq_part):
    """'~C07♪~C00→~C02♪~C00→~C02♪~C00' → ('PRR', '07,02,02')；'♪→♪' 用前色"""
    notes = []
    colors = []
    last = "00"
    for cm in re.finditer(r"~C([0-9A-F]{2})♪|♪", seq_part):
        if cm.group(1):
            last = cm.group(1)
        notes.append(COLOR_NOTE.get(last, "?"))
        colors.append(last)
    return "".join(notes), ",".join(colors)


def parse():
    texts = read_table(0x1691010, 4) + read_table(0x1691020, 17)
    entries = []  # (category, name, notes, notes_color)
    category = ""
    pending_name = None
    last_name = None
    for t in texts:
        if not t:
            continue
        for line in t.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 去掉行首颜色码（~C00◇◇ → ◇◇）
            line_nc = re.sub(r"^~C[0-9A-F]{2}", "", line).strip()
            # 分类标题：《xxx》或 ◇ 旋律表（xxx）
            m = re.match(r"《([^》]+)》", line_nc)
            if m:
                category = m.group(1)
                continue
            if "旋律表" in line_nc and line_nc.startswith("◇"):
                m2 = re.search(r"旋律表（([^）]+)）", line_nc)
                category = m2.group(1) if m2 else "旋律表"
                pending_name = None
                continue
            if line_nc.startswith("◇"):
                pending_name = None
                continue
            # ♪ 行
            if "♪" in line:
                parts = line.split("♪")[0]
                nm = re.sub(r"[~C0-9A-F→\s　]+$", "", parts).strip()
                name = None
                if nm and not nm.startswith("~"):
                    name = nm
                if not name:
                    name = pending_name if pending_name else last_name
                for seq in re.split(r"後", line):
                    if "♪" not in seq:
                        continue
                    notes, colors = parse_notes(seq)
                    if name and notes:
                        entries.append((category, name, notes, colors))
                        last_name = name
                pending_name = None
            else:
                # 名称行：与前一行累积合并（跨行名称）
                pending_name = (pending_name or "") + line
    # 去重（category, name, notes）
    seen = set()
    out = []
    for cat, name, notes, colors in entries:
        key = (cat, name, notes)
        if key in seen:
            continue
        seen.add(key)
        out.append((cat, name, notes, colors))
    return out


def main():
    entries = parse()
    print("旋律条目:", len(entries))
    cats = {}
    for cat, name, notes, colors in entries:
        cats.setdefault(cat, []).append((name, notes, colors))
    for cat, lst in cats.items():
        print("\n== %s (%d) ==" % (cat, len(lst)))
        for name, notes, colors in lst[:8]:
            print("  %-22s %s [%s]" % (name, notes, colors))

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS horn_songs")
    cur.execute("CREATE TABLE horn_songs ("
                "_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "category TEXT, category_zh TEXT,"
                "name TEXT, name_zh TEXT, notes TEXT, notes_color TEXT)")
    for cat, name, notes, colors in entries:
        cur.execute("INSERT INTO horn_songs (category, category_zh, name, name_zh, notes, "
                    "notes_color) VALUES (?,?,?,?,?,?)",
                    (cat, A.to_simplified(cat), name, A.to_simplified(name), notes, colors))
    con.commit()
    print("\nhorn_songs:", cur.execute("SELECT COUNT(*) FROM horn_songs").fetchone()[0])
    for r in cur.execute("SELECT category_zh, name_zh, notes FROM horn_songs LIMIT 10"):
        print("  ", r)
    con.close()

    shutil.copy2(DB, CN)
    for z in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN, "database.db")
        print("repacked", z, round(os.path.getsize(z) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
