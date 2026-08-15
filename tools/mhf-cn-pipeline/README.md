# MHFZ 中文化管线（物品系）

把游戏汉化版文本灌入 `database.db`，为 App 增加中文显示支持。

## 数据源

| 源 | 内容 |
|----|------|
| `D:\Games\PC\MHF\dat\*.bin`（汉化版） | 中文文本（经 FrontierTextHandler 解析） |
| `D:\repos\FrontierTextHandler` | 解析引擎（ECD 解密 + JKR 解压 + headers.json 指针表） |
| `database.db` | App 数据库（英文 name + 日文 name_ja） |

## 对齐规则（已验证）

```
物品名表索引 = 游戏物品 ID = int(item_hid, 16)     ← 注意：不是 ID-1！
item_hid 格式:
  4 字符纯数字 hex（'0007'）  → 普通物品，走本管线
  5 字符前缀（'h0001'/'b2693'）→ 防具（h=頭/b=体/a=腕/w=腰/l=脚），后续批次
  空                            → 跳过（dummy/活动物品）
```

- 物品描述表前 24 条是 UI 消息，描述从索引 24 开始（`index_shift=24`）
- 游戏内未命名物品在文本区是自引用占位（如 `1F`），对齐时跳过

## 运行

```bash
cd tools/mhf-cn-pipeline
python extract.py       # 提取中文三表（名/描述/来源）→ cache/items_zh.json
python align_items.py   # 对齐 + 建库 → database_cn.db / database_cn.db.zip
```

align_items.py 已把新库复制到 `app/src/main/assets/databases/`（database.db + zip）。

## App 侧改动（已完成）

| 文件 | 改动 |
|------|------|
| `MonsterHunterDatabaseHelper.kt` | `DATABASE_VERSION` 14 → 15（触发老用户强制覆盖复制） |
| `DataManager.kt` | `getLanguages()` 加 `"zh"`（设置界面语言选项） |
| `AppSettings.kt` | `appLanguages` + `allLanguages` 加 `"zh"`（系统语言自动匹配） |

`localizeColumn()` 是通用逻辑：locale=zh → `name_zh` 列，无需改查询代码。
`init { setForcedUpgrade() }` 已就位：版本 14→15 后老用户启动时强制用新 assets 库覆盖。

## 发布流程

1. 重新构建 APK（新 database.db 已入 assets）
2. 用户安装后：老用户自动覆盖数据库（15 > 14），新用户直接复制
3. App 设置 → 数据语言 → 选择"中文"（或系统语言设为中文自动生效）

## 覆盖率（物品系）

- items 表：15,679 个普通物品行 **100%** 覆盖（name_zh/description_zh）
- source_zh：15,505（99%）
- 防具行（63,216）+ 空 hid（24,839）本批次不动

## 后续批次

- 防具（h/b/a/w/l 前缀 → 防具名表，系列+部位对齐）
- 武器（weapon_parent → 武器名表）
- 任务/怪物/技能（ja↔zh 语料匹配）
- 其他小表（locations/horn_melodies/shop_list 等）
