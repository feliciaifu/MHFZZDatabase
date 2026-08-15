# -*- coding: utf-8 -*-
"""Fix two bento names to standard simplified-Chinese spellings."""
import os
import shutil
import sqlite3
import zipfile

DB = r"app/src/main/assets/databases/database.db"
CN = r"tools/mhf-cn-pipeline/database_cn.db"

con = sqlite3.connect(DB)
con.execute("UPDATE items SET name_zh='呆瓜意大利面' WHERE _id=400014")
con.execute("UPDATE items SET name_zh='辣辣咖喱' WHERE _id=400010")
con.commit()
for r in con.execute("SELECT _id, name_zh FROM items WHERE _id IN (400010, 400014)"):
    print(r)
con.close()

shutil.copy2(DB, CN)
for z in (r"app/src/main/assets/databases/database.db.zip",
          r"tools/mhf-cn-pipeline/database_cn.db.zip"):
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(CN, "database.db")
    print("repacked", z, round(os.path.getsize(z) / 1048576, 1), "MB")
