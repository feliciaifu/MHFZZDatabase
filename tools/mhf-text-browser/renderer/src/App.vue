<template>
  <div class="app-root">
    <header class="app-header">
      <div class="brand">
        <span class="logo">🗡️</span>
        <span class="title">MHFZ 文本数据浏览器</span>
      </div>
      <div class="search-box">
        <el-select v-model="searchPath" class="search-file" placeholder="选择搜索文件" filterable clearable>
          <el-option v-for="g in store.files" :key="g.name" :label="g.name" disabled />
          <el-option v-for="f in allFiles" :key="f.path" :label="groupLabel(f)" :value="f.path" />
        </el-select>
        <el-input v-model="searchQ" class="search-input" placeholder="搜索关键词…（如：回復藥 / 調合書）"
                  clearable @keyup.enter="doSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="doSearch" :loading="searching">搜索</el-button>
        <span class="search-info">{{ searchInfo }}</span>
      </div>
    </header>

    <div class="main-body">
      <aside class="sidebar">
        <Sidebar @open-file="openFile" @open-table="openTable" @open-pair="openPair"
                 @open-dtable="openDTable" />
      </aside>
      <EntriesPanel ref="entriesPanel" @select-entry="selectEntry" @select-pair="selectPair"
                    @select-drow="selectDRow" />
      <DetailPanel :entry="detailEntry" :pair="detailPair" :pair-meta="detailPairMeta"
                   :drow="detailDRow" :path="store.currentPath" />
    </div>

    <footer class="statusbar">{{ store.status }}</footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { Search } from '@element-plus/icons-vue';
import { store, setStatus, fmtSize } from './store';
import Sidebar from './components/Sidebar.vue';
import EntriesPanel from './components/EntriesPanel.vue';
import DetailPanel from './components/DetailPanel.vue';

const searchPath = ref('');
const searchQ = ref('');
const searchInfo = ref('');
const searching = ref(false);
const entriesPanel = ref(null);
const detailEntry = ref(null);
const detailPair = ref(null);
const detailPairMeta = ref(null);
const detailDRow = ref(null);

const allFiles = computed(() => store.files.flatMap((g) => g.files));
function groupLabel(f) {
  const g = store.files.find((x) => x.files.includes(f));
  return (g ? g.name + '/' : '') + f.path.split('/').pop();
}

onMounted(async () => {
  try {
    const [files, td] = await Promise.all([mhf.scanFiles(), mhf.getTables()]);
    store.files = files;
    store.tables = td.tables;
    store.pairs = td.pairs;
    try {
      const sd = await mhf.getSchema();
      store.dtables = sd.tables || [];
    } catch (e) {
      store.dtables = [];
      setStatus('数据表引擎不可用: ' + e.message);
      return;
    }
    const n = files.reduce((s, g) => s + g.files.length, 0);
    setStatus(`就绪：${n} 个文件，${store.dtables.length} 张数据表（汉化工具 + 游戏数据）`);
  } catch (e) {
    setStatus('初始化失败: ' + e.message);
  }
});

async function openFile(path) {
  store.currentPath = path;
  store.tableMode = null;
  store.offset = 0;
  detailEntry.value = null;
  detailPair.value = null;
  const info = await mhf.getFileInfo(path);
  store.fileSize = info.size;
  setStatus(`${path}（${fmtSize(info.size)}）`);
  entriesPanel.value.reload();
}

async function openTable(idx) {
  const t = store.tables[idx];
  store.currentPath = t[0];
  store.tableMode = { kind: 'table', idx };
  store.offset = 0;
  detailEntry.value = null;
  detailPair.value = null;
  setStatus(t[3]);
  entriesPanel.value.reload();
}

async function openPair(idx) {
  const p = store.pairs[idx];
  store.currentPath = p[0];
  store.tableMode = { kind: 'pair', idx };
  store.offset = 0;
  detailEntry.value = null;
  detailPair.value = null;
  detailDRow.value = null;
  setStatus(p[3]);
  entriesPanel.value.reload();
}

async function openDTable(id) {
  const meta = store.dtables.find((t) => t.id === id);
  if (!meta) return;
  store.currentPath = 'dt:' + id;
  store.tableMode = { kind: 'dt', id };
  store.dtMeta = meta;
  store.dtSort = null;
  store.dtDir = 'asc';
  store.dtQ = '';
  store.offset = 0;
  detailEntry.value = null;
  detailPair.value = null;
  detailDRow.value = null;
  searchQ.value = '';
  setStatus('数据表：' + meta.name + '（' + meta.file + '）');
  entriesPanel.value.reload();
}

function selectEntry(e) {
  detailPair.value = null;
  detailDRow.value = null;
  detailEntry.value = e;
}

function selectPair(p) {
  detailEntry.value = null;
  detailDRow.value = null;
  detailPair.value = p;
  detailPairMeta.value = store.tableMode ? store.pairs[store.tableMode.idx] : null;
}

function selectDRow(row) {
  detailEntry.value = null;
  detailPair.value = null;
  detailDRow.value = row;
}

async function doSearch() {
  const q = searchQ.value.trim();
  // 数据表模式：搜索变为当前表过滤
  if (store.tableMode && store.tableMode.kind === 'dt') {
    store.dtQ = q;
    store.offset = 0;
    searchInfo.value = q ? '过滤: ' + q : '';
    entriesPanel.value.reload();
    return;
  }
  const path = searchPath.value;
  if (!q) { searchInfo.value = '请输入关键词'; return; }
  if (!path) { searchInfo.value = '请选择文件'; return; }
  searching.value = true;
  searchInfo.value = '搜索中…';
  try {
    const d = await mhf.search(path, q, 300);
    searchInfo.value = `找到 ${d.total} 条（显示前 ${d.hits.length} 条）`;
    entriesPanel.value.showSearchResults(path, q, d.hits);
  } catch (e) {
    searchInfo.value = '错误: ' + e.message;
  } finally {
    searching.value = false;
  }
}
</script>

<style scoped>
.app-root { display: flex; flex-direction: column; height: 100vh; }
.main-body { flex: 1; display: flex; min-height: 0; }
</style>
