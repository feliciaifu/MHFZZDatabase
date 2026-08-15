# -*- coding: utf-8 -*-
"""便当中文化：items 400001-400016（Bento 料理）→ 中文名 → name_zh。

译名来源：MHF 台湾版 Wiki「料理食譜」页（mhwiki.axibug.com/atwiki_mhfotw/w.atwiki.jp/mhfotw/pages/16.html）
用食材组合与 wiki 表格逐条精确匹配，16 个便当全部命中官方译名（繁体），此处繁→简。
例：コロコロッケ(可乐饼) → 滾動可樂餅 → 滚动可乐饼
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

# 官方译名（繁体，来自 TW wiki）→ 简体
BENTO_TW = {
    400001: "暗暗稀飯",        # Ananzo Suey / アンアンゾースイ（アンアン=暗暗）
    400002: "滾動可樂餅",      # Coro-Croquettes / コロコロッケ（コロコロ=滚动）
    400003: "爆炸湯",          # Dokkan Soup / ドッカンスープ（ドッカン=爆炸声）
    400004: "驚異燉飯",        # Dokkiri Risotto / ドッキリゾット（ドッキリ=惊异）
    400005: "冒泡焗烤",        # Doku-doku Doria / ドクドクドリア（咕嘟冒泡）
    400006: "圓滾炸物",        # Fried Pokkori / ポッコリフライ（ポッコリ=圆滚滚）
    400007: "燦爛拉麵",        # Gingi Ramen / ギンギラーメン（ギンギラ=灿烂）
    400008: "滾動奶汁烤菜",    # Gura-Gratin / グラグラタン（グラタン=奶汁烤菜）
    400009: "毅力炒飯",        # Guts Fried Rice / ガッツチャーハン（ガッツ=毅力）
    400010: "辣辣咖哩",        # Hi-hi Curry / ヒーヒーカレー（辣得嘶嘶）
    400011: "暖暖鍋",          # Hoku-hoku Hot Pot / ホクホク鍋（热乎乎）
    400012: "巨型披薩",        # Jumbo Pizza / ジャンボピザ
    400013: "驚人蛋糕",        # Ottama Cake / オッタマケーキ（オッタマ=吃惊）
    400014: "呆瓜義大利麵",    # Pappara Pasta / パッパラパスタ（パッパラ=呆瓜）
    400015: "蘭蘭沙拉",        # Ran-Ran Salad / ランランサラダ
    400016: "驚嚇燉肉",        # Surprise Stew / ビックリシチュー（ビックリ=惊吓）
}


def main():
    con = sqlite3.connect(ASSETS_DB)
    cur = con.cursor()
    n = 0
    for iid, tw in sorted(BENTO_TW.items()):
        zh = A.to_simplified(tw)
        r = cur.execute("SELECT name_ja FROM items WHERE _id=?", (iid,)).fetchone()
        if not r:
            print("  !! items %s 不存在" % iid)
            continue
        cur.execute("UPDATE items SET name_zh=? WHERE _id=?", (zh, iid))
        print("  %s %-18s | %-8s -> %s" % (iid, r[0], tw, zh))
        n += 1
    con.commit()
    print("写入:", n)

    for r in cur.execute("SELECT _id, name_ja, name_zh FROM items "
                         "WHERE _id BETWEEN 400001 AND 400016 ORDER BY _id"):
        print("  ", r)
    con.close()

    shutil.copy2(ASSETS_DB, CN_DB)
    for zpath in (ASSETS_ZIP, CN_ZIP):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN_DB, "database.db")
        print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))


if __name__ == "__main__":
    main()
