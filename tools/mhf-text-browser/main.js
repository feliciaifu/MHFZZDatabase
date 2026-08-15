'use strict';
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const P = require('./lib/parser');
const FTH = require('./lib/fth');

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 680,
    backgroundColor: '#11111b',
    title: 'MHFZ 文本数据浏览器',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    win.loadURL(devUrl);
  } else {
    win.loadFile(path.join(__dirname, 'renderer', 'dist', 'index.html'));
  }
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// ---------------------------------------------------------------------------
// IPC
// ---------------------------------------------------------------------------
function page(data, offset, limit) {
  return data.slice(offset, offset + limit);
}

ipcMain.handle('scan-files', () => P.scanFiles());
ipcMain.handle('get-tables', () => ({ tables: P.KNOWN_TABLES, pairs: P.KNOWN_PAIRS }));

ipcMain.handle('get-fileinfo', (_e, rel) => {
  const tf = P.getTextFile(rel);
  return { path: rel, size: tf.size };
});

ipcMain.handle('get-entries', (_e, rel, offset, limit) => {
  const entries = P.getTextFile(rel).entries();
  return {
    path: rel, total: entries.length,
    offset, limit,
    entries: page(entries, offset, limit).map((e, i) => ({ ...e, idx: offset + i })),
  };
});

ipcMain.handle('get-table', (_e, rel, fromPos, maxLen, offset, limit) => {
  const entries = P.tableEntries(rel, fromPos, maxLen);
  return {
    path: rel, from: fromPos, total: entries.length,
    offset, limit,
    entries: page(entries, offset, limit).map((e, i) => ({ ...e, idx: offset + i })),
  };
});

ipcMain.handle('get-pair', (_e, jaRel, zhRel, offset, limit) => {
  const je = P.getTextFile(jaRel).entries();
  const ze = P.getTextFile(zhRel).entries();
  const common = Math.min(je.length, ze.length);
  const pairs = [];
  for (let i = offset; i < Math.min(offset + limit, common); i++) {
    pairs.push({
      idx: i,
      ja: { start: je[i].start, len: je[i].len, text: je[i].text },
      zh: { start: ze[i].start, len: ze[i].len, text: ze[i].text },
    });
  }
  return { ja: jaRel, zh: zhRel, ja_total: je.length, zh_total: ze.length, common, offset, limit, pairs };
});

ipcMain.handle('search', (_e, rel, q, maxHits) => {
  const entries = P.getTextFile(rel).entries();
  const needle = q.toLowerCase();
  const hits = [];
  for (let i = 0; i < entries.length && hits.length < (maxHits || 300); i++) {
    const pos = entries[i].text.toLowerCase().indexOf(needle);
    if (pos >= 0) hits.push({ idx: i, start: entries[i].start, len: entries[i].len, text: entries[i].text, pos });
  }
  return { path: rel, q, total: hits.length, hits };
});

ipcMain.handle('get-hex', (_e, rel, pos, len) => {
  const tf = P.getTextFile(rel);
  const data = tf.data().slice(pos, pos + Math.min(len, 8192));
  return { path: rel, pos, length: data.length, lines: P.hexdump(data, pos) };
});

// ---------------------------------------------------------------------------
// 数据表视图（FrontierTextHandler 移植引擎：ECD 解密 + JKR 解压 + headers.json）
// ---------------------------------------------------------------------------
ipcMain.handle('get-schema', () => ({ tables: FTH.listTables() }));

ipcMain.handle('get-dtable', (_e, id, opts) => FTH.buildTable(id, opts || {}));

ipcMain.handle('get-drow', (_e, id, idx, hexLen) => FTH.tableRowDetail(id, idx, hexLen));
