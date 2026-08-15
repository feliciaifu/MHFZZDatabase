# -*- coding: utf-8 -*-
"""Inspect palico_armor / palico_weapons / felyne_skills tables."""
import sqlite3

con = sqlite3.connect(r"app/src/main/assets/databases/database.db")
c = con.cursor()

for t in ("palico_armor", "palico_weapons", "felyne_skills"):
    print("== %s ==" % t)
    cols = [r[1] for r in c.execute("PRAGMA table_info(%s)" % t)]
    print("cols:", cols)
    print("rows:", c.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0])
    for r in c.execute("SELECT * FROM %s LIMIT 5" % t):
        print("  ", r)
    print()
con.close()
