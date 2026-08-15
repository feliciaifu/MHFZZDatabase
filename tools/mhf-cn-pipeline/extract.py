# -*- coding: utf-8 -*-
"""中文化管线 - 提取中文文本源（物品名/描述/入手来源）

用 FrontierTextHandler 解析游戏汉化文件，提取物品三表，缓存为 JSON。
输出: cache/items_zh.json
"""
import json
import os
import sys

FTH_DIR = r"D:\repos\FrontierTextHandler"
GAME_DAT = r"D:\Games\PC\MHF\dat"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

sys.path.insert(0, FTH_DIR)
from src import common  # noqa: E402

SECTIONS = [
    ("dat/items/name", "name", 0),
    ("dat/items/description", "description", 24),  # 前 24 条为 UI 消息
    ("dat/items/source", "source", 0),
]

HEADERS_PATH = os.path.join(FTH_DIR, "headers.json")


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    data = common.load_file_data(os.path.join(GAME_DAT, "mhfdat.bin"))
    out = {}
    for xpath, key, shift in SECTIONS:
        cfg = common.read_extraction_config(xpath, HEADERS_PATH)
        entries = common.extract_text_data_from_bytes(data, cfg, "zz")
        # 对齐后列表：索引 i 对应物品 ID i+1
        aligned = [e["text"] for e in entries[shift:]]
        out[key] = aligned
        print("%-16s %6d 条 (shift=%d)" % (key, len(aligned), shift))

    path = os.path.join(CACHE_DIR, "items_zh.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("写入:", path)

    # 抽查
    print("\n抽查（物品 ID → 中文）:")
    for idx in [0, 1, 6, 7, 31, 141]:
        print("  ID %-4d name=%-16s desc=%-24s src=%s" % (
            idx + 1,
            out["name"][idx][:16],
            out["description"][idx][:24].replace("\n", " "),
            out["source"][idx][:20].replace("\n", " ")))


if __name__ == "__main__":
    main()
