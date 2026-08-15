# -*- coding: utf-8 -*-
"""Add labelText string keys + replace hardcoded labels in armor detail layout."""
import os
import re

ADD = [
    ("ui_improve", "Improve", "强化"),
    ("ui_improve_2", "Improve 2", "强化2"),
    ("ui_improve_3", "Improve 3", "强化3"),
    ("ui_improve_4", "Improve 4", "强化4"),
    ("ui_improve_5", "Improve 5", "强化5"),
    ("ui_improve_6", "Improve 6", "强化6"),
    ("ui_improve_7", "Improve 7", "强化7"),
    ("ui_improve_8", "Improve 8", "强化8"),
    ("ui_upgrades_to", "Upgrades To", "升级为"),
    ("ui_upgrades_from", "Upgrades From", "由…升级"),
]
for path, lang in ((r"app/src/main/res/values/strings.xml", 0),
                   (r"app/src/main/res/values-zh/strings.xml", 1)):
    c = open(path, encoding="utf-8").read()
    existing = set(re.findall(r'name="([^"]+)"', c))
    for key, en, zh in ADD:
        if key in existing:
            continue
        val = zh if lang == 1 else en
        c = c.rstrip()
        c = c[: -len("</resources>")] + ('    <string name="%s">%s</string>\n</resources>\n'
                                         % (key, val))
    open(path, "w", encoding="utf-8").write(c)

REPL = {
    "Improve 2": "ui_improve_2", "Improve 3": "ui_improve_3", "Improve 4": "ui_improve_4",
    "Improve 5": "ui_improve_5", "Improve 6": "ui_improve_6", "Improve 7": "ui_improve_7",
    "Improve 8": "ui_improve_8",
}
p = r"app/src/main/res/layout/fragment_armor_detail.xml"
c = open(p, encoding="utf-8").read()
for en, key in REPL.items():
    c = c.replace('app:labelText="%s"' % en, 'app:labelText="@string/%s"' % key)
c = c.replace('app:labelText="Improve"', 'app:labelText="@string/ui_improve"')
c = c.replace('app:labelText="Upgrades To"', 'app:labelText="@string/ui_upgrades_to"')
c = c.replace('app:labelText="Upgrades From"', 'app:labelText="@string/ui_upgrades_from"')
# 演示行 Attack/Defense（gone）
c = c.replace('app:labelText="Attack"', 'app:labelText="@string/ui_attack"')
c = c.replace('app:labelText="Defense"', 'app:labelText="@string/ui_defense"')
open(p, "w", encoding="utf-8").write(c)
print("updated", p)

import xml.dom.minidom as m
m.parse(r"app/src/main/res/values/strings.xml")
m.parse(r"app/src/main/res/values-zh/strings.xml")
print("XML OK")
