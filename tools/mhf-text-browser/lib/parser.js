'use strict';
// MHFZ 文本数据浏览器 - 解析库（Node 侧）
const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// 配置
// ---------------------------------------------------------------------------
const TOOL_DIR = 'D:\\Games\\PC\\MHF\\MHF External tool 5.41_axibug_α';
const GAME_DIR = 'D:\\Games\\PC\\MHF';

// 已知名字表（位置来自 docs/mhf-text-data-guide.md 逆向验证）
// [文件, 起始字节偏移, 表名, 说明, ID基址偏移]
const KNOWN_TABLES = [
  ['zh/mhfdat.bin', 2177907, '物品名表', '索引 = 游戏物品ID - 1（item_hid 为 ID 的十六进制）', 1],
  ['zh/mhfdat.bin', 221641, '防具名表', '游戏防具ID顺序：每系列先脚后头，每部位男女2件', 1],
  ['zh/mhfdat.bin', 1142878, '武器名表', '游戏武器ID顺序', 1],
  ['zh/mhfdat.bin', 0, '装备描述区', '头部装备描述碎片（00分隔）', null],
  ['zh/quests.bin', 0, '任务文本(zh)', '与 ja/quests.bin 按序一一对应（5116条）', null],
  ['ja/quests.bin', 0, '任务文本(ja)', '日文原文，索引与 zh/quests.bin 对应', null],
];

// 已知配对（ja 原文 ↔ zh 译文）
const KNOWN_PAIRS = [
  ['ja/quests.bin', 'zh/quests.bin', '任务文本配对', '5116 条一一对应（已验证）'],
  ['ja/shards/mhfdat.bin', 'zh/shards/mhfdat.bin', 'mhfdat 片段配对', '2332 条，带内存地址'],
  ['ja/shards/mhfpac.bin', 'zh/shards/mhfpac.bin', 'mhfpac 片段配对', '10 条，带内存地址'],
  ['ja/load/uc00_000_00.bin', 'zh/load/uc00_000_00.bin', '事件文本配对', '近似对齐（条目数略有差异，需 LCS）'],
];

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------
const sjisDecoder = new TextDecoder('shift_jis');

function decodeSJIS(buf) {
  return sjisDecoder.decode(buf);
}

function resolvePath(rel) {
  rel = rel.replace(/\\/g, '/');
  if (rel.startsWith('GAME/')) return path.join(GAME_DIR, rel.slice(5));
  return path.join(TOOL_DIR, rel);
}

// ---------------------------------------------------------------------------
// 文件扫描
// ---------------------------------------------------------------------------
function scanFiles() {
  const groups = [];
  if (fs.existsSync(TOOL_DIR)) {
    for (const sub of ['zh', 'ja', 'ptr']) {
      const d = path.join(TOOL_DIR, sub);
      if (!fs.existsSync(d)) continue;
      const files = [];
      const walk = (dir) => {
        for (const name of fs.readdirSync(dir)) {
          const full = path.join(dir, name);
          const st = fs.statSync(full);
          if (st.isDirectory()) walk(full);
          else if (name.toLowerCase().endsWith('.bin')) {
            files.push({ path: path.relative(TOOL_DIR, full).replace(/\\/g, '/'), size: st.size });
          }
        }
      };
      walk(d);
      files.sort((a, b) => a.path.localeCompare(b.path));
      if (files.length) groups.push({ name: '汉化工具/' + sub, files });
    }
  }
  if (fs.existsSync(GAME_DIR)) {
    const d = path.join(GAME_DIR, 'dat');
    if (fs.existsSync(d)) {
      const files = [];
      for (const name of fs.readdirSync(d)) {
        const full = path.join(d, name);
        if (!fs.statSync(full).isFile()) continue;
        if (/\.(bin|txb)$/i.test(name)) {
          files.push({ path: 'GAME/dat/' + name, size: fs.statSync(full).size });
        }
      }
      files.sort((a, b) => a.path.localeCompare(b.path));
      if (files.length) groups.push({ name: '游戏目录/dat', files });
    }
  }
  return groups;
}

// ---------------------------------------------------------------------------
// 文本区解析
// ---------------------------------------------------------------------------
class TextFile {
  constructor(full) {
    this.full = full;
    this.size = fs.statSync(full).size;
    this._data = null;
  }
  data() {
    if (this._data === null) this._data = fs.readFileSync(this.full);
    return this._data;
  }
  entries() {
    // 按 0x00 切分，返回 [{start,end,len,text}]
    if (this._entries) return this._entries;
    const data = this.data();
    const out = [];
    let start = 0;
    for (let i = 0; i < data.length; i++) {
      if (data[i] === 0) {
        const ln = i - start;
        if (ln > 0) out.push({ start, end: i, len: ln, text: decodeSJIS(data.slice(start, i)) });
        start = i + 1;
      }
    }
    if (data.length - start > 0) out.push({ start, end: data.length, len: data.length - start, text: decodeSJIS(data.slice(start)) });
    this._entries = out;
    return out;
  }
}

const fileCache = new Map();
function getTextFile(rel) {
  const full = resolvePath(rel);
  let tf = fileCache.get(full);
  if (!tf) {
    tf = new TextFile(full);
    fileCache.set(full, tf);
    if (fileCache.size > 20) {
      const first = fileCache.keys().next().value;
      fileCache.delete(first);
    }
  }
  return tf;
}

function tableEntries(rel, fromPos, maxLen = 40) {
  const data = getTextFile(rel).data();
  const out = [];
  let p = fromPos;
  const n = data.length;
  while (p < n) {
    let end = p;
    while (end < n - 1 && data[end] !== 0) end++;
    const ln = end - p;
    if (ln <= 0 || ln > maxLen) break;
    const text = decodeSJIS(data.slice(p, end));
    if (text.length < 2) break;
    out.push({ start: p, end, len: ln, text });
    p = end + 1;
  }
  return out;
}

function hexdump(data, pos) {
  const lines = [];
  for (let off = 0; off < data.length; off += 16) {
    const chunk = data.slice(off, off + 16);
    const hexs = Array.from(chunk, (c) => c.toString(16).padStart(2, '0').toUpperCase()).join(' ');
    const asc = Array.from(chunk, (c) => (c >= 32 && c <= 126 ? String.fromCharCode(c) : '.')).join('');
    lines.push(`${(pos + off).toString(16).padStart(8, '0')}  ${hexs.padEnd(47)}  ${asc}`);
  }
  return lines;
}

module.exports = {
  TOOL_DIR, GAME_DIR, KNOWN_TABLES, KNOWN_PAIRS,
  decodeSJIS, resolvePath, scanFiles, getTextFile, tableEntries, hexdump,
};
