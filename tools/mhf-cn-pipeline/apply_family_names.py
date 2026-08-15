# -*- coding: utf-8 -*-
"""防具家族名中文化：armor_families.name_zh。

家族名无独立文本表，按以下优先级推导（已验证统计）：
  1. 多成员家族 → 成员 items.name_zh 的最长公共前缀 + 家族名日文后缀（逐字转简）
     （例：アカムト[剣] 成员 霸龙削头/霸龙破坏者… → 公共前缀「霸龙」+ 后缀「[剣]→[剑]」= 霸龙[剑]）
  2. 单成员家族 → 成员 name_zh（例：ガルルガフェイク → 鄢狼鸟伪装）
  3. 无成员 / 前缀为空 → 跳过（兜底日文）
"""
import os
import shutil
import sqlite3
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import align_items as A

ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
CN_DB = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")


def common_prefix(strs):
    if not strs:
        return ""
    p = strs[0] or ""
    for s in strs[1:]:
        s = s or ""
        while not s.startswith(p):
            p = p[:-1]
            if not p:
                return ""
    return p


def main():
    con = sqlite3.connect(ASSETS_DB)
    cur = con.cursor()

    if "name_zh" not in [r[1] for r in cur.execute("PRAGMA table_info(armor_families)")]:
        cur.execute("ALTER TABLE armor_families ADD COLUMN name_zh TEXT")

    fam_rows = cur.execute("""
        SELECT af._id, af.name_ja,
            (SELECT group_concat(i.name_zh, '|') FROM armor a JOIN items i ON i._id = a._id
             WHERE a.family = af._id AND i.name_zh IS NOT NULL AND i.name_zh != ''),
            (SELECT group_concat(i.name_ja, '|') FROM armor a JOIN items i ON i._id = a._id
             WHERE a.family = af._id AND i.name_ja IS NOT NULL AND i.name_ja != '')
        FROM armor_families af
    """).fetchall()

    n_multi = n_single = n_skip = 0
    samples = []
    for fid, fam_ja, zh_members, ja_members in fam_rows:
        zhs = [m for m in (zh_members or "").split("|") if m]
        jas = [m for m in (ja_members or "").split("|") if m]
        if not zhs:
            n_skip += 1
            continue
        if len(zhs) >= 2:
            zh_cp = common_prefix(zhs)
            if not zh_cp:
                n_skip += 1
                continue
            ja_cp = common_prefix(jas)
            suffix = ""
            if fam_ja and ja_cp and fam_ja.startswith(ja_cp):
                suffix = fam_ja[len(ja_cp):]
            name = zh_cp + A.to_simplified(suffix)
            n_multi += 1
        else:
            name = zhs[0]
            n_single += 1
        cur.execute("UPDATE armor_families SET name_zh=? WHERE _id=?", (name, fid))
        if len(samples) < 14:
            samples.append((fid, fam_ja, name))

    con.commit()
    print("多成员:", n_multi, "| 单成员:", n_single, "| 跳过:", n_skip)

    print("\n抽查:")
    for fid, ja, zh in samples:
        print("  %s %-16s -> %s" % (fid, ja, zh))

    print("\n指定验证:")
    for fid in (1, 2, 3, 28, 85, 487, 525, 528):
        r = cur.execute("SELECT _id, name_ja, name_zh FROM armor_families WHERE _id=?", (fid,)).fetchone()
        print("  ", r)
    con.close()

    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
