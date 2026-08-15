# MHFZ 文本数据浏览器

解包浏览 MHFZ（Monster Hunter Frontier Z）游戏全部文本数据的桌面工具。

技术栈：**Electron + Vue 3 + Element Plus + Vite**（深色主题，组件化界面）。

## 功能

- **文件浏览**：扫描汉化工具目录（`zh/ja/ptr`）与游戏 `dat/` 目录的全部 `.bin/.txb` 文件，按分组展示
- **结构化查看**：按 `0x00` 切分条目，Shift-JIS 解码，`el-table` 分页浏览（索引/偏移/长度/文本）
- **数据表视图（权威解析）**：直接读取游戏 `dat/*.bin` 原始加密文件（ECD 解密 + JKR 解压，引擎 `lib/fth.js` 移植自 [FrontierTextHandler](https://github.com/Houmgaor/FrontierTextHandler)），按 `lib/headers.json` 的指针表布局解析成数据库表：
  - 物品（16,701 行：名字/描述/入手来源，ID=索引+1）、任务（2,839 行 × 8 字段）、技能（232 行）、武器近战/远程、防具（并排 5 部位 + 单部位纵向 68,730 行）、怪物、装备描述、HR 等级、狩猎笛、猫伙伴、公会伙伴、跳转菜单
  - 支持列排序、关键词过滤、行下钻（各字段 + 明文偏移 + Hex）
- **已知名字表**（侧边栏一键直达，位置来自逆向验证）：
  - 物品名表（zh/mhfdat.bin @2177907，**16478 条**，索引 = 游戏物品 ID - 1，`item_hid` 为 ID 十六进制）
  - 防具名表（@221641，85069 条）
  - 武器名表（@1142878）
  - 装备描述区、任务文本
- **ja↔zh 配对视图**：任务文本（**5116 条一一对应**）、shards 片段等，日文原文与中文译文并排对照 + 双 Hex
- **全文搜索**：任意文件内关键词搜索（子串匹配），点击结果跳转并高亮
- **详情面板**：文本 + Hex 双视图

## 使用方法

```bash
cd tools/mhf-text-browser
npm install        # 安装依赖（国内建议先设置镜像，见下）
npm start          # 构建 + 启动
```

开发模式（热更新）：

```bash
npm run dev
```

### 国内镜像加速（可选）

```powershell
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
npm install --registry=https://registry.npmmirror.com
```

## 路径配置

默认路径在 `lib/parser.js` 顶部：

```js
const TOOL_DIR = 'D:\\Games\\PC\\MHF\\MHF External tool 5.41_axibug_α';  // 汉化工具目录
const GAME_DIR = 'D:\\Games\\PC\\MHF';                                   // 游戏目录
```

## 数据格式速查

| 项 | 说明 |
|----|------|
| 编码 | Shift-JIS（cp932），`TextDecoder('shift_jis')` 解码 |
| 分隔 | `0x00` |
| 文本区 | `zh/*.bin` = 游戏文本区完整替换（繁体中文） |
| 名字表 | 按游戏 ID 顺序排列（物品表索引 = item_hid 十六进制值 - 1） |
| 配对 | `ja/quests.bin` ↔ `zh/quests.bin` 按条目索引一一对应（5116 条） |

详细提取指南见 `docs/mhf-text-data-guide.md`。

## 目录结构

```
mhf-text-browser/
├── package.json
├── main.js              # Electron 主进程（窗口 + IPC，含数据表 IPC）
├── preload.js           # 安全桥接（window.mhf API）
├── lib/parser.js        # 解析库（扫描/条目/名字表/配对/Hex）
├── lib/fth.js           # 数据表引擎（ECD/JKR/指针表，移植自 FrontierTextHandler）
├── lib/headers.json     # 指针表布局配置（来自 FrontierTextHandler）
├── scripts/dev.js       # 开发模式（Vite + Electron 联调）
├── renderer/            # Vue 3 + Element Plus 前端
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js      # 入口（Element Plus 深色主题）
│       ├── App.vue      # 布局 + 搜索（数据表模式搜索=表内过滤）
│       ├── store.js     # 全局状态
│       ├── styles.css   # 主题覆盖
│       └── components/
│           ├── Sidebar.vue       # 文件树 + 数据表 + 已知表 + 配对
│           ├── EntriesPanel.vue  # 条目表格 + 分页 + 搜索结果（数据表动态列/排序）
│           └── DetailPanel.vue   # 文本 + Hex 详情（含数据表行详情）
└── server.py            # （备用）旧版 Python http 后端，不使用可删除
```
