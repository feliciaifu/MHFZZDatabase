# -*- coding: utf-8 -*-
"""猫武器/防具汉化优化：无 id 行改用 gao 全中文名（游戏汉化文本）。

匹配：假名词典 + 汉字子串/LCS → gao 索引；色名按索引精确匹配；
未匹配/误匹配 → 手动映射（语义翻译）。
"""
import json
import os
import shutil
import sqlite3
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
sys.path.insert(0, BASE)
import align_items as A

DB = r"app/src/main/assets/databases/database.db"
CN = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"

KATA = {
    "ソード": "剑", "ピック": "尖刃刀", "ハンマー": "锤", "レイピア": "细剑",
    "ブレイド": "之刃", "カッター": "切", "ボード": "板", "チクリ": "刺",
    "フォーク": "叉", "ワンド": "之杖", "スピア": "枪", "トンファー": "棍",
    "フライパン": "锅", "ククリ": "弯刀", "ニードル": "针", "グレイブ": "锄",
    "ダオラ": "钢龙", "トルム": "响狼", "どんぐり": "橡实", "ばくだん": "炸弹",
    "つっぱり": "撑", "アカタマ": "红蝌蚪", "タマ": "玉", "ツリ": "钓",
    "カロテ": "胡萝匐", "ペリ": "佩利", "ブロンズ": "青铜", "テンロウ": "天廊",
    "ロロ": "罗罗", "レイ": "冥雷", "荒くれ": "粗暴", "巨大": "巨大",
    "跳緋獸": "跳绯兽", "爆狼": "爆狼", "青たる": "青樽", "マキワリ": "斩木",
    "チャーム": "魅力", "靈魂": "魂邃", "太陽": "银日", "翡翠": "翡翠",
    "棘龍": "棘龙", "友誼": "友谊", "王國": "王国", "凍海獸": "冻海兽",
    "貓の花団子": "猫之花团子", "マカ": "燕雀",
}

# 色名 → gao 索引（已验证）
COLOR_IDX = {
    "貓の花団子・赤": 44, "貓の花団子・青": 45, "貓の花団子・黒": 46, "貓の花団子・白": 47,
    "蛙猫頭飾‧綠": 75, "蛙猫頭飾‧桃": 76,
    "蛙猫服裝‧綠": 75, "蛙猫服裝‧桃": 76,
    "麥草猫帽子‧青": 77, "麥草猫帽子‧赤": 78, "麥草猫帽子‧黃": 79,
    "ツリ貓ハンマー・青": 77, "ツリ貓ハンマー・赤": 78, "ツリ貓ハンマー・黄": 79,
}

# 手动映射（wiki 名 → gao 索引；gao 无对应 → 直接中文）
MANUAL = {
    "ロロ貓フォーク": None,      # 保持语义直译
    "ペリ貓ソード": None,
    "巨大貓どんぐり": None,
    "爆狼タマ貓ハンマー": None,
    "青たる貓ばくだん": None,
    "レイ貓フォーク": None,      # 误匹配 冥雷猫錘
    "つっぱり貓ハンマー": None,  # 误匹配 骨猫錘
    "荒くれ貓ハンマー": None,    # 误匹配 闇暴猫錘
}
MANUAL_ZH = {
    "ロロ貓フォーク": "罗罗猫叉",
    "ペリ貓ソード": "佩利猫剑",
    "巨大貓どんぐり": "巨大橡实",
    "爆狼タマ貓ハンマー": "爆狼玉猫锤",
    "青たる貓ばくだん": "青樽猫炸弹",
    "レイ貓フォーク": "冥雷猫叉",
    "つっぱり貓ハンマー": "撑猫锤",
    "荒くれ貓ハンマー": "粗暴猫锤",
}


def to_hz(s):
    t = s
    for k, v in KATA.items():
        t = t.replace(k, v)
    return A.to_simplified("".join(c for c in t if "\u4e00" <= c <= "\u9fff"))


def lcs(a, b):
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[n][m]


def match_gao(name, table):
    hz = to_hz(name)
    if len(hz) < 2:
        return None
    best = None
    for i, g in enumerate(table):
        ghz = to_hz(g)
        if not ghz:
            continue
        if hz in ghz or ghz in hz:
            score = len(hz) + 100
        else:
            l = lcs(hz, ghz)
            if l < max(2, len(hz) - 1):
                continue
            score = l * 2 - abs(len(ghz) - len(hz))
        if best is None or score > best[0]:
            best = (score, i, g)
    return best[1] if best else None


def resolve(name, table):
    """wiki 名 → (gao 中文名 or None, 手动中文 or None)"""
    if name in COLOR_IDX:
        return A.to_simplified(table[COLOR_IDX[name]]), None
    if name in MANUAL:
        return None, MANUAL_ZH[name]
    idx = match_gao(name, table)
    if idx is not None:
        return A.to_simplified(table[idx]), None
    return None, None


def main():
    wiki = json.load(open(os.path.join(CACHE, "neko_wiki.json"), encoding="utf-8"))
    gao = json.load(open(os.path.join(CACHE, "gao_all.json"), encoding="utf-8"))
    gwn, gah, gam = gao["gwn"], gao["gah"], gao["gam"]

    con = sqlite3.connect(DB)
    cur = con.cursor()
    # items._id 映射到 wiki 行：按顺序（有 id 行用 id，无 id 行顺序）—— 直接用 wiki 行顺序对应 items 插入顺序
    rows = cur.execute("SELECT _id, name, name_zh FROM items WHERE _id >= 500000 "
                       "AND _id < 500269 ORDER BY _id").fetchall()
    print("items 猫装备:", len(rows))
    n_gao = n_manual = n_keep = 0
    r = 0
    for sec in wiki["weapon"]:
        for row in sec["rows"]:
            if r >= len(rows):
                break
            iid, name, name_zh = rows[r]
            r += 1
            if row["id"]:
                continue  # 有 id 行已用 gao 名
            gzh, mzh = resolve(row["name"], gwn)
            if gzh:
                cur.execute("UPDATE items SET name_zh=? WHERE _id=?", (gzh, iid))
                n_gao += 1
            elif mzh:
                cur.execute("UPDATE items SET name_zh=? WHERE _id=?", (mzh, iid))
                n_manual += 1
            else:
                n_keep += 1
                print("  !! 无解: %s (%s)" % (iid, row["name"]))
    for sec in wiki["armor"]:
        is_head = "頭" in sec["section"]
        table = gah if is_head else gam
        for row in sec["rows"]:
            if r >= len(rows):
                break
            iid, name, name_zh = rows[r]
            r += 1
            if row["id"]:
                continue
            gzh, mzh = resolve(row["name"], table)
            if gzh:
                cur.execute("UPDATE items SET name_zh=? WHERE _id=?", (gzh, iid))
                n_gao += 1
            elif mzh:
                cur.execute("UPDATE items SET name_zh=? WHERE _id=?", (mzh, iid))
                n_manual += 1
            else:
                n_keep += 1
                print("  !! 无解: %s (%s)" % (iid, row["name"]))
    con.commit()
    print("gao 名:", n_gao, "| 手动:", n_manual, "| 保持:", n_keep)

    print("\n抽查:")
    for r in cur.execute("SELECT _id, name_zh FROM items WHERE _id >= 500000 AND _id < 500269 "
                         "ORDER BY _id LIMIT 30"):
        print("  ", r)
    # 片假名残留检查
    k = cur.execute("SELECT COUNT(*) FROM items WHERE _id >= 500000 AND _id < 500269 "
                    "AND name_zh GLOB '*[ァ-ヶ]*'").fetchone()[0]
    print("仍含片假名:", k)
    con.close()

    shutil.copy2(DB, CN)
    for z in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN, "database.db")
        print("repacked", z, round(os.path.getsize(z) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
