# -*- coding: utf-8 -*-
"""Find felyne-related tables in DB."""
import sqlite3

con = sqlite3.connect(r"app/src/main/assets/databases/database.db")
c = con.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("all tables:", tables)
print()
print("candidate:", [t for t in tables if "felyne" in t or "cat" in t or "palico" in t or "gao" in t])
con.close()
