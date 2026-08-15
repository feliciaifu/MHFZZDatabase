<template>
  <section class="list-panel">
    <div class="list-head">
      <span class="file-label">{{ title }}</span>
      <span class="count">{{ countLabel }}</span>
    </div>

    <div class="table-wrap">
      <el-table :data="rows" size="small" height="100%" highlight-current-row stripe
                :row-key="(row) => row.idxLabel" :current-row-key="currentRowKey"
                @current-change="onRowClick" ref="tableRef"
                @sort-change="onSortChange">
        <template v-if="isDT">
          <el-table-column label="#" width="80">
            <template #default="{ row }">
              <span class="cell-idx">{{ row.idx }}</span>
            </template>
          </el-table-column>
          <el-table-column v-for="col in dtCols" :key="col.key" :label="col.label"
                           :prop="col.key" min-width="140" sortable="custom" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="cell-txt">{{ cellText(row[col.key]) }}</span>
            </template>
          </el-table-column>
        </template>
        <template v-else>
          <el-table-column label="#" width="95">
            <template #default="{ row }">
              <span class="cell-idx">{{ row.idxLabel }}</span>
            </template>
          </el-table-column>
          <el-table-column label="偏移" width="90">
            <template #default="{ row }">
              <span class="cell-off">0x{{ row.start.toString(16) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="长度" width="60" prop="len" />
          <el-table-column label="文本" min-width="200">
            <template #default="{ row }">
              <span class="cell-txt" :class="{ ja: row.isJa }" v-html="row.html"></span>
            </template>
          </el-table-column>
        </template>
      </el-table>
    </div>

    <div class="pager-bar">
      <el-pagination small background layout="prev, pager, next, sizes, jumper"
                     :total="store.total" :current-page="currentPage" :page-size="store.pageSize"
                     :page-sizes="[50, 200, 1000, 5000]"
                     @current-change="(p) => { store.offset = (p - 1) * store.pageSize; reload(); }"
                     @size-change="(s) => { store.pageSize = s; store.offset = 0; reload(); }" />
    </div>

    <div v-if="searchVisible" class="search-results">
      <div class="hit-head">{{ searchTitle }}</div>
      <div v-for="h in searchHits" :key="h.idx" class="hit" @click="gotoHit(h)">
        <span class="hidx">#{{ h.idx }} @0x{{ h.start.toString(16) }}</span>
        <span v-html="highlight(h.text)"></span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, defineExpose } from 'vue';
import { store, setStatus } from '../store';

const emit = defineEmits(['select-entry', 'select-pair', 'select-drow']);
const tableRef = ref(null);
const searchVisible = ref(false);
const searchHits = ref([]);
const searchQ = ref('');
const searchPath = ref('');
const currentRowKey = ref(null);

const isDT = computed(() => store.tableMode && store.tableMode.kind === 'dt');
const dtCols = computed(() => (store.dtMeta ? store.dtMeta.columns : []));

function cellText(v) {
  if (v === undefined || v === null || v === '') return '';
  return String(v).replace(/\n/g, '⏎').slice(0, 80);
}

const rows = computed(() => {
  const t = store.tableMode;
  if (isDT.value) {
    return store.dtRows.map((r) => ({ ...r, idxLabel: r.idx, isDT: true }));
  }
  if (t && t.kind === 'pair') {
    return store.pairData.map((p) => ({
      idxLabel: p.idx,
      start: p.ja.start,
      len: p.ja.len,
      isJa: true,
      html: esc(p.ja.text.slice(0, 55)) + '<span class="arrow">⮕</span>' + esc(p.zh.text.slice(0, 40)),
      pair: p,
    }));
  }
  if (t && t.kind === 'table') {
    const tab = store.tables[t.idx];
    return store.entries.map((e) => ({
      idxLabel: tab[4] != null ? 'ID ' + (e.idx + tab[4]) : e.idx,
      start: e.start,
      len: e.len,
      isJa: false,
      html: esc(e.text.slice(0, 100)),
      entry: e,
    }));
  }
  return store.entries.map((e) => ({
    idxLabel: e.idx,
    start: e.start,
    len: e.len,
    isJa: false,
    html: esc(e.text.slice(0, 100)),
    entry: e,
  }));
});

const title = computed(() => {
  const t = store.tableMode;
  if (!store.currentPath) return '← 从左侧选择文件或名字表';
  if (t && t.kind === 'dt') {
    return '🗄 ' + (store.dtMeta ? store.dtMeta.name : '') + ' — ' + (store.dtMeta ? store.dtMeta.file : '');
  }
  if (t && t.kind === 'pair') return '🔗 ' + store.pairs[t.idx][2];
  if (t && t.kind === 'table') {
    const tab = store.tables[t.idx];
    return '📋 ' + tab[2] + ' — ' + tab[0] + ' @' + tab[1];
  }
  return store.currentPath;
});

const countLabel = computed(() => {
  const t = store.tableMode;
  if (!store.currentPath) return '';
  if (t && t.kind === 'dt') {
    return '共 ' + store.total.toLocaleString() + ' 行' + (store.dtQ ? '（过滤: ' + store.dtQ + '）' : '');
  }
  if (t && t.kind === 'pair') {
    return '配对 ' + store.total.toLocaleString() + ' 条';
  }
  return '共 ' + store.total.toLocaleString() + ' 条';
});

const currentPage = computed(() => Math.floor(store.offset / store.pageSize) + 1);

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function highlight(text) {
  if (!searchQ.value) return esc(text);
  const q = esc(searchQ.value);
  const re = new RegExp(esc(q).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
  return esc(text).replace(re, '<span class="highlight">' + q + '</span>');
}

function onRowClick(row) {
  if (!row) return;
  if (row.isDT) emit('select-drow', row);
  else if (row.pair) emit('select-pair', row.pair);
  else if (row.entry) emit('select-entry', row.entry);
}

function onSortChange({ prop, order }) {
  if (!isDT.value || !prop) return;
  store.dtSort = prop;
  store.dtDir = order === 'descending' ? 'desc' : 'asc';
  if (!order) store.dtSort = null;
  store.offset = 0;
  reload();
}

function showSearchResults(path, q, hits) {
  searchPath.value = path;
  searchQ.value = q;
  searchHits.value = hits;
  searchVisible.value = true;
}

function gotoHit(h) {
  store.currentPath = searchPath.value;
  store.tableMode = null;
  searchVisible.value = false;
  currentRowKey.value = null;
  store.offset = Math.floor(h.idx / store.pageSize) * store.pageSize;
  awaitReloadThenHighlight(h.idx);
}

async function awaitReloadThenHighlight(idx) {
  await reload();
  // 目标行可能在下一页（行恰好在边界时）：重新计算
  if (idx >= store.offset + rows.value.length) {
    store.offset = Math.floor(idx / store.pageSize) * store.pageSize;
    await reload();
  }
  const target = rows.value.find((r) => (r.entry && r.entry.idx === idx) || (r.pair && r.pair.idx === idx));
  if (target) currentRowKey.value = target.idxLabel;
}

async function reload() {
  if (!store.currentPath) return;
  store.loading = true;
  try {
    const t = store.tableMode;
    if (t && t.kind === 'dt') {
      const d = await mhf.getDTable(t.id, {
        offset: store.offset, limit: store.pageSize,
        q: store.dtQ, sort: store.dtSort || null, dir: store.dtDir,
      });
      store.total = d.total;
      store.dtRows = d.rows;
      store.entries = [];
      store.pairData = [];
    } else if (t && t.kind === 'pair') {
      const p = store.pairs[t.idx];
      const d = await mhf.getPair(p[0], p[1], store.offset, store.pageSize);
      store.total = d.common;
      store.pairData = d.pairs;
      store.entries = [];
    } else if (t && t.kind === 'table') {
      const tab = store.tables[t.idx];
      const d = await mhf.getTable(tab[0], tab[1], 40, store.offset, store.pageSize);
      store.total = d.total;
      store.entries = d.entries;
      store.pairData = [];
    } else {
      const d = await mhf.getEntries(store.currentPath, store.offset, store.pageSize);
      store.total = d.total;
      store.entries = d.entries;
      store.pairData = [];
    }
  } catch (e) {
    setStatus('错误: ' + e.message);
  } finally {
    store.loading = false;
  }
}

defineExpose({ reload, showSearchResults });
</script>
