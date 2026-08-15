# -*- coding: utf-8 -*-
"""为 localizeColumn 兜底（中→日→英）补 _zh 列。

- 无 _zh 列的表补空列（后续批次填数据，兜底先显示日文）
- decorations/cuffs 的 name_zh 直接从 items 复制（同 _id）
- horn_melodies/hunting_rewards/quests 补 _zh 列
"""
import shutil
import sqlite3
import zipfile

SRC = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
OUT = r"D:\repos\MHFZZDatabase\tools\mhf-cn-pipeline\database_cn.db"

shutil.copy2(SRC, OUT)
con = sqlite3.connect(OUT)
cur = con.cursor()

def add_cols(table, cols):
    existing = {r[1] for r in cur.execute("PRAGMA table_info(%s)" % table)}
    for c in cols:
        if c not in existing:
            cur.execute("ALTER TABLE %s ADD COLUMN %s TEXT" % (table, c))
            print("  + %s.%s" % (table, c))

# 需要补 _zh 列的表（name_ja 已存在的直接兜底到日文）
add_cols("quests", ["name_zh", "header_zh", "goal_zh", "sub_goal_a_zh",
                    "sub_goal_b_zh", "flavor_zh", "hirer_zh"])
add_cols("locations", ["name_zh"])
add_cols("skill_trees", ["name_zh", "desc_zh"])
add_cols("skills", ["name_zh", "description_zh", "skill_tree_name_zh"])
add_cols("cuffs", ["name_zh"])
add_cols("armor_families", ["name_zh"])
add_cols("horn_melodies", ["effect1_zh", "effect2_zh"])
add_cols("hunting_rewards", ["condition_zh"])

# decorations 没有 name_ja 列 → 补 name_ja（复制 name）+ name_zh
dcols = {r[1] for r in cur.execute("PRAGMA table_info(decorations)")}
if "name_ja" not in dcols:
    cur.execute("ALTER TABLE decorations ADD COLUMN name_ja TEXT")
    cur.execute("UPDATE decorations SET name_ja = name")
    print("  + decorations.name_ja (复制 name)")
if "name_zh" not in dcols:
    cur.execute("ALTER TABLE decorations ADD COLUMN name_zh TEXT")
    print("  + decorations.name_zh")

# decorations/cuffs 的 name_zh 从 items 复制（同 _id）
for table in ("decorations", "cuffs"):
    n = cur.execute("""UPDATE %s SET name_zh = (
        SELECT i.name_zh FROM items i WHERE i._id = %s._id AND i.name_zh IS NOT NULL AND i.name_zh != ''
    )""" % (table, table)).rowcount if False else None
    cur.execute("""UPDATE %s SET name_zh = (
        SELECT i.name_zh FROM items i WHERE i._id = %s._id
    ) WHERE EXISTS (SELECT 1 FROM items i WHERE i._id = %s._id AND i.name_zh IS NOT NULL AND i.name_zh != '')""" % (table, table, table))
    n = cur.rowcount
    print("  %s.name_zh 从 items 复制: %d 行" % (table, n))

con.commit()

# 验证
print("\n== 验证 ==")
for r in cur.execute("SELECT _id, name, name_ja, name_zh FROM decorations LIMIT 5"):
    print("  deco", r)
for r in cur.execute("SELECT _id, name, name_ja, name_zh FROM cuffs LIMIT 3"):
    print("  cuff", r)
for r in cur.execute("SELECT _id, name, name_ja, name_zh FROM locations LIMIT 3"):
    print("  loc ", r)
con.close()

# 更新 pipeline zip + assets
with zipfile.ZipFile(OUT + ".zip", "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(OUT, "database.db")
shutil.copy2(OUT, SRC)
shutil.copy2(OUT + ".zip", r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip")
print("\nassets 已更新")
