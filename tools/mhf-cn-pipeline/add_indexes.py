# -*- coding: utf-8 -*-
"""给主表加常用查询索引（详情页 JOIN / WHERE 列），减少全表扫描。"""
import os
import shutil
import sqlite3
import zipfile

ASSETS_DB = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db"
ASSETS_ZIP = r"D:\repos\MHFZZDatabase\app\src\main\assets\databases\database.db.zip"
BASE = os.path.dirname(os.path.abspath(__file__))
CN_DB = os.path.join(BASE, "database_cn.db")
CN_ZIP = os.path.join(BASE, "database_cn.db.zip")

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_items_item_hid ON items(item_hid)",
    "CREATE INDEX IF NOT EXISTS idx_components_created ON components(created_item_id)",
    "CREATE INDEX IF NOT EXISTS idx_components_component ON components(component_item_id)",
    "CREATE INDEX IF NOT EXISTS idx_its_item ON item_to_skill_tree(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_its_tree ON item_to_skill_tree(skill_tree_id)",
    "CREATE INDEX IF NOT EXISTS idx_quest_rewards_quest ON quest_rewards(quest_id)",
    "CREATE INDEX IF NOT EXISTS idx_quest_rewards_item ON quest_rewards(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_gathering_item ON gathering(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_hunting_rewards_item ON hunting_rewards(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_hunting_rewards_monster ON hunting_rewards(monster_id)",
    "CREATE INDEX IF NOT EXISTS idx_monster_damage_monster ON monster_damage(monster_id)",
    "CREATE INDEX IF NOT EXISTS idx_monster_to_quest_monster ON monster_to_quest(monster_id)",
    "CREATE INDEX IF NOT EXISTS idx_monster_to_quest_quest ON monster_to_quest(quest_id)",
    "CREATE INDEX IF NOT EXISTS idx_armor_upgrade_item ON armor_upgrade(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_quests_hub_stars ON quests(hub, stars)",
    "CREATE INDEX IF NOT EXISTS idx_weapons_wtype ON weapons(wtype)",
    "CREATE INDEX IF NOT EXISTS idx_monster_habitat_monster ON monster_habitat(monster_id)",
]

con = sqlite3.connect(ASSETS_DB)
cur = con.cursor()
for sql in INDEXES:
    try:
        cur.execute(sql)
        print("OK:", sql.split(" ON ")[1])
    except sqlite3.OperationalError as e:
        print("SKIP:", sql, "->", e)
con.commit()
print()
print("=== indexes now ===")
for r in cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"):
    print(" ", r[0])
con.close()

shutil.copy2(ASSETS_DB, CN_DB)
for zpath in (ASSETS_ZIP, CN_ZIP):
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(CN_DB, "database.db")
    print("rezipped:", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1048576))
