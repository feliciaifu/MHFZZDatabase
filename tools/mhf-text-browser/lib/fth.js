'use strict';
// MHFZ 数据表引擎（Node 版）
// 移植自 FrontierTextHandler (https://github.com/Houmgaor/FrontierTextHandler)，
// 支持：ECD/EXF 解密 → JKR/JPK 解压 → headers.json 指针表布局提取 → 数据表构建。
const fs = require('fs');
const path = require('path');

const GAME_DAT = 'D:\\Games\\PC\\MHF\\dat';
const HEADERS_PATH = path.join(__dirname, 'headers.json');
const HEADERS = JSON.parse(fs.readFileSync(HEADERS_PATH, 'utf-8'));

// ===========================================================================
// ECD / EXF 解密（移植 crypto.py）
// ===========================================================================
const ECD_MAGIC = 0x1a646365;
const EXF_MAGIC = 0x1a667865;

const RND_BUF_ECD = Buffer.from([
  0x4a, 0x4b, 0x52, 0x2e, 0x00, 0x00, 0x00, 0x01, // Key 0
  0x00, 0x01, 0x0d, 0xcd, 0x00, 0x00, 0x00, 0x01, // Key 1
  0x00, 0x01, 0x0d, 0xcd, 0x00, 0x00, 0x00, 0x01, // Key 2
  0x00, 0x01, 0x0d, 0xcd, 0x00, 0x00, 0x00, 0x01, // Key 3
  0x00, 0x19, 0x66, 0x0d, 0x00, 0x00, 0x00, 0x03, // Key 4 (default)
  0x7d, 0x2b, 0x89, 0xdd, 0x00, 0x00, 0x00, 0x01, // Key 5
]);

const RND_BUF_EXF = Buffer.from([
  0x4a, 0x4b, 0x52, 0x2e, 0x00, 0x00, 0x00, 0x01,
  0x00, 0x01, 0x0d, 0xcd, 0x00, 0x00, 0x00, 0x01,
  0x00, 0x01, 0x0d, 0xcd, 0x00, 0x00, 0x00, 0x01,
  0x00, 0x01, 0x0d, 0xcd, 0x00, 0x00, 0x00, 0x01,
  0x02, 0xe9, 0x0e, 0xdd, 0x00, 0x00, 0x00, 0x03, // Key 4
]);

function loadU32BE(buf, off) {
  return ((buf[off] << 24) | (buf[off + 1] << 16) | (buf[off + 2] << 8) | buf[off + 3]) >>> 0;
}

function getRndEcd(key, rnd) {
  const m = loadU32BE(RND_BUF_ECD, 8 * key);
  const inc = loadU32BE(RND_BUF_ECD, 8 * key + 4);
  rnd = ((rnd * m + inc) & 0xffffffff) >>> 0;
  return [rnd, rnd];
}

function decodeEcd(data) {
  if (data.length < 16) throw new Error('ECD buffer too small');
  const ecdKey = data.readUInt16LE(4);
  const payloadSize = data.readUInt32LE(8);
  const crc32 = data.readUInt32LE(12);
  if (ecdKey > 5) throw new Error('Invalid ECD key index: ' + ecdKey);
  if (data.length < 16 + payloadSize) throw new Error('ECD data truncated');
  let rnd = (((crc32 << 16) | (crc32 >>> 16) | 1) & 0xffffffff) >>> 0;
  let xorpad;
  [rnd, xorpad] = getRndEcd(ecdKey, rnd);
  let r8 = xorpad & 0xff;
  const out = Buffer.alloc(payloadSize);
  for (let i = 0; i < payloadSize; i++) {
    [rnd, xorpad] = getRndEcd(ecdKey, rnd);
    const enc = data[16 + i];
    let r11 = enc ^ r8;
    let r12 = (r11 >>> 4) & 0xff;
    for (let k = 0; k < 8; k++) {
      const r10 = (xorpad ^ r11) & 0xff;
      r11 = r12;
      r12 = (r12 ^ r10) & 0xff;
      xorpad = (xorpad >>> 4) >>> 0;
    }
    r8 = (r12 & 0xf) | ((r11 & 0xf) << 4);
    out[i] = r8;
  }
  return out;
}

function createXorKeyExf(header) {
  const keyBuf = Buffer.alloc(16);
  const index = header.readUInt16LE(4);
  const value = header.readUInt32LE(12);
  let temp = value;
  for (let i = 0; i < 4; i++) {
    const m = loadU32BE(RND_BUF_EXF, index * 8);
    const inc = loadU32BE(RND_BUF_EXF, index * 8 + 4);
    temp = ((temp * m + inc) & 0xffffffff) >>> 0;
    const key = (temp ^ value) >>> 0;
    keyBuf.writeUInt32LE(key, i * 4);
  }
  return keyBuf;
}

function decodeExf(data) {
  if (data.length < 16) throw new Error('EXF buffer too small');
  const header = data.slice(0, 16);
  const keybuf = createXorKeyExf(header);
  const out = Buffer.alloc(data.length - 16);
  for (let i = 16; i < data.length; i++) {
    const r28 = i - 16;
    const r8 = data[i];
    const index = r28 & 0xf;
    const r4 = (r8 ^ r28) & 0xff;
    const r12 = keybuf[index];
    const r0 = (r4 & 0xf0) >> 4;
    const r7 = keybuf[r0];
    const r9 = ((r4 >> 4) ^ r12) & 0xff; // r9 ^= r12
    const r5 = r7 >> 4;
    const r26low = (r5 ^ r4) & 0x0f;     // (r26 & ~0xF0) 保留低半字节
    const r26 = r26low | ((r9 & 0x0f) << 4);
    out[r28] = r26 & 0xff;
  }
  return out;
}

function isEcdFile(data) { return data.length >= 4 && data.readUInt32LE(0) === ECD_MAGIC; }
function isExfFile(data) { return data.length >= 4 && data.readUInt32LE(0) === EXF_MAGIC; }
function isEncrypted(data) { return isEcdFile(data) || isExfFile(data); }

function decrypt(data) {
  if (isEcdFile(data)) return decodeEcd(data);
  if (isExfFile(data)) return decodeExf(data);
  throw new Error('Data is not an ECD or EXF encrypted file');
}

// ===========================================================================
// JKR / JPK 解压（移植 jkr_decompress.py）
// ===========================================================================
const JKR_MAGIC = 0x1a524b4a;
const HF_LEAF = 0x100;
const HF_BASE = 0x200;
const HF_ADJ = 0x3fc;
const LZ_LEN_MASK = 0xe0;
const LZ_LEN_SHIFT = 5;
const LZ_OFF_HI = 0x1f;
const LZ_BASE_LONG = 0x1a;
const LZ_RUN_BASE = 0x1b;
const LZ_RUN_MARKER = 0xff;

class LZDecoder {
  constructor() { this._shift = 0; this._flag = 0; this._pos = 0; }

  _readByte(data) {
    if (this._pos >= data.length) throw new Error('Reached end of file too early!');
    return data[this._pos++];
  }

  _bit() {
    if (this._shift <= 0) { this._shift = 7; this._flag = this._readByte(this._data); }
    else this._shift -= 1;
    return ((this._flag >>> this._shift) & 1) === 1;
  }

  _copy(out, offset, length, index) {
    for (let i = 0; i < length; i++) out[index + i] = out[index + i - offset - 1];
    return length;
  }

  decode(data, outSize) {
    this._data = data;
    const out = Buffer.alloc(outSize);
    let idx = 0;
    try {
      while (idx < outSize) {
        if (!this._bit()) { out[idx++] = this._readByte(data); continue; }
        if (!this._bit()) {
          // Case 0: short back-reference
          const length = (this._bit() ? 2 : 0) + (this._bit() ? 1 : 0);
          const offset = this._readByte(data);
          idx += this._copy(out, offset, length + 3, idx);
          continue;
        }
        const hi = this._readByte(data);
        const lo = this._readByte(data);
        let length = (hi & LZ_LEN_MASK) >> LZ_LEN_SHIFT;
        const offset = ((hi & LZ_OFF_HI) << 8) | lo;
        if (length !== 0) { idx += this._copy(out, offset, length + 2, idx); continue; }
        if (!this._bit()) {
          length = 0;
          for (let i = 3; i >= 0; i--) if (this._bit()) length += 1 << i;
          idx += this._copy(out, offset, length + 2 + 8, idx);
          continue;
        }
        const temp = this._readByte(data);
        if (temp === LZ_RUN_MARKER) {
          for (let i = 0; i < offset + LZ_RUN_BASE; i++) out[idx++] = this._readByte(data);
          continue;
        }
        idx += this._copy(out, offset, temp + LZ_BASE_LONG, idx);
      }
    } catch (e) { /* EOF: 允许提前结束 */ }
    return out;
  }
}

class HFIDecoder extends LZDecoder {
  constructor() { super(); this._hfFlag = 0; this._hfShift = 0; this._hfOff = 0; this._hfDataOff = 0; this._hfLen = 0; }

  _readByte(data) {
    if (!this._useHf) return super._readByte(data);
    let node = this._hfLen;
    while (node >= HF_LEAF) {
      this._hfShift -= 1;
      if (this._hfShift < 0) {
        this._hfShift = 7;
        this._pos = this._hfDataOff;
        this._hfDataOff += 1;
        if (this._pos >= data.length) throw new Error('EOF in Huffman decode');
        this._hfFlag = data[this._pos];
      }
      const bit = (this._hfFlag >>> this._hfShift) & 1;
      const off = (node * 2 - HF_BASE + bit) * 2 + this._hfOff;
      node = data.readInt16LE(off);
    }
    return node & 0xff;
  }

  decode(data, outSize) {
    this._data = data;
    this._hfLen = data.readInt16LE(0);
    this._pos = 2;
    this._hfOff = this._pos;
    this._hfDataOff = this._pos + this._hfLen * 4 - HF_ADJ;
    this._useHf = true;
    try { return super.decode(data, outSize); } finally { this._useHf = false; }
  }
}

function decompressJkr(data) {
  if (data.length < 16) throw new Error('Data too short for JKR header');
  const magic = data.readUInt32LE(0);
  if (magic !== JKR_MAGIC) throw new Error('Invalid JKR magic bytes');
  const ctype = data.readUInt16LE(6);
  const dataOffset = data.readUInt32LE(8);
  const outSize = data.readUInt32LE(12);
  const body = data.slice(dataOffset);
  let out;
  if (ctype === 0 || ctype === 1) {
    out = Buffer.from(body.slice(0, outSize));
  } else if (ctype === 2) {
    const d = new HFIRWDecoder();
    d._data = data;
    d._hfLen = body.readInt16LE(0);
    d._pos = dataOffset + 2;
    d._hfOff = d._pos;
    d._hfDataOff = d._pos + d._hfLen * 4 - HF_ADJ;
    out = d.decodeHf(data, outSize);
  } else if (ctype === 3) {
    out = new LZDecoder().decode(body, outSize);
  } else if (ctype === 4) {
    out = new HFIDecoder().decode(body, outSize);
  } else {
    throw new Error('Unknown JKR compression type: ' + ctype);
  }
  return out;
}

class HFIRWDecoder {
  constructor() { this._hfFlag = 0; this._hfShift = 0; }

  _readByteHf(data) {
    let node = this._hfLen;
    while (node >= HF_LEAF) {
      this._hfShift -= 1;
      if (this._hfShift < 0) {
        this._hfShift = 7;
        this._pos = this._hfDataOff;
        this._hfDataOff += 1;
        this._hfFlag = data[this._pos];
      }
      const bit = (this._hfFlag >>> this._hfShift) & 1;
      const off = (node * 2 - HF_BASE + bit) * 2 + this._hfOff;
      node = data.readInt16LE(off);
    }
    return node & 0xff;
  }

  decodeHf(data, outSize) {
    const out = Buffer.alloc(outSize);
    for (let i = 0; i < outSize; i++) out[i] = this._readByteHf(data);
    return out;
  }
}

function isJkrFile(data) { return data.length >= 4 && data.readUInt32LE(0) === JKR_MAGIC; }

// ===========================================================================
// 文件加载：读盘 → ECD 解密 → JKR 解压
// ===========================================================================
const plainCache = new Map(); // file -> { mtime, data }

function loadPlainBytes(fileName) {
  const full = path.join(GAME_DAT, fileName);
  const st = fs.statSync(full);
  const hit = plainCache.get(fileName);
  if (hit && hit.mtime === st.mtimeMs) return hit.data;
  let data = fs.readFileSync(full);
  if (isEncrypted(data)) data = decrypt(data);
  if (isJkrFile(data)) data = decompressJkr(data);
  plainCache.set(fileName, { mtime: st.mtimeMs, data });
  if (plainCache.size > 4) {
    const first = plainCache.keys().next().value;
    plainCache.delete(first);
  }
  return data;
}

// ===========================================================================
// 指针表区段提取（移植 pointer_tables.py 的核心模式）
// ===========================================================================
const JOIN = '{j}';

class Reader {
  constructor(data) { this.data = data; this.pos = 0; }
  seek(p) { this.pos = p; }
  readU8() { return this.data[this.pos++]; }
  readU16() { const v = this.data.readUInt16LE(this.pos); this.pos += 2; return v; }
  readU32() { const v = this.data.readUInt32LE(this.pos); this.pos += 4; return v; }
  readNullTerm() {
    const start = this.pos;
    while (this.pos < this.data.length && this.data[this.pos] !== 0) this.pos++;
    return this.data.slice(start, this.pos);
  }
  validate(off, ctx) {
    if (off < 0 || off >= this.data.length) {
      throw new Error('Pointer offset 0x' + off.toString(16) + ' is outside file bounds (0x0 - 0x' +
        (this.data.length - 1).toString(16) + ')' + (ctx ? ' (' + ctx + ')' : ''));
    }
  }
}

function decodeSJIS(buf) {
  return new TextDecoder('shift_jis').decode(buf);
}

function readFileSection(rd, startPos, length) {
  rd.validate(startPos, 'section start');
  if (length > 0) rd.validate(startPos + length - 1, 'section end');
  rd.seek(startPos);
  const pointers = [];
  for (let i = 0; i < length; i += 4) pointers.push(rd.readU32());
  const joinLines = pointers.includes(0);
  const out = [];
  let curTexts = [];
  let curOffsets = [];
  const flush = () => {
    if (!curTexts.length) return;
    out.push({ offset: curOffsets[0], text: curTexts.join(JOIN), sub_offsets: [...curOffsets] });
    curTexts = [];
    curOffsets = [];
  };
  for (let i = 0; i < pointers.length; i++) {
    const slotOff = startPos + i * 4;
    const ptr = pointers[i];
    if (ptr === 0) { if (joinLines) flush(); continue; }
    rd.validate(ptr, 'string at offset 0x' + ptr.toString(16));
    rd.seek(ptr);
    const raw = rd.readNullTerm();
    const text = decodeSJIS(raw);
    if (joinLines) { curTexts.push(text); curOffsets.push(slotOff); }
    else out.push({ offset: slotOff, text, sub_offsets: [slotOff] });
  }
  flush();
  return out;
}

function readStructStrings(rd, base, count, entrySize, fieldOffsets) {
  const fos = Array.isArray(fieldOffsets) ? fieldOffsets : [fieldOffsets];
  const out = [];
  for (let i = 0; i < count; i++) {
    const entryBase = base + i * entrySize;
    for (const fo of fos) {
      const ptrOff = entryBase + fo;
      rd.validate(ptrOff, 'struct entry ' + i + ' +0x' + fo.toString(16));
      rd.seek(ptrOff);
      const ptr = rd.readU32();
      if (ptr === 0) continue;
      rd.validate(ptr, 'string pointer in entry ' + i + ' +0x' + fo.toString(16));
      rd.seek(ptr);
      out.push({ offset: ptrOff, text: decodeSJIS(rd.readNullTerm()), sub_offsets: [ptrOff] });
    }
  }
  return out;
}

function readQuestTable(rd, categoryTablePtr, numCategories, questTextOffset, textPtrCount) {
  const out = [];
  for (let c = 0; c < numCategories; c++) {
    const catAddr = categoryTablePtr + c * 8;
    rd.validate(catAddr + 7, 'category ' + c);
    rd.seek(catAddr + 2);
    const count = rd.readU16();
    const arrPtr = rd.readU32();
    if (arrPtr === 0 || count === 0) continue;
    rd.validate(arrPtr + count * 4 - 1, 'category ' + c + ' quest array');
    rd.seek(arrPtr);
    const qptrs = [];
    for (let i = 0; i < count; i++) qptrs.push(rd.readU32());
    for (const qp of qptrs) {
      if (qp === 0) continue;
      const tpAddr = qp + questTextOffset;
      rd.validate(tpAddr + 3, 'quest at 0x' + qp.toString(16) + ' text field');
      rd.seek(tpAddr);
      const blockPtr = rd.readU32();
      if (blockPtr === 0) continue;
      rd.validate(blockPtr + textPtrCount * 4 - 1, 'quest text block at 0x' + blockPtr.toString(16));
      rd.seek(blockPtr);
      const strPtrs = [];
      for (let i = 0; i < textPtrCount; i++) strPtrs.push(rd.readU32());
      const subs = [];
      const subOffs = [];
      for (let i = 0; i < strPtrs.length; i++) {
        const sp = strPtrs[i];
        if (sp === 0) continue;
        rd.validate(sp, 'quest string ptr ' + i + ' at 0x' + sp.toString(16));
        rd.seek(sp);
        subs.push(decodeSJIS(rd.readNullTerm()));
        subOffs.push(blockPtr + i * 4);
      }
      if (subs.length) out.push({ offset: subOffs[0], text: subs.join(JOIN), sub_offsets: subOffs });
    }
  }
  return out;
}

function resolveCount(value) {
  if (typeof value === 'number') return value;
  if (typeof value === 'object') return value.zz !== undefined ? value.zz : Object.values(value)[0];
  throw new Error('Cannot resolve entry_count: ' + JSON.stringify(value));
}

function extractSection(plain, config) {
  const rd = new Reader(plain);
  const begin = parseInt(config.begin_pointer, 16);

  if (config.entry_count !== undefined && config.entry_size !== undefined) {
    // Struct-strided
    const count = resolveCount(config.entry_count);
    let base;
    if (config.literal_base) base = begin;
    else { rd.seek(begin); base = rd.readU32(); }
    return readStructStrings(rd, base, count, config.entry_size, config.field_offset);
  }
  if (config.entry_count !== undefined) {
    // Flat pointer array
    const count = resolveCount(config.entry_count);
    const ppe = config.pointers_per_entry || 1;
    if (count === 0) return [];
    rd.validate(begin + 3, 'begin_pointer dereference');
    rd.seek(begin);
    const start = rd.readU32();
    return readFileSection(rd, start, count * ppe * 4);
  }
  if (config.quest_table) {
    const cb = config.count_base_pointer;
    rd.seek(parseInt(cb, 16));
    const baseAddr = rd.readU32();
    const cntAddr = baseAddr + parseInt(config.count_offset || '0', 16);
    rd.validate(cntAddr, 'indirect count address');
    rd.seek(cntAddr);
    const count = (config.count_type === 'u16' ? rd.readU16() : rd.readU32()) + (config.count_adjust || 0);
    if (count === 0) return [];
    rd.seek(begin);
    const catPtr = rd.readU32();
    return readQuestTable(rd, catPtr, count,
      parseInt(config.quest_text_offset || '0x28', 16), config.text_pointers_count || 8);
  }
  if (config.null_terminated) {
    const ppe = config.pointers_per_entry || 1;
    const groupBytes = ppe * 4;
    rd.seek(begin);
    const start = rd.readU32();
    if (config.grouped_entries && ppe > 1) {
      return readMultiPointerEntries(rd, start, ppe);
    }
    let pos = start;
    for (;;) {
      rd.validate(pos, 'null-terminated scan');
      rd.seek(pos);
      if (rd.readU32() === 0) break;
      pos += groupBytes;
    }
    return readFileSection(rd, start, pos - start);
  }
  if (config.next_field_pointer) {
    const nextPtr = parseInt(config.next_field_pointer, 16);
    const cropEnd = config.crop_end || 0;
    rd.seek(begin);
    const start = rd.readU32();
    rd.seek(nextPtr);
    const readLen = rd.readU32() - start - cropEnd;
    return readFileSection(rd, start, readLen);
  }
  if (config.count_pointer) {
    rd.seek(begin);
    const start = rd.readU32();
    rd.seek(parseInt(config.count_pointer, 16));
    const count = rd.readU32();
    if (count === 0) return [];
    return readFileSection(rd, start, count * 4);
  }
  throw new Error('Unknown extraction config format: ' + Object.keys(config).join(','));
}

function readMultiPointerEntries(rd, startPos, ppe) {
  const out = [];
  let pos = startPos;
  for (;;) {
    rd.validate(pos, 'multi-pointer entry scan');
    rd.seek(pos);
    if (rd.readU32() === 0) break;
    rd.seek(pos);
    const ptrs = [];
    for (let i = 0; i < ppe; i++) ptrs.push(rd.readU32());
    const subs = [];
    const subOffs = [];
    for (let i = 0; i < ptrs.length; i++) {
      if (ptrs[i] === 0) continue;
      rd.validate(ptrs[i], 'string pointer in entry at 0x' + pos.toString(16));
      rd.seek(ptrs[i]);
      subs.push(decodeSJIS(rd.readNullTerm()));
      subOffs.push(pos + i * 4);
    }
    if (subs.length) out.push({ offset: subOffs[0], text: subs.join(JOIN), sub_offsets: subOffs });
    pos += ppe * 4;
  }
  return out;
}

// 扁平指针表：逐槽读取，0 = 空槽（绕开 grouped 启发式）
function flatSectionEntries(plain, config) {
  const rd = new Reader(plain);
  const begin = parseInt(config.begin_pointer, 16);
  rd.seek(begin);
  const tableStart = rd.readU32();
  const count = resolveCount(config.entry_count);
  const out = [];
  for (let i = 0; i < count; i++) {
    rd.seek(tableStart + i * 4);
    const ptr = rd.readU32();
    if (ptr === 0) { out.push({ offset: tableStart + i * 4, text: '', sub_offsets: [] }); continue; }
    rd.validate(ptr, 'flat string pointer 0x' + ptr.toString(16));
    rd.seek(ptr);
    out.push({ offset: tableStart + i * 4, text: decodeSJIS(rd.readNullTerm()), sub_offsets: [tableStart + i * 4] });
  }
  return out;
}

// ===========================================================================
// 区段缓存
// ===========================================================================
const sectionCache = new Map(); // file|xpath|flat -> { mtime, entries }

function sectionEntries(fileName, xpath, flat) {
  const key = fileName + '|' + xpath + '|' + (flat ? 1 : 0);
  const full = path.join(GAME_DAT, fileName);
  const mtime = fs.statSync(full).mtimeMs;
  const hit = sectionCache.get(key);
  if (hit && hit.mtime === mtime) return hit.entries;
  const plain = loadPlainBytes(fileName);
  const cfg = lookupConfig(xpath);
  const entries = flat ? flatSectionEntries(plain, cfg) : extractSection(plain, cfg);
  sectionCache.set(key, { mtime, entries });
  return entries;
}

function lookupConfig(xpath) {
  let node = HEADERS;
  for (const part of xpath.split('/')) {
    node = node[part];
    if (!node) throw new Error("xpath '" + xpath + "' not found in headers.json");
  }
  return node;
}

function splitJoinText(text) {
  return String(text).split(/\{j\}|<join at="\d+">/);
}

// ===========================================================================
// 数据表 schema
// ===========================================================================
const TABLES = [
  {
    id: 'items', name: '物品', file: 'mhfdat.bin', id_label: '物品ID（索引+1）', id_base: 1,
    columns: [
      { key: 'name', label: '名字', xpath: 'dat/items/name' },
      { key: 'description', label: '描述', xpath: 'dat/items/description', index_shift: 24,
        note: 'description 表前 24 条为 UI 消息，物品描述从 24 开始' },
      { key: 'source', label: '入手来源', xpath: 'dat/items/source' },
    ],
  },
  {
    id: 'weapons_melee', name: '武器（近战）', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'name', label: '名字', xpath: 'dat/weapons/melee/name' },
      { key: 'description', label: '描述', xpath: 'dat/weapons/melee/description' },
    ],
  },
  {
    id: 'weapons_ranged', name: '武器（远程）', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'name', label: '名字', xpath: 'dat/weapons/ranged/name' },
      { key: 'description', label: '描述', xpath: 'dat/weapons/ranged/description' },
    ],
  },
  {
    id: 'armors', name: '防具（全部部位）', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'head', label: '頭', xpath: 'dat/armors/head' },
      { key: 'body', label: '身', xpath: 'dat/armors/body' },
      { key: 'arms', label: '腕', xpath: 'dat/armors/arms' },
      { key: 'waist', label: '腰', xpath: 'dat/armors/waist' },
      { key: 'legs', label: '脚', xpath: 'dat/armors/legs' },
    ],
  },
  {
    id: 'armor_parts', name: '防具名（单部位视图）', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    parts: [
      ['head', '頭', 'dat/armors/head'],
      ['body', '身', 'dat/armors/body'],
      ['arms', '腕', 'dat/armors/arms'],
      ['waist', '腰', 'dat/armors/waist'],
      ['legs', '脚', 'dat/armors/legs'],
    ],
    columns: [
      { key: 'part', label: '部位' },
      { key: 'name', label: '名字' },
    ],
  },
  {
    id: 'quests', name: '任务', file: 'mhfinf.bin', id_label: '任务索引', id_base: 0,
    columns: [
      { key: 'title', label: '标题', xpath: 'inf/quests', split_index: 0 },
      { key: 'textMain', label: '主要目标', xpath: 'inf/quests', split_index: 1 },
      { key: 'textSubA', label: '次要目标A', xpath: 'inf/quests', split_index: 2 },
      { key: 'textSubB', label: '次要目标B', xpath: 'inf/quests', split_index: 3 },
      { key: 'successCond', label: '成功条件', xpath: 'inf/quests', split_index: 4 },
      { key: 'failCond', label: '失败条件', xpath: 'inf/quests', split_index: 5 },
      { key: 'contractor', label: '委托人', xpath: 'inf/quests', split_index: 6 },
      { key: 'description', label: '描述', xpath: 'inf/quests', split_index: 7 },
    ],
  },
  {
    id: 'skills', name: '技能', file: 'mhfpac.bin', id_label: '索引', id_base: 0, flat: true,
    note: '扁平指针表：每指针槽一条（0=空槽），不用分组启发式',
    columns: [
      { key: 'name', label: '名字', xpath: 'pac/skills/name' },
      { key: 'effect', label: '效果', xpath: 'pac/skills/effect' },
      { key: 'effect_z', label: '效果Z', xpath: 'pac/skills/effect_z' },
      { key: 'description', label: '描述', xpath: 'pac/skills/description' },
    ],
  },
  {
    id: 'monsters', name: '怪物', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'description', label: '描述', xpath: 'dat/monsters/description' },
    ],
  },
  {
    id: 'equipment', name: '装备描述块', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'description', label: '描述（{j} 连接多行）', xpath: 'dat/equipment/description' },
    ],
  },
  {
    id: 'ranks', name: 'HR 等级', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'label', label: '标签', xpath: 'dat/ranks/label' },
      { key: 'requirement', label: '条件', xpath: 'dat/ranks/requirement' },
    ],
  },
  {
    id: 'hunting_horn', name: '狩猎笛', file: 'mhfdat.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'guide', label: '音色指南', xpath: 'dat/hunting_horn/guide' },
      { key: 'tutorial', label: '教程', xpath: 'dat/hunting_horn/tutorial' },
    ],
  },
  {
    id: 'gao', name: '猫伙伴（mhfgao）', file: 'mhfgao.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'armor_helm', label: '頭防具', xpath: 'gao/armor_helm' },
      { key: 'armor_mail', label: '身防具', xpath: 'gao/armor_mail' },
      { key: 'weapon_names', label: '武器名', xpath: 'gao/weapon_names' },
    ],
  },
  {
    id: 'sqd', name: '伙伴/公会（mhfsqd）', file: 'mhfsqd.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'npc_names', label: '伙伴名', xpath: 'sqd/npc_names' },
      { key: 'skill_activation', label: '技能发动', xpath: 'sqd/skill_activation' },
      { key: 'skill_description', label: '技能描述', xpath: 'sqd/skill_description' },
    ],
  },
  {
    id: 'jmp', name: '跳转菜单（mhfjmp）', file: 'mhfjmp.bin', id_label: '索引', id_base: 0,
    columns: [
      { key: 'title', label: '标题', xpath: 'jmp/menu/title' },
      { key: 'description', label: '描述', xpath: 'jmp/menu/description' },
    ],
  },
];

function tableMeta(tab) {
  return {
    id: tab.id, name: tab.name, file: tab.file,
    id_label: tab.id_label || '索引', id_base: tab.id_base || 0,
    columns: tab.columns.map((c) => ({ key: c.key, label: c.label })),
  };
}

function listTables() { return TABLES.map(tableMeta); }

function columnValues(tab, col) {
  const flat = !!(tab.flat || col.flat);
  const entries = sectionEntries(tab.file, col.xpath, flat);
  const shift = col.index_shift || 0;
  if (col.split_index !== undefined) {
    const k = col.split_index;
    return entries.slice(shift).map((e) => {
      const parts = splitJoinText(e.text);
      return parts[k] !== undefined ? parts[k] : '';
    });
  }
  return entries.slice(shift).map((e) => e.text);
}

function buildTable(tabId, opts) {
  const tab = TABLES.find((t) => t.id === tabId);
  if (!tab) throw new Error('unknown table: ' + tabId);
  const offset = opts.offset || 0;
  const limit = opts.limit || 100;
  const q = (opts.q || '').toLowerCase();
  const sort = opts.sort || null;
  const sortDir = opts.dir === 'desc' ? -1 : 1;

  let rows;
  if (tab.parts) {
    rows = [];
    for (const [partKey, partLabel, xpath] of tab.parts) {
      const entries = sectionEntries(tab.file, xpath, false);
      entries.forEach((e, i) => rows.push({ idx: i, part: partLabel, name: e.text }));
    }
  } else {
    const colVals = tab.columns.map((c) => [c.key, columnValues(tab, c)]);
    const n = colVals.length ? colVals[0][1].length : 0;
    rows = [];
    for (let i = 0; i < n; i++) {
      const row = { idx: i };
      for (const [key, vals] of colVals) row[key] = i < vals.length ? vals[i] : '';
      rows.push(row);
    }
  }

  if (q) rows = rows.filter((r) => Object.values(r).some((v) => String(v).toLowerCase().includes(q)));
  if (sort) rows.sort((a, b) => String(a[sort]).localeCompare(String(b[sort]), 'ja') * sortDir);
  const total = rows.length;
  const page = rows.slice(offset, offset + limit);
  return { meta: tableMeta(tab), total, offset, limit, rows: page };
}

function tableRowDetail(tabId, idx, hexLen) {
  const tab = TABLES.find((t) => t.id === tabId);
  if (!tab) throw new Error('unknown table: ' + tabId);
  hexLen = hexLen || 192;

  if (tab.parts) {
    for (const [partKey, partLabel, xpath] of tab.parts) {
      const entries = sectionEntries(tab.file, xpath, false);
      if (idx < entries.length) {
        const e = entries[idx];
        return {
          meta: tableMeta(tab), idx,
          fields: [
            { key: 'part', label: '部位', text: partLabel, offset: null },
            { key: 'name', label: '名字', text: e.text, offset: e.offset },
          ],
          hex: hexOf(tab.file, e.offset, hexLen),
        };
      }
    }
    throw new Error('index out of range');
  }

  const fields = [];
  let hexInfo = null;
  for (const col of tab.columns) {
    const flat = !!(tab.flat || col.flat);
    const entries = sectionEntries(tab.file, col.xpath, flat);
    const eidx = idx + (col.index_shift || 0);
    if (eidx >= entries.length) {
      fields.push({ key: col.key, label: col.label, text: '', offset: null });
      continue;
    }
    const e = entries[eidx];
    if (col.split_index !== undefined) {
      const parts = splitJoinText(e.text);
      const k = col.split_index;
      fields.push({ key: col.key, label: col.label, text: parts[k] !== undefined ? parts[k] : '', offset: e.offset });
      if (!hexInfo && parts[k] !== undefined) hexInfo = e;
    } else {
      fields.push({ key: col.key, label: col.label, text: e.text, offset: e.offset });
      if (!hexInfo) hexInfo = e;
    }
  }
  return { meta: tableMeta(tab), idx, fields, hex: hexInfo ? hexOf(tab.file, hexInfo.offset, hexLen) : null };
}

function hexOf(fileName, off, hexLen) {
  if (off === undefined || off === null) return null;
  const data = loadPlainBytes(fileName);
  const start = Math.max(0, off - 16);
  const chunk = data.slice(start, start + hexLen);
  const lines = [];
  for (let i = 0; i < chunk.length; i += 16) {
    const line = chunk.slice(i, i + 16);
    const hexs = Array.from(line, (c) => c.toString(16).padStart(2, '0').toUpperCase()).join(' ');
    const asc = Array.from(line, (c) => (c >= 32 && c <= 126 ? String.fromCharCode(c) : '.')).join('');
    lines.push((start + i).toString(16).padStart(8, '0') + '  ' + hexs.padEnd(47) + '  ' + asc);
  }
  return { file: fileName, pos: start, lines };
}

module.exports = {
  GAME_DAT, TABLES, listTables, buildTable, tableRowDetail,
  decrypt, decompressJkr, isEncrypted, isJkrFile,
  loadPlainBytes, sectionEntries, lookupConfig,
};
