# -*- coding: utf-8 -*-
"""Fix palico_weapons.element NULL -> '' (UI calls .length() on it)."""
import os
import shutil
import sqlite3
import zipfile

DB = r"app/src/main/assets/databases/database.db"
CN = r"tools/mhf-cn-pipeline/database_cn.db"

con = sqlite3.connect(DB)
n = con.execute("UPDATE palico_weapons SET element = '' WHERE element IS NULL").rowcount
con.commit()
print("fixed rows:", n)
con.close()

shutil.copy2(DB, CN)
for z in (r"app/src/main/assets/databases/database.db.zip",
          r"tools/mhf-cn-pipeline/database_cn.db.zip"):
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(CN, "database.db")
    print("repacked", z, round(os.path.getsize(z) / 1048576, 1), "MB")
