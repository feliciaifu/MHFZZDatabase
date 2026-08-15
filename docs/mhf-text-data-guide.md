# MHFZ 文本数据提取指南

> 本文档记录 MHFZ（Monster Hunter Frontier Z）游戏中所有文本数据（物品、防具、武器、怪物、任务、事件等）的存放位置与提取方法，供中文化数据库开发使用。
>
> 核心结论：**游戏内的日文原文与中文译文都以 Shift-JIS 编码存放在固定布局的文本区中，按游戏 ID 顺序排列；数据库数据（如 MHFZZDatabase 的 database.db）通过游戏 ID 与之对应，而不是通过文本匹配。**

---

## 1. 数据源总览

MHFZ 的文本数据分布在三个地方：

| 数据源 | 路径 | 内容 | 语言 |
|--------|------|------|------|
| **汉化工具数据** | `D:\Games\PC\MHF\MHF External tool 5.41_axibug_α\` | 游戏文本区的完整替换文件 | 繁体中文（Shift-JIS 编码） |
| **游戏目录** | `D:\Games\PC\MHF\dat\` | 游戏原始数据文件（ECD 加密） | 已被汉化补丁改写成中文；日文原文仅存在于 `ja/` 目录部分文件 |
| **Erupe 私服仓库** | `D:\repos\Erupe\` | 解密工具链、逆向成果、任务数据 | 工具 + 数据 |

> ⚠️ 注意：当前游戏目录**已打汉化补丁**，`mhfdat_dec.bin` 等解密产物中的文本已是中文。游戏内的日文原文（物品名表等）只存在于旧版游戏文件或 `ja/` 目录中，**DB 的 `name_ja` 列是日文名称的最佳来源**。

---

## 2. 汉化工具的架构（理解文件结构的前提）

`MHF External tool 5.41_axibug_α` 是一个易语言写的内存补丁汉化工具：

- 游戏启动后，工具按 `dat.ini` 中记录的**内存地址**（如 `pos=004491EC.5B4609C.BE0`）把 `zh/` 目录下的文件内容写入游戏内存，替换原始文本。
- 每个文本区文件的大小 = 游戏原始文本区的大小（`dat.ini` 的 `offsets/size` 字段）。
- 因此 **`zh/*.bin` 是游戏文本区按原始偏移布局的完整替换**：字符串之间用 `0x00` 分隔，编码为 **Shift-JIS**（因此繁体中文中只使用 Shift-JIS 字符集内的汉字）。

### 2.1 目录结构

```
MHF External tool 5.41_axibug_α/
├── dat.ini          # 文本区 → 内存地址映射（offsets/size/pos）
├── ja/              # 日文原文（quests/load/stage/shards 有 ja 版本）
│   ├── quests.bin   # 任务文本（5116 条，与 zh 一一对应）
│   ├── load/*.bin   # 事件文本（129 个文件）
│   ├── stage/*.bin  # 地图文本（38 个文件）
│   └── shards/*.bin # 带地址的字符串片段（mhfdat/mhfo/mhfo-hd/mhfpac）
├── zh/              # 中文译文（核心数据源）
│   ├── mhfdat.bin   # 3.3MB 物品/装备/武器名表 + 描述（最重要）
│   ├── mhfpac.bin   # 1.2MB 角色/UI/对话文本
│   ├── mhfinf.bin   # 434KB 信息文本
│   ├── mhfgao.bin   # 41KB 技能/状态/采集点/猫防具名
│   ├── mhfsqd.bin   # 技能/公会文本
│   ├── mhfjmp.bin   # 跳转/小文本
│   ├── mhfrcc.bin   # 稀有度文本
│   ├── quests.bin   # 任务文本（5116 条）
│   ├── load/*.bin   # 事件文本（129 个）
│   ├── stage/*.bin  # 地图文本（38 个）
│   └── shards/*.bin # 带地址的字符串片段（部分已翻译）
└── ptr/             # 32 位偏移表（对应 zh 文件的字符串边界）
```

### 2.2 文件格式（统一规则）

```
格式：连续 Shift-JIS 字符串，0x00 结尾，无文件头
条目：按文件内的顺序排列（顺序即游戏 ID 顺序）
```

- 编码：**Shift-JIS**（代码页 932）。解码示例：
  - PowerShell: `[System.Text.Encoding]::GetEncoding(932)`
  - Go: `erupe/common/stringsupport.SJISToUTF8()`
  - Python: `bytes.decode('shift_jis')`
- 分隔符：`0x00`
- 例外：`zh/shards/*.bin` 每条 = 3 字节小端地址 + `0x01` 标志 + Shift-JIS 文本 + `0x00`
- 例外：`ptr/*.bin` = 4 字节小端偏移值数组（每个字符串的结束偏移），无文本

---

## 3. 各数据类型：从哪个文件找、怎么找

### 3.1 物品名（items）—— ✅ 已验证，ID 精确映射

| 项 | 值 |
|----|----|
| 文件 | `zh/mhfdat.bin` |
| 名字表起始 | bytePos **2177907**（定位锚点：`調合書１入門篇`） |
| 条目数 | **16478 条**（表索引 = 游戏物品 ID - 1） |
| 结束 | `懷舊硬幣(200)` |

**定位方法**：
1. 在文件中找到 `調合書１入門篇`（Shift-JIS 字节 `92 4F 93 81 8F 6F 82 50 ...`）的字节位置。
2. 从该位置向后按 `0x00` 切分，收集短条目（字节长度 ≤ 40）即得名字表。
3. 表索引 `i` 对应**游戏物品 ID = i + 1**。

**与数据库的对应**（MHFZZDatabase `database.db`）：
- `items.item_hid` = 游戏物品 ID 的**十六进制字符串**（`0001` = ID 1 = 調合書①入門編）
- 例：`回復薬` → `0007` → ID 7 → 表索引 6 → `回復藥`
- 例：`爆薬` → `0020` → ID 32 → 表索引 31 → `爆藥`
- 中文名 = 表[hexToDec(item_hid) - 1]

**已验证的对应关系**（前 8 项全部正确）：

| 游戏 ID | DB `item_hid` | DB `name_ja` | zh 名字表 |
|---------|---------------|--------------|-----------|
| 1 | 0001 | 調合書①入門編 | 調合書１入門篇 |
| 2 | 0002 | 調合書②初級編 | 調合書２初級篇 |
| 7 | 0007 | 回復薬 | 回復藥 |
| 8 | 0008 | 回復薬グレート | 回復藥・大 |
| 11 | 000B | 解毒薬 | 解毒藥 |
| 32 | 0020 | 爆薬 | 爆藥 |
| 33 | 0021 | 生命の粉 | 生命之粉 |
| 34 | 0022 | 生命の粉塵 | 生命粉塵 |

> 注：`items` 表中 `item_hid` 为空的行（如 dummy 物品）和 `hXXXX` 格式的行（防具条目）不适用此表。

### 3.2 防具名（armor）—— ✅ 表已定位

| 项 | 值 |
|----|----|
| 文件 | `zh/mhfdat.bin` |
| 名字表起始 | bytePos **221641**（定位锚点：`綠色護脚`） |
| 条目数 | **85069 条** |

**定位方法**：找到 `紅帽鞋子`（bytePos 260098）后向前回溯到表起点（连续短条目段的开头，221641）。表内顺序为游戏防具 ID 顺序：**先脚（護脚/脛甲/護腿）后头**，每系列每部位男女 2 件。

**已验证的对应关系**：

| zh 表条目 | 对应系列 |
|-----------|----------|
| 綠色護脚 / 青色護脚 | レザーライト / チェーン |
| 獵人護腿 / 獵人脛甲 | ハンター |
| 骨製護腿 / 骨製脛甲 | ボーン |
| 迅猛龍護腿 / 迅猛龍脛甲 | ランポス |
| 戰鬥護腿 / 戰鬥脛甲 | バトル |

**对齐方法**：DB `armor` 表（`name_ja` + `slot` + `family`）按系列顺序与 zh 表按系列+部位（Legs→Waist→Arms→Body→Head）× 男女 对齐。DB 防具无 hid 列，需程序化对齐（系列名匹配 + slot 映射）。

> DB `items` 表中 `item_hid` 为 `hXXXX` 格式（十六进制防具 ID）的行也是防具（如 `h0001` = レザーライトヘルム），可用于交叉验证。

### 3.3 武器名 —— ✅ 表已定位

| 项 | 值 |
|----|----|
| 文件 | `zh/mhfdat.bin` |
| 名字表起始 | bytePos **1142878**（定位锚点：`天噬弓逐光飛翼・極`） |
| 条目数 | ≥17987（武器名连续段） |

**定位方法**：找到 `天噬弓逐光飛翼・極` 即表起点。表内为武器名（弓/大剣/槍/鎚/笛...）。

### 3.4 物品/装备描述文本 —— ✅ 已验证

| 项 | 值 |
|----|----|
| 文件 | `zh/mhfdat.bin` |
| 位置 | 文件开头区域（bytePos 0 起，约 0-215703 为防具描述区） |

- 描述文本为**多行碎片**（如 `使用輕巧素材製成的頭裝備。` 按行拆分），条目按游戏数据顺序排列。
- 物品描述中**内嵌物品名**（如 `内有回復藥的壺` ），可作为物品名交叉验证来源。
- Erupe 已产出分类产物：`D:\repos\Erupe\descriptions_merged\`（按部位合并的描述）。

### 3.5 任务文本（quests）—— ✅ 日中文一一配对

| 项 | 值 |
|----|----|
| 日文原文 | `ja/quests.bin`（436KB） |
| 中文译文 | `zh/quests.bin`（331KB） |
| 条目数 | **5116 = 5116，按序一一对应** |

**配对方法**：两个文件都按 `0x00` 切分，索引 `i` 的日文条目 ↔ 中文条目。例：

```
ja[0]: 師匠から急な命令があってね。一人前の剥ぎ取り職人なら、...
zh[0]: 從師傅那接到緊急的命令，說要成為能獨當一面剥取的專家的話，...
```

**与数据库的对应**：DB `quests.name_ja`/`goal_ja`/`header_ja` 在 ja 条目中做子串匹配（命中率：任务名 34%，任务目标 61%），命中后取同索引 zh 条目。

### 3.6 事件文本（load/）与地图文本（stage/）

| 项 | 值 |
|----|----|
| 日文原文 | `ja/load/*.bin`（129 个）、`ja/stage/*.bin`（38 个） |
| 中文译文 | `zh/load/*.bin`、`zh/stage/*.bin` |
| 对齐 | **近似对齐**：zh 条目数通常比 ja 多几个（00 切分差异），需序列对齐（最长公共子序列/LCS）处理 |

### 3.7 技能/状态/采集点/猫防具（mhfgao.bin）

| 项 | 值 |
|----|----|
| 文件 | `zh/mhfgao.bin`（41KB） |
| 内容 | 短条目块：状态名（`睡眠/麻痺/氣絶`）、采集点（`折斷的樹木/小小樹木/大河`）、猫防具名（`橡實猫鎧甲/雌火龍猫鎧甲`）等 |
| 注意 | 部分内容未翻译（含日文原文），如武器描述区 |

### 3.8 怪物名（monsters）

- **DB `monsters.name_ja` 是日文名的权威来源**（185 个怪物）。
- 中文名提取：在 `ja/quests.bin` + `ja/load/*` + `ja/stage/*` 语料中定位日文名（命中率 83%），取同索引 zh 条目中的对应中文名（怪物名在任务文本中通常成对出现）。
- 怪物 ID → 名称枚举另见 Erupe `common/mhfmon/mhfmon.go`。

---

## 4. 游戏原始数据文件（结构化数据）

| 文件 | 加密 | 内部格式 | 说明 |
|------|------|----------|------|
| `dat/mhfdat.bin`（6MB） | ECD (`ecd\x1a`) + JPK | `mhf\x1a`, version 0x59, **3016 条目** | 主游戏数据 |
| `dat/mhfdat_dec.bin`（26MB） | 已解密 | 同上 | 当前是汉化后的中文 |
| `dat/mhfpac.bin`（623KB） | ECD + JPK | `pac\x1a`, version 10, ~14K 条目 | 角色/装备表 |
| `dat/mhfinf.bin`（351KB） | ECD + JPK | `inf\x1a`, version 6 | 信息表 |
| `dat/*.txb`（18 个） | 部分 ECD | u32 条目数 + u32 头部大小 + 8B/条目 | UI/纹理批次 |
| `dat/extracted_*.bin` | - | 纯文本区（已被汉化） | 工具提取的文本段 |

**解密工具**（Erupe，Go）：
```bash
cd D:\repos\Erupe
gamedata.exe decrypt <file>                    # ECD 解密 + JPK 解压 → stdout
gamedata.exe extract <game-dir> <out-dir>      # 自动解密全部文件
gamedata.exe parse-mhfdat <mhfdat.bin>         # 解析 mhf\x1a 索引结构
gamedata.exe parse-mhfpac <mhfpac.bin>         # 解析 pac\x1a 结构
gamedata.exe extract-all-text <dec.bin> <out.tsv>  # 全量文本导出
```

- Go 源码：`D:\repos\Erupe\common\decryption\ecd.go`（ECD）、`jpk.go`（JPK LZ）、`common\stringsupport\`（Shift-JIS）
- **Erupe 根目录已有产物**：`extracted_texts.tsv`（81K 条文本偏移索引）、`entry9_full.csv`（9600 行装备记录）、`mhfpac_dec.bin`、`export_mhfpac_bin/`（70+ 张表 CSV）、`text_regions.txt`、`table_dump.txt`
- mhfdat_dec.bin 结构逆向（Ghidra 反汇编 mhfo-hd.dll）：0x48 字节固定条目、0xFFFF 终止、372+ 张表。详见 `D:\repos\Erupe\docs\mhf-data-browser-plan.md`

---

## 5. 文本匹配的字符规范化

日文名 ↔ 中文名/繁体匹配时需要规范化（否则 `調合書①入門編` 匹配不上 `調合書１入門篇`）：

| 类型 | 转换 |
|------|------|
| 圈号数字 | ①→1, ②→2 ... ⑩→0 |
| 全角字符 | １→1, Ａ→A（全角 ASCII → 半角） |
| 半角片假名 | ﾌ→フ（含浊音组合 ｶﾞ→ガ） |
| 日文新字体→繁体 | 竜→龍, 沢→澤, 剣→劍, 気→氣, 薬→藥, 編→篇, 錬→煉, 猟→獵 ...（约 200 组） |

**匹配策略**（已验证命中率）：
- 汉字型名称：规范化后直接子串匹配（技能树 87%、技能 75%）
- 假名型名称：靠语料定位 + 配对索引提取（怪物 83%）
- 物品/防具：**不要用文本匹配，用 ID 对齐**（见 3.1/3.2）

---

## 6. 中文化数据管线（推荐流程）

```
┌─────────────────────────────────────────────────────────┐
│ 1. 解析 zh/mhfdat.bin                                     │
│    ├─ 物品名表 @2177907 (16478条)  ← items.item_hid 对齐   │
│    ├─ 防具名表 @221641  (85069条)  ← 系列+slot 对齐        │
│    ├─ 武器名表 @1142878 (17987+条) ← 武器 ID 对齐          │
│    └─ 描述碎片区 @0 起              ← 按位置/条目配对       │
│ 2. 解析 zh/quests.bin + ja/quests.bin 配对 (5116对)        │
│ 3. 解析 zh/load|stage + ja/load|stage 配对 (LCS 对齐)      │
│ 4. 解析 zh/mhfgao.bin (技能/状态/采集点)                    │
│ 5. 规范化匹配：DB name_ja → 中文名                         │
│ 6. 生成 name_zh/description_zh 列 → 重新打包 database.db   │
└─────────────────────────────────────────────────────────┘
```

---

## 7. 参考工具与资料

| 资料 | 路径 | 用途 |
|------|------|------|
| Erupe 数据工具 | `D:\repos\Erupe\cmd\gamedata\` | 解密/提取 CLI（gamedata.exe 已编译） |
| Erupe 解密库 | `D:\repos\Erupe\common\decryption\` | ECD/JPK 的 Go 实现 |
| Erupe 字符串库 | `D:\repos\Erupe\common\stringsupport\` | Shift-JIS ↔ UTF-8 |
| Erupe 任务解析 | `D:\repos\Erupe\server\channelserver\quest_json_parser.go` | 任务 .bin → JSON |
| Erupe 任务文件 | `D:\repos\Erupe\bin\quests\` | 1000+ 个任务二进制 |
| Erupe 浏览器方案 | `D:\repos\Erupe\docs\mhf-data-browser-plan.md` | 数据浏览器架构设计 |
| Erupe 怪物表 | `D:\repos\Erupe\common\mhfmon\mhfmon.go` | 怪物 ID → 名称 |
| 汉化工具 dat.ini | `MHF External tool 5.41_axibug_α\dat.ini` | 文本区偏移/内存地址映射 |
| mhf-launcher | `D:\repos\mhf-launcher\` | 启动器（无解包代码，仅补丁分发） |
| mhf-iel | `C:\Users\suiyi\RustroverProjects\mhf-iel\` | 游戏内存结构（DataZZ/GlobalData） |
