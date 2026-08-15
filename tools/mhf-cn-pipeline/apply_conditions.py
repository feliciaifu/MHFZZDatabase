# -*- coding: utf-8 -*-
"""hunting_rewards 条件中文化：condition_ja（日文）→ condition_zh（中文）。

界面显示走 localizeColumn("h.condition")：zh → COALESCE(condition_zh, condition_ja, condition)。
"""
import os
import re
import shutil
import sqlite3
import zipfile

DB = r"app/src/main/assets/databases/database.db"
CN = r"tools/mhf-cn-pipeline/database_cn.db"

# 通用翻译规则（按 pattern 匹配 condition_ja）
RULES = [
    (r"^本体 (\d+)回$", lambda m: "本体剥取%s次" % m.group(1)),
    (r"^本体 (\d+)回$", None),  # placeholder to keep order explicit
]

# 精确映射（简单值）
EXACT = {
    "捕獲報酬": "捕获报酬",
    "落とし物": "掉落物",
    "ＨＣ剥ぎ取り": "HC剥取",
    "死にまね中": "装死中",
    "キング": "王者",
    "体質白討伐": "体质白讨伐",
    "体質紅討伐": "体质红讨伐",
    "体質蒼討伐": "体质苍讨伐",
    "体質黄討伐": "体质黄讨伐",
    "消火中に転倒": "灭火中摔倒",
    "切断後結晶破壊": "切断后破坏结晶",
    "捕獲報酬:蒼": "捕获报酬：苍",
    "本体蒼 3回": "本体苍剥取3次",
    "嘔吐：緑石": "呕吐：绿石",
    "嘔吐：青石": "呕吐：青石",
    "嘔吐：紫石": "呕吐：紫石",
    "嘔吐：白石": "呕吐：白石",
    "嘔吐：肉": "呕吐：肉",
    "尻尾(水晶)": "尾巴（水晶）",
    "追加報酬：嘔吐１回": "追加报酬：呕吐1次",
    "追加報酬：嘔吐２回": "追加报酬：呕吐2次",
    "追加報酬：嘔吐３回": "追加报酬：呕吐3次",
    "追加報酬：嘔吐４回": "追加报酬：呕吐4次",
    "部位破壊：ドスランポス吸血後": "部位破坏：迅猛龙王吸血后",
    "部位破壊：ドスゲネポス吸血後": "部位破坏：痹猛龙王吸血后",
    "部位破壊：ドスイーオス吸血後": "部位破坏：毒猛龙王吸血后",
}

# 部位名映射（部位破壊：X / 破壊報酬：X / 落とし物：X / 嘔吐：X）
PART = {
    "頭": "头", "背中": "背", "翼": "翼", "角": "角", "尻尾": "尾巴",
    "爪": "爪", "腹": "腹部", "頭部": "头部", "尾": "尾", "ヒレ": "鳍",
    "右爪": "右爪", "左爪": "左爪", "翼爪": "翼爪", "嘴": "嘴", "殻": "壳",
    "体": "体", "左翼": "左翼", "右翼": "右翼", "胴体": "躯干", "前脚": "前脚",
    "脚": "脚", "前足": "前足", "腕": "腕", "耳": "耳", "牙": "牙",
    "翼脚": "翼脚", "尾ヒレ": "尾鳍", "首元": "颈部", "翼膜": "翼膜",
    "後足": "后足", "後脚": "后脚", "眼": "眼", "脊/足": "背/足",
    "尾翼": "尾翼", "足": "足", "触覚": "触角", "両腕": "双腕",
    "舌": "舌", "左前足": "左前足", "右前足": "右前足", "他": "其他",
    "？？": "？？", "殻(頭殻)": "壳（头壳）", "殻(骨)": "壳（骨）",
    "殻(貝)": "壳（贝）", "左副尾": "左副尾", "右副尾": "右副尾",
    "背中?": "背？",
}


def trans_part(part):
    """部位破壊：頭1段階 / 頭2段階 / 頭[辿] 等"""
    s = part
    s = s.replace("[辿]", "[辿异]")
    m = re.match(r"(.+?)(\d+)段階$", s)
    if m:
        return trans_part(m.group(1)) + m.group(2) + "阶段"
    # 未知部位逐字转简
    import sys
    sys.path.insert(0, r"tools/mhf-cn-pipeline")
    import align_items as A
    return A.to_simplified(PART.get(s, s))


def translate(ja):
    if not ja:
        return ""
    if ja in EXACT:
        return EXACT[ja]
    # 本体 N回 / 本体：X N回 / 本体：X N×M回
    m = re.match(r"^本体(?:：(.+?))? (\d+)(?:×(\d+))?回$", ja)
    if m:
        body = trans_part(m.group(1)) if m.group(1) else ""
        n = m.group(2)
        m2 = m.group(3)
        if m2:
            return "本体：%s %s×%s次" % (body, n, m2)
        return "本体%s剥取%s次" % (("：" + body) if body else "", n)
    # 尻尾 N回 / 背中 N回
    m = re.match(r"^(尻尾|背中) (\d+)回$", ja)
    if m:
        return "%s剥取%s次" % (trans_part(m.group(1)), m.group(2))
    # 部位破壊：X
    if ja.startswith("部位破壊："):
        return "部位破坏：" + trans_part(ja[len("部位破壊："):])
    # 破壊報酬：X
    if ja.startswith("破壊報酬："):
        return "破坏报酬：" + trans_part(ja[len("破壊報酬："):])
    # 落とし物：X
    if ja.startswith("落とし物："):
        return "掉落物：" + trans_part(ja[len("落とし物："):])
    # 嘔吐：X
    if ja.startswith("嘔吐："):
        return "呕吐：" + trans_part(ja[len("嘔吐："):])
    return None  # 未覆盖


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute("SELECT DISTINCT condition_ja FROM hunting_rewards").fetchall()
    n_ok = n_fail = 0
    for (ja,) in rows:
        zh = translate(ja)
        if zh is None:
            n_fail += 1
            print("  !! 未覆盖: %r" % ja)
            continue
        cur.execute("UPDATE hunting_rewards SET condition_zh=? WHERE condition_ja=?",
                    (zh, ja))
        n_ok += 1
    con.commit()
    print("翻译写入: %d | 未覆盖: %d" % (n_ok, n_fail))

    print("\n抽查:")
    for r in cur.execute("SELECT condition_ja, condition_zh FROM hunting_rewards "
                         "WHERE condition_zh IS NOT NULL GROUP BY condition_ja LIMIT 15"):
        print("  %-20s -> %s" % (r[0], r[1]))
    con.close()

    shutil.copy2(DB, CN)
    for z in (r"app/src/main/assets/databases/database.db.zip",
              r"tools/mhf-cn-pipeline/database_cn.db.zip"):
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN, "database.db")
        print("repacked", z, round(os.path.getsize(z) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
