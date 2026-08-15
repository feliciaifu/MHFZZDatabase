# -*- coding: utf-8 -*-
"""删除猫铠甲 7 个空槽（items + palico_armor）。"""
import os
import shutil
import sqlite3
import zipfile

DB = r"app/src/main/assets/databases/database.db"
CN = r"tools/mhf-cn-pipeline/database_cn.db"

con = sqlite3.connect(DB)
cur = con.cursor()
n1 = cur.execute("DELETE FROM palico_armor WHERE _id BETWEEN 500242 AND 500248").rowcount
n2 = cur.execute("DELETE FROM items WHERE _id BETWEEN 500242 AND 500248").rowcount
con.commit()
print("deleted palico_armor:", n1, "| items:", n2)
print("palico_armor 剩余:", cur.execute("SELECT COUNT(*) FROM palico_armor").fetchone()[0])
print("items 猫装备剩余:", cur.execute(
    "SELECT COUNT(*) FROM items WHERE _id >= 500000").fetchone()[0])
con.close()

shutil.copy2(DB, CN)
for z in (r"app/src/main/assets/databases/database.db.zip",
          r"tools/mhf-cn-pipeline/database_cn.db.zip"):
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(CN, "database.db")
    print("repacked", z)
