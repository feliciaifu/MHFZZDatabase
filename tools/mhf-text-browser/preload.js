'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('mhf', {
  scanFiles: () => ipcRenderer.invoke('scan-files'),
  getTables: () => ipcRenderer.invoke('get-tables'),
  getFileInfo: (rel) => ipcRenderer.invoke('get-fileinfo', rel),
  getEntries: (rel, offset, limit) => ipcRenderer.invoke('get-entries', rel, offset, limit),
  getTable: (rel, fromPos, maxLen, offset, limit) => ipcRenderer.invoke('get-table', rel, fromPos, maxLen, offset, limit),
  getPair: (ja, zh, offset, limit) => ipcRenderer.invoke('get-pair', ja, zh, offset, limit),
  search: (rel, q, max) => ipcRenderer.invoke('search', rel, q, max),
  getHex: (rel, pos, len) => ipcRenderer.invoke('get-hex', rel, pos, len),
  getSchema: () => ipcRenderer.invoke('get-schema'),
  getDTable: (id, opts) => ipcRenderer.invoke('get-dtable', id, opts),
  getDRow: (id, idx, hexLen) => ipcRenderer.invoke('get-drow', id, idx, hexLen),
});
