# -*- coding: utf-8 -*-
"""地区面板中文化：locations.name_zh 完整语义映射（依据英文名/日文名）。"""
import os
import shutil
import sqlite3
import zipfile

DB = r"app/src/main/assets/databases/database.db"
CN = r"tools/mhf-cn-pipeline/database_cn.db"

LOC_ZH = {
    1: "密林", 3: "密林Dream", 4: "沙漠", 6: "雪山",
    8: "斗技演习1", 10: "斗技演习2", 12: "沼泽", 14: "火山(A)",
    16: "森丘", 18: "塔1", 19: "塔3", 20: "攻城要塞",
    22: "斗技演习3", 24: "城", 25: "绯红战场", 26: "城镇攻防",
    28: "要塞", 30: "峡谷", 32: "塔NEST", 33: "高地",
    35: "潮岛", 37: "树海", 39: "树海顶端", 40: "塔2",
    41: "决战场", 42: "火山(B)", 44: "花田", 46: "第一区塔1",
    47: "第一区塔2", 48: "紧急塔", 49: "竹林", 51: "大型飞空艇",
    52: "第二区塔2", 53: "第三区塔", 54: "第四区塔", 55: "第二区塔1",
    56: "决战场2", 57: "白湖", 59: "望云要塞", 60: "极海",
    62: "彩之泷", 64: "圣域", 65: "圣峰", 66: "猎人之路",
    67: "世界尽头", 68: "深坑", 69: "商队气球", 71: "孤境深渊·讨伐1",
    72: "孤境深渊·支援1", 73: "孤境深渊·支援2", 74: "孤境深渊·支援3",
    75: "孤境深渊·支援4", 76: "孤境深渊·支援5", 77: "史迹",
    78: "孤境岛1", 79: "孤境岛2", 80: "孤境岛3", 81: "迎击据点",
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute("SELECT _id, name, name_ja FROM locations ORDER BY _id").fetchall()
    n = 0
    for iid, name, name_ja in rows:
        zh = LOC_ZH.get(iid)
        if not zh:
            print("  !! 未映射 %s (%s/%s)" % (iid, name, name_ja))
            continue
        cur.execute("UPDATE locations SET name_zh=? WHERE _id=?", (zh, iid))
        n += 1
    con.commit()
    print("写入:", n, "/", len(rows))

    print("\n结果:")
    for r in cur.execute("SELECT _id, name, name_zh FROM locations ORDER BY _id"):
        print("  %-3s %-26s %s" % (r[0], r[1] or "-", r[2]))
    con.close()

    shutil.copy2(DB, CN)
    for z in (r"app/src/main/assets/databases/database.db.zip",
              r"tools/mhf-cn-pipeline/database_cn.db.zip"):
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN, "database.db")
        print("repacked", z, round(os.path.getsize(z) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
