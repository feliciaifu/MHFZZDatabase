# -*- coding: utf-8 -*-
"""技能面板中文化（完整版）：skill.html（普通技能）+ skill_chan.html（辿异技能）→ _zh 列。

树匹配：树名繁→简后 == name_ja，或 TREE_MAP（wiki 中文译名 ↔ DB 日文名）。
技能匹配：树内（树名+点数），先 (名字简, 点数) 精确，再同树内点数兜底。
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
sys.path.insert(0, BASE)
import align_items as A

ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
CN_DB = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")

# wiki 树名（中文译名）→ DB skill_trees._id
TREE_MAP = {
    # 基础（之前确认）
    "研磨師": 4, "全耐性UP": 51, "三界的守護": 134, "調和師": 118, "搬運": 58,
    "耐力": 40, "用餐": 6, "防禦性能": 11, "銳利度": 43, "子彈調和": 63,
    "眩暈": 9, "偷竊無效": 35, "地型": 41, "釣魚": 24, "採集": 2, "剝取": 20,
    # 本轮新增（wiki 中文译名 ↔ DB 日文名）
    "飢餓": 50,          # はらへり
    "大胃王": 7,          # 食いしん坊
    "危險品領會": 145,     # 劇物の心得
    "吹笛名人": 104,       # 笛吹き名人
    "突發力": 18,          # 底力
    "蓄力威力": 129,       # 溜め威力
    "武器技術": 103,       # 武器捌き
    "得意": 173,          # 腕利き
    "質擊": 165,          # 贅撃
    "遁逃": 108,          # とんずら
    "單手劍技": 85,        # 片手剣技
    "大錘技": 91,          # 鎚技
    "裝著": 127,          # 装着
    "子彈節約術": 201,     # 弾丸節約術強化
    "除臭": 74,           # 脱臭
    "耐醉": 193,          # 耐酔
    "毅力": 100,          # 根性
    "反覆無常": 96,        # 気まぐれ
    "強力投手": 109,       # ナイフ使い
    "獵人": 111,          # 狩人
    "烤肉": 54,           # 肉焼き
    "魔物": 56,           # モンスター
    "育成": 112,          # ブリーダー
    "羈絆": 72,           # 絆
    "靈光一閃": 66,        # ひらめき
    "捕獲高手": 61,        # 捕獲上手
    "慰勞": 128,          # いたわり
    "黑之命脈": 143,       # 黒ノ命脈
    "拔納術": 158,         # 抜納術
    # 辿异技能（skill_chan.html kind ↔ DB 強化系树）
    "技能格擴張": 216,      # スキル枠拡張
    "閃轉強化": 203,        # 閃転強化
    "巧擊強化": 219,        # 巧撃強化
    "巧流強化": 220,        # 巧流強化
    "纏雷強化": 221,        # 纏雷強化
    "吸血強化": 222,        # 吸血強化
    "血氣活性強化": 223,     # 血気活性強化
    "風壓強化": 224,        # 風圧強化
    "耐麻痺強化": 211,      # 耐麻痺強化
    "耐毒強化": 212,        # 耐毒強化
    "耐震強化": 213,        # 耐震強化
    "耐睡眠強化": 217,      # 耐睡眠強化
    "反射強化": 214,        # 反射強化
    "猛進強化": 215,        # 猛進強化
    "ガード性能強化": 207,   # ガード性能強化
    "耳栓強化": 208,        # 耳栓強化
    "氷界創生強化": 209,    # 氷界創生強化
    "雌伏強化": 210,        # 雌伏強化
    "弾丸節約術強化": 201,   # 弾丸節約術強化
    "幕無強化": 202,        # 幕無強化
    "屬擊強化": 204,        # 属撃強化
    "劇物強化": 205,        # 劇物強化
    "鼓舞強化": 206,        # 鼓舞強化
    "適應擊強化": 199,      # 適応撃強化
    "支援強化": 200,        # 支援強化
    "喝強化": 218,          # 喝強化
    "耳塞強化": 208,        # 耳栓強化
    "危險品強化": 205,      # 劇物強化
    "子彈節約術強化": 201,   # 弾丸節約術強化
    "防禦性能強化": 207,    # ガード性能強化
    "穩射": 153,           # 穏射
}

# 日文汉字 → 简体（技能/树名归一用）
JP2CN = {"穏": "稳", "軽": "轻", "転": "转", "拡": "扩", "撃": "击", "弾": "弹",
         "枠": "框", "圧": "压", "気": "气", "発": "发", "応": "应", "遅": "迟",
         "減": "减", "強": "强", "時": "时", "間": "间", "変": "变", "確": "确",
         "残": "残", "暑": "暑", "寒": "寒", "氷": "冰", "龍": "龙", "炎": "炎",
         "護": "护", "抜": "拔", "獣": "兽", "鉄": "铁", "鎚": "锤", "剣": "剑",
         "猟": "猎", "獲": "获", "採": "采", "釣": "钓", "業": "业", "職": "职",
         "統": "统", "弾丸": "弹丸"}


def norm(s):
    t = A.to_simplified(s or "").replace(" ", "")
    for k, v in JP2CN.items():
        t = t.replace(k, v)
    return t


def parse_skill_page(path, chan=False):
    html = open(path, encoding="utf-8").read()
    trees = []
    cur = None
    for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", html):
        tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr)
        ths = re.findall(r"<th[^>]*>([\s\S]*?)</th>", tr)
        if ths and not tds:
            continue
        cells = [re.sub(r"<[^>]+>", "", td).strip() for td in tds]
        cells = [c for c in cells if c]
        if not cells:
            continue
        if chan:
            # 辿异：kind(系统), origin(来源), name(技能), effect(效果)
            if len(cells) >= 4 and cells[2]:
                if cur is None or cur["name"] != cells[0]:
                    cur = {"name": cells[0], "skills": []}
                    trees.append(cur)
                cur["skills"].append({"name": cells[2], "points": None,
                                      "desc": cells[3] if len(cells) > 3 else ""})
        else:
            # 普通：树行 [树名, ○/×, 技能名, 点数, 描述]
            if len(cells) >= 4 and cells[1] in ("○", "×"):
                cur = {"name": cells[0],
                       "skills": [{"name": cells[2], "points": cells[3],
                                   "desc": cells[4] if len(cells) > 4 else ""}]}
                trees.append(cur)
            elif len(cells) >= 3 and cur is not None:
                cur["skills"].append({"name": cells[0], "points": cells[1],
                                      "desc": cells[2] if len(cells) > 2 else ""})
    return trees


def main():
    trees = parse_skill_page(os.path.join(r"tools/mhf-wiki-mirror/skill", "skill.html"))
    trees += parse_skill_page(os.path.join(r"tools/mhf-wiki-mirror/skill", "skill_chan.html"), chan=True)
    print("trees total:", len(trees), "| skills:",
          sum(len(t["skills"]) for t in trees))

    con = sqlite3.connect(ASSETS_DB)
    cur = con.cursor()

    db_trees = {norm(r[1]): r[0] for r in cur.execute("SELECT _id, name_ja FROM skill_trees")}
    tree_zh = {}
    n_tree = n_tree_miss = 0
    tree_misses = []
    for t in trees:
        tn = norm(t["name"])
        tid = db_trees.get(tn) or TREE_MAP.get(t["name"])
        if tid:
            zh = A.to_simplified(t["name"])
            cur.execute("UPDATE skill_trees SET name_zh=? WHERE _id=?", (zh, tid))
            tree_zh[tn] = zh
            n_tree += 1
        else:
            n_tree_miss += 1
            if len(tree_misses) < 20:
                tree_misses.append(t["name"])

    db_skills = cur.execute(
        "SELECT _id, skill_tree_id, name_ja, required_skill_tree_points FROM skills").fetchall()
    idx = {}
    idx_pts = {}
    for sid, stid, name_ja, pts in db_skills:
        idx.setdefault((norm(name_ja), str(pts)), []).append((sid, stid))
        idx_pts.setdefault((str(stid), str(pts)), []).append(sid)

    n_sk = n_pts = n_miss = 0
    miss_examples = []
    for t in trees:
        tn = norm(t["name"])
        tid = db_trees.get(tn) or TREE_MAP.get(t["name"])
        for s in t["skills"]:
            if s["points"] in ("○", "×"):
                continue
            sid = None
            if s["points"] is not None:
                hits = idx.get((norm(s["name"]), s["points"]))
                if hits:
                    sid = hits[0][0]
                elif tid:
                    pts_hits = idx_pts.get((str(tid), s["points"]))
                    if pts_hits and len(pts_hits) == 1:
                        sid = pts_hits[0]
                        n_pts += 1
            else:
                # 辿异技能：按树内名字匹配
                hits = idx.get((norm(s["name"]), None))
                if not hits and tid:
                    hits = [r for r in db_skills
                            if str(r[1]) == str(tid) and norm(r[2]) == norm(s["name"])]
                if hits:
                    sid = hits[0][0]
            if sid:
                cur.execute("UPDATE skills SET name_zh=?, description_zh=?, skill_tree_name_zh=? "
                            "WHERE _id=?",
                            (A.to_simplified(s["name"]), A.to_simplified(s["desc"]),
                             tree_zh.get(tn, A.to_simplified(t["name"])), sid))
                n_sk += 1
            else:
                n_miss += 1
                if len(miss_examples) < 15:
                    miss_examples.append((t["name"], s["name"], s["points"]))

    con.commit()
    print("树: %d 匹配, %d 未匹配" % (n_tree, n_tree_miss))
    print("技能: %d 匹配（点数兜底 %d）, %d 未匹配" % (n_sk, n_pts, n_miss))
    print("树未匹配:", tree_misses)
    print("技能未匹配示例:", miss_examples)

    print("\nDB 剩余未填技能:",
          cur.execute("SELECT COUNT(*) FROM skills WHERE name_zh IS NULL OR name_zh = ''").fetchone()[0])
    print("DB 剩余未填树:",
          cur.execute("SELECT COUNT(*) FROM skill_trees WHERE name_zh IS NULL OR name_zh = ''").fetchone()[0])
    con.close()

    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
