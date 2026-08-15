# -*- coding: utf-8 -*-
"""中文化管线 - 物品中文对齐 + 建库

对齐规则（已验证）:
  物品名表索引 = 游戏物品 ID（int(item_hid, 16)），直接索引
  - item_hid 4 字符纯数字 hex（如 '0007'）→ 物品名表
  - item_hid 5 字符前缀（h/b/a/w/l...，如 'h0001'、'b2693'）→ 防具，跳过（后续批次）
  - item_hid 空 → 跳过
"""
import json
import os
import shutil
import sqlite3
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
OUT_DB = os.path.join(BASE, "database_cn.db")
CACHE = os.path.join(BASE, "cache", "items_zh.json")
TS_CHARS = os.path.join(BASE, "ts_chars.txt")  # 繁→简 单字映射表（取自 opencc TSCharacters.txt）


def load_char_map():
    """按字繁→简映射：只做逐字转换，不做任何词汇调整。

    表格式：每行 "繁体字 简体字[ 简体变体...]"，取第一个简体。
    """
    mapping = {}
    with open(TS_CHARS, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
    return mapping


_CHAR_MAP = load_char_map()

# 日式汉字/异体字补充映射（opencc 标准表不含，游戏汉化文本中常见）
_SUPPLEMENT = {
    "痺": "痹", "靭": "韧", "砕": "碎", "錬": "炼", "焔": "焰", "燐": "磷",
    "沢": "泽", "塩": "盐", "桜": "樱", "鉄": "铁", "仮": "假", "両": "两",
    "帰": "归", "歳": "岁", "豊": "丰", "収": "收", "売": "卖", "買": "买",
    "価": "价", "劇": "剧", "獣": "兽", "図": "图", "園": "园", "島": "岛",
    "読": "读", "語": "语", "訳": "译", "職": "职", "業": "业", "術": "术",
    "衛": "卫", "験": "验", "検": "检", "県": "县", "関": "关", "閉": "闭",
    "開": "开", "拡": "扩", "張": "张", "効": "效", "雑": "杂", "難": "难",
    "仏": "佛", "躰": "体", "體": "体", "毎": "每",
    "氣": "气", "溫": "温", "濕": "湿", "淺": "浅", "滿": "满", "澤": "泽",
    "燒": "烧", "嚴": "严", "壊": "坏", "聲": "声", "醫": "医",
    "裡": "里", "裏": "里", "餘": "余", "麼": "么",
    # 日式新字体（JIS 新字体 → 简体）
    "撃": "击", "焼": "烧", "値": "值", "専": "专", "砲": "炮", "蔵": "藏",
    "蝱": "虻", "鴈": "雁", "伝": "传", "歩": "步", "剣": "剑", "黒": "黑",
    "竜": "龙", "様": "样", "晩": "晚", "発": "发", "暦": "历", "汚": "污",
    "巻": "卷", "団": "团", "気": "气", "広": "广", "変": "变", "鉱": "矿",
    "楽": "乐", "氷": "冰", "対": "对", "圧": "压", "軽": "轻", "戦": "战",
    "醤": "酱", "歯": "齿", "絵": "绘", "満": "满", "鶏": "鸡", "髄": "髓",
    "帯": "带", "巣": "巢", "実": "实", "応": "应", "闘": "斗", "駆": "驱",
    "囲": "围", "繋": "系", "弾": "弹", "転": "转", "観": "观", "穏": "稳",
    "覚": "觉", "郷": "乡", "増": "增", "厳": "严", "潜": "潜", "聴": "听",
    "経": "经", "艶": "艳", "滝": "泷", "蛍": "萤", "猟": "猎", "勧": "劝",
    "兎": "兔", "亜": "亚", "賛": "赞", "隠": "隐", "歓": "欢", "譲": "让",
    "労": "劳", "臓": "脏", "続": "续", "亀": "龟", "頼": "赖", "悪": "恶",
    "辺": "边", "荘": "庄", "唖": "哑", "薬": "药", "鎗": "枪", "繍": "绣",
    "嚢": "囊", "廻": "回", "筯": "箸", "痺": "痹", "靭": "韧", "砕": "碎",
    "錬": "炼", "焔": "焰", "燐": "磷", "覇": "霸", "頬": "颊", "嚙": "啮",
    "䖝": "绿",  # 「绿」的异体字（游戏汉化常见，防具名如 䖝色护脚）
}
for _k, _v in _SUPPLEMENT.items():
    _CHAR_MAP.setdefault(_k, _v)


def to_simplified(text):
    """游戏汉化文本（繁体）→ 简体：纯按字转换"""
    if not text:
        return text
    return "".join(_CHAR_MAP.get(c, c) for c in text)


def load_cache():
    with open(CACHE, encoding="utf-8") as f:
        return json.load(f)


def is_item_hid(hid):
    """4 字符纯数字 hex = 普通物品 ID"""
    return (hid is not None and len(hid) == 4 and
            all(c in "0123456789abcdefABCDEF" for c in hid))


def main():
    zh = load_cache()
    names = [to_simplified(s) for s in zh["name"]]       # 索引 = 物品 ID
    descs = [to_simplified(s) for s in zh["description"]]
    sources = [to_simplified(s) for s in zh["source"]]
    n_slots = len(names)

    assert os.path.exists(SRC_DB), "源数据库不存在: " + SRC_DB
    shutil.copy2(SRC_DB, OUT_DB)
    con = sqlite3.connect(OUT_DB)
    cur = con.cursor()

    # 新增列（已存在则跳过）
    existing = {r[1] for r in cur.execute("PRAGMA table_info(items)")}
    for col in ("name_zh", "description_zh", "source_zh"):
        if col not in existing:
            cur.execute("ALTER TABLE items ADD COLUMN %s TEXT" % col)

    # 收集所有物品 ID（去重）
    rows = cur.execute("SELECT _id, item_hid, name_ja FROM items").fetchall()
    id_rows = [(r[0], int(r[1], 16)) for r in rows if is_item_hid(r[1])]
    valid = [(iid, vid) for iid, vid in id_rows if 1 <= vid < n_slots]
    oob = [(iid, vid) for iid, vid in id_rows if not (1 <= vid < n_slots)]

    print("items 行数: %d | 数字 hid: %d | 表内: %d | 表外: %d" %
          (len(rows), len(id_rows), len(valid), len(oob)))

    # 占位检测：'1F' 这类自引用 hex 文本 = 游戏未命名物品
    placeholder = 0
    updated = 0
    for iid, vid in valid:
        name = names[vid]
        if name == format(vid, "X") or name == format(vid, "x") or name == "------":
            placeholder += 1
            continue
        cur.execute(
            "UPDATE items SET name_zh=?, description_zh=?, source_zh=? WHERE _id=?",
            (name, descs[vid], sources[vid], iid))
        updated += 1

    con.commit()

    # 覆盖率报告
    total = len(valid)
    print("已更新: %d | 占位跳过: %d | 覆盖: %.1f%%" %
          (updated, placeholder, 100.0 * updated / max(total, 1)))

    # 抽查
    print("\n抽查:")
    for hid in ("0001", "0007", "0008", "0020", "008E", "013A", "05A8"):
        r = cur.execute("SELECT _id, item_hid, name_ja, name_zh FROM items WHERE item_hid=?",
                        (hid,)).fetchone()
        if r:
            print("  %s %-20s %-20s %s" % (r[1], r[2], r[3] or "(占位/空)", ""))
        else:
            print("  %s 不在 items 表" % hid)

    con.close()

    # 打包 zip（App 资源格式：database.db.zip）
    zip_path = os.path.join(BASE, "database_cn.db.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(OUT_DB, "database.db")
    print("\n输出: %s (%.1f MB)" % (OUT_DB, os.path.getsize(OUT_DB) / 1048576))
    print("输出: %s (%.1f MB)" % (zip_path, os.path.getsize(zip_path) / 1048576))


if __name__ == "__main__":
    main()
