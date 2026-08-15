# -*- coding: utf-8 -*-
"""防具家族名中文化：armor_families.name_zh（改进版）。

家族名无独立文本表，按以下优先级推导：
  1. 多成员家族 → 成员 items.name_zh 的字符级最长公共前缀 + 家族名日文后缀（逐字转简）
     - 字符级前缀：逐字比较直到不一致（修复半角 [剣] vs 全角 【乌帽子】 的整串前缀失配）
     - zh 前缀尾部剥离 【 、・ （部件后缀起始符）
     - 后缀规范：A.to_simplified + [ガ]→[枪]
  2. 单成员家族 → 成员 name_zh
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


def char_prefix(strs):
    """字符级最长公共前缀（逐字比较，半角/全角括号不匹配即停）。"""
    if not strs:
        return ""
    p = strs[0] or ""
    for s in strs[1:]:
        s = s or ""
        n = 0
        for a, b in zip(p, s):
            if a != b:
                break
            n += 1
        p = p[:n]
        if not p:
            return ""
    return p


def strip_tail_marks(s):
    """剥离 zh 公共前缀尾部的部件后缀起始符（【 、・）。"""
    while s and s[-1] in ("\u3010", "\u30fb", "\uff65"):
        s = s[:-1]
    return s


def strip_brace_tags(s):
    """去掉 {xxx} 标记（{G}/{HC}/{狩護}/{剛種} 等 DB 内部标记）。"""
    import re
    return re.sub(r"\{[^}]*\}", "", s)


def family_variant(fam_ja, ja_cp):
    """家族名变体 = fam_ja 与 ja 前缀字符级共同部分之后的剩余。

    例：忍・陽 vs 忍の → 共同「忍」→ 变体「・陽」
        金色・魁 vs 金色ノ → 共同「金色」→ 变体「・魁」
        ミヅハＧ[剣]{G} vs ミヅハＧ【 → 共同「ミヅハＧ」→ 变体「[剣]{G}」
        バトル[剣] vs バトル → 共同「バトル」→ 变体「[剣]」
    """
    n = 0
    for a, b in zip(fam_ja, ja_cp):
        if a != b:
            break
        n += 1
    return fam_ja[n:]


def normalize_variant(s):
    """变体规范化：繁转简 + 剥武器标志 [剣]/[ガ] + 去 {xxx} + 去分隔・。

    保留版本词：魁、Ｆ、FX、Ｇ、GF、GX、Ｕ、Ｒ、Ｓ、Ｌ、阳、空、天 等。
    """
    s = A.to_simplified(s)
    s = s.replace("[ガ]", "").replace("[剣]", "").replace("[剑]", "").replace("[枪]", "")
    s = strip_brace_tags(s)
    s = s.replace("・", "").replace("．", "")
    return s


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
    n_fixed = 0
    samples = []
    for fid, fam_ja, zh_members, ja_members in fam_rows:
        zhs = [m for m in (zh_members or "").split("|") if m]
        jas = [m for m in (ja_members or "").split("|") if m]
        if not zhs:
            n_skip += 1
            continue
        if len(zhs) >= 2:
            zh_cp = char_prefix(zhs)
            if not zh_cp:
                n_skip += 1
                continue
            zh_cp = strip_tail_marks(zh_cp)
            ja_cp = char_prefix(jas)
            var = family_variant(fam_ja, ja_cp) if fam_ja and ja_cp else ""
            name = zh_cp + normalize_variant(var)
            n_multi += 1
        else:
            name = zhs[0]
            n_single += 1
        name = strip_brace_tags(name)
        cur.execute("UPDATE armor_families SET name_zh=? WHERE _id=?", (name, fid))
        if len(samples) < 14:
            samples.append((fid, fam_ja, name))

    con.commit()
    print("多成员:", n_multi, "| 单成员:", n_single, "| 跳过:", n_skip)

    print("\n抽查:")
    for fid, ja, zh in samples:
        print("  %s %-16s -> %s" % (fid, ja, zh))

    print("\n指定验证:")
    for fid in (333, 334, 336, 337, 463, 507, 513, 630, 635, 979, 1598, 2006, 5981, 6946, 6177, 2193):
        r = cur.execute("SELECT _id, name_ja, name_zh FROM armor_families WHERE _id=?", (fid,)).fetchone()
        print("  ", r)

    # 统计残留残缺
    bad = cur.execute("""
        SELECT COUNT(*) FROM armor_families
        WHERE name_zh IS NULL OR name_zh = ''
           OR name_zh LIKE '%【' OR name_zh LIKE '%之' OR name_zh LIKE '%・'
    """).fetchone()[0]
    print("\n残留残缺 name_zh:", bad)

    con.close()

    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
