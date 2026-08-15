# -*- coding: utf-8 -*-
"""给 bento 表补 name_zh 空列（MetadataDao.colName("b") 兜底 COALESCE 需要）。"""
import os
import shutil
import sqlite3
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
CN_DB = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")

con = sqlite3.connect(ASSETS_DB)
cols = {r[1] for r in con.execute("PRAGMA table_info(bento)")}
if "name_zh" not in cols:
    con.execute("ALTER TABLE bento ADD COLUMN name_zh TEXT")
    con.commit()
    print("+ bento.name_zh")
else:
    print("bento.name_zh 已存在")
con.close()

shutil.copy2(ASSETS_DB, CN_DB)
for zpath in (ASSETS_ZIP, CN_ZIP):
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(CN_DB, "database.db")
    print("重打包:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))
