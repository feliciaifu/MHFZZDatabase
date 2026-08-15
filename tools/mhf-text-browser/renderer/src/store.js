import { reactive } from 'vue';

export const store = reactive({
  files: [],
  tables: [],
  pairs: [],
  dtables: [], // 数据表（权威解析）
  currentPath: null,
  tableMode: null, // { kind: 'table'|'pair'|'dt', idx|id }
  currentKey: null, // 树节点高亮 key
  total: 0,
  pageSize: 200,
  offset: 0,
  entries: [],
  pairData: [],
  dtRows: [],
  dtMeta: null, // 当前数据表的 meta（列定义等）
  dtSort: null,
  dtDir: 'asc',
  dtQ: '',
  loading: false,
  status: '就绪',
  fileSize: 0,
});

export function setStatus(msg) {
  store.status = msg;
}

export function fmtSize(n) {
  if (n > 1048576) return (n / 1048576).toFixed(1) + ' MB';
  if (n > 1024) return (n / 1024).toFixed(1) + ' KB';
  return n + ' B';
}

/** 把扁平文件列表 + 已知表 + 配对 + 数据表，构建成目录树数据 */
export function buildTreeData(files, tables, pairs, dtables) {
  const tree = [];
  for (const g of files) {
    const node = { label: g.name, type: 'group', key: 'group:' + g.name, children: [] };
    const dirMap = new Map();
    for (const f of g.files) {
      const parts = f.path.split('/');
      const name = parts[parts.length - 1];
      let cur = node.children;
      let dirKey = g.name;
      for (let i = 0; i < parts.length - 1; i++) {
        dirKey += '/' + parts[i];
        let dirNode = dirMap.get(dirKey);
        if (!dirNode) {
          dirNode = { label: parts[i], type: 'dir', key: 'dir:' + dirKey, children: [] };
          dirMap.set(dirKey, dirNode);
          cur.push(dirNode);
        }
        cur = dirNode.children;
      }
      cur.push({ label: name, type: 'file', path: f.path, size: f.size, key: 'file:' + f.path });
    }
    tree.push(node);
  }
  tree.push({
    label: '🗄 数据表（权威解析）',
    type: 'group',
    key: 'group:dtables',
    children: (dtables || []).map((t) => ({
      label: t.name, type: 'dtable', id: t.id,
      tip: t.file + ' · ' + t.columns.map((c) => c.label).join(' / '),
      key: 'dtable:' + t.id,
    })),
  });
  tree.push({
    label: '📋 已知名字表',
    type: 'group',
    key: 'group:tables',
    children: tables.map((t, i) => ({
      label: t[2] + '  @' + t[1], type: 'table', idx: i, tip: t[3], key: 'table:' + i,
    })),
  });
  tree.push({
    label: '🔗 ja↔zh 配对',
    type: 'group',
    key: 'group:pairs',
    children: pairs.map((p, i) => ({
      label: p[2], type: 'pair', idx: i, tip: p[3], key: 'pair:' + i,
    })),
  });
  return tree;
}
