<template>
  <div class="sidebar-inner">
    <el-scrollbar>
      <el-tree :data="tree" node-key="key" highlight-current
               :current-node-key="store.currentKey"
               :expand-on-click-node="false" :default-expanded-keys="expandedKeys"
               @node-click="onNodeClick">
        <template #default="{ data }">
          <span class="node-label" :title="data.tip || data.path">
            <span v-if="data.type === 'dir'">📁 </span>
            <span v-else-if="data.type === 'file'">📄 </span>
            <span v-else-if="data.type === 'dtable'">🗄 </span>
            <span v-else-if="data.type === 'table'">📋 </span>
            <span v-else-if="data.type === 'pair'">🔗 </span>
            {{ data.label }}
          </span>
          <span v-if="data.size" class="node-size">{{ fmtSize(data.size) }}</span>
        </template>
      </el-tree>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { store, fmtSize, buildTreeData } from '../store';

const emit = defineEmits(['open-file', 'open-table', 'open-pair', 'open-dtable']);

const tree = computed(() => buildTreeData(store.files, store.tables, store.pairs, store.dtables));

// 默认展开第一层分组
const expandedKeys = computed(() =>
  store.files.map((g) => 'group:' + g.name).concat(['group:dtables', 'group:tables', 'group:pairs'])
);

function onNodeClick(data) {
  if (data.type === 'file') {
    store.currentKey = data.key;
    emit('open-file', data.path);
  } else if (data.type === 'dtable') {
    store.currentKey = data.key;
    emit('open-dtable', data.id);
  } else if (data.type === 'table') {
    store.currentKey = data.key;
    emit('open-table', data.idx);
  } else if (data.type === 'pair') {
    store.currentKey = data.key;
    emit('open-pair', data.idx);
  }
}
</script>

<style scoped>
.sidebar-inner { display: flex; flex-direction: column; height: 100%; }
:deep(.el-tree) {
  background: transparent;
  color: #cdd6f4;
  font-size: 12.5px;
}
:deep(.el-tree-node__content) {
  height: 26px;
  display: flex;
  align-items: center;
}
:deep(.el-tree-node__content:hover) { background: #313244; }
:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: #45475a;
  color: #89b4fa;
}
:deep(.el-tree-node__label) { flex: 1; min-width: 0; }
:deep(.el-tree-node__expand-icon) { color: #6c7086; }
.node-label {
  display: inline-flex; align-items: center; gap: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 100%;
}
.node-size { color: #6c7086; font-size: 11px; margin-left: 8px; flex-shrink: 0; }
</style>
