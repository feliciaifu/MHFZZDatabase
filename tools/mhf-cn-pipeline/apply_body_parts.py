# -*- coding: utf-8 -*-
"""怪物伤害部位中文化：monster_damage.body_part_zh（英文/日文部位 → 中文）。"""
import os
import shutil
import sqlite3
import zipfile

DB = r"app/src/main/assets/databases/database.db"
CN = r"tools/mhf-cn-pipeline/database_cn.db"

PART_ZH = {
    # 英文
    "Head": "头", "Tail": "尾巴", "Back": "背", "Belly": "腹部",
    "Leg": "腿", "Wing": "翼", "Neck": "颈", "Torso": "躯干",
    "Right Foot": "右脚", "Left Foot": "左脚",
    # 日文
    "後脚": "后脚", "前脚": "前脚", "胴": "躯干", "尾先": "尾尖",
    "左爪": "左爪", "右爪": "右爪", "全身": "全身", "結晶": "结晶",
    "腕": "腕", "ヤド": "壳", "鋏": "钳", "尾": "尾巴", "胸": "胸",
    "喉": "喉咙", "鉤爪": "钩爪", "牙": "牙", "副尾": "副尾",
    "背中/尻尾": "背/尾巴", "顔": "脸", "頭部": "头部", "舌": "舌",
    "腹/脚": "腹/脚", "背棘": "背棘", "手": "手", "左前脚": "左前脚",
    "右前脚": "右前脚", "尾先端": "尾尖端", "触角": "触角", "触手": "触手",
    "目": "眼", "口中": "口中", "氷尾": "冰尾", "頭首": "头颈",
    "翼尾/先端": "翼尾/尖端", "左脚/腹": "左脚/腹", "左後脚": "左后脚",
    "右後脚": "右后脚", "角": "角", "翼脚": "翼脚", "尾中間": "尾中间",
    "肩": "肩", "弱点/体中": "弱点/全身", "翼膜": "翼膜", "爪": "爪",
    "弱点/ヤドの中": "弱点/壳中", "？？": "？？", "": "", "-": "-",
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    if "body_part_zh" not in [r[1] for r in cur.execute("PRAGMA table_info(monster_damage)")]:
        cur.execute("ALTER TABLE monster_damage ADD COLUMN body_part_zh TEXT")

    n = n_miss = 0
    for part, zh in PART_ZH.items():
        cur.execute("UPDATE monster_damage SET body_part_zh=? WHERE body_part=?", (zh, part))
        n += 1
    # 未映射的（应无）
    for r in cur.execute("SELECT DISTINCT body_part FROM monster_damage "
                         "WHERE body_part_zh IS NULL"):
        n_miss += 1
        print("  !! 未映射:", repr(r[0]))
    con.commit()

    print("映射写入:", n, "| 未映射:", n_miss)
    print("\n抽查:")
    for r in cur.execute("SELECT body_part, body_part_zh FROM monster_damage "
                         "WHERE body_part IN ('Head','背棘','ヤド','前脚','Right Foot','翼膜') "
                         "GROUP BY body_part"):
        print("  ", r)
    con.close()

    shutil.copy2(DB, CN)
    for z in (r"app/src/main/assets/databases/database.db.zip",
              r"tools/mhf-cn-pipeline/database_cn.db.zip"):
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(CN, "database.db")
        print("repacked", z, round(os.path.getsize(z) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
