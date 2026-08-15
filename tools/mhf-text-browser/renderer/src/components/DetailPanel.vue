<template>
  <section class="detail-panel">
    <div class="detail-head">条目详情</div>
    <div class="detail-body">
      <div v-if="!entry && !pair && !drow" class="empty-hint">
        点击左侧条目查看详情<br>（文本 + Hex 双视图）
      </div>

      <template v-else-if="drow">
        <div class="detail-field">数据表行（{{ drow.meta ? drow.meta.name : '' }}）</div>
        <div class="detail-val">#{{ drow.idx }}</div>
        <template v-for="f in drow.fields" :key="f.key">
          <div class="detail-field">{{ f.label }}
            <span v-if="f.offset != null" class="field-off">@明文偏移 0x{{ f.offset.toString(16) }}</span>
          </div>
          <div class="detail-val" :class="{ ja: true }">{{ f.text || '' }}</div>
        </template>
        <div v-if="drow.hex" class="detail-field">明文 Hex（{{ drow.hex.file }}，解密+解压后）</div>
        <pre v-if="drow.hex" class="detail-hex">{{ drowHex }}</pre>
      </template>

      <template v-else-if="pair">
        <div class="detail-field">条目索引（ja↔zh 对应）</div>
        <div class="detail-val">#{{ pair.idx }}</div>

        <div class="detail-field">日文原文（{{ pairMeta ? pairMeta[0] : '' }}）</div>
        <div class="detail-val ja">{{ pair.ja.text }}</div>
        <div class="detail-field">日文 Hex</div>
        <pre class="detail-hex">{{ jaHex }}</pre>

        <div class="detail-field">中文译文（{{ pairMeta ? pairMeta[1] : '' }}）</div>
        <div class="detail-val">{{ pair.zh.text }}</div>
        <div class="detail-field">中文 Hex</div>
        <pre class="detail-hex">{{ zhHex }}</pre>
      </template>

      <template v-else>
        <div class="detail-field">条目索引</div>
        <div class="detail-val">{{ entry.idx }}</div>

        <div class="detail-field">字节偏移</div>
        <div class="detail-val">0x{{ entry.start.toString(16) }} — 0x{{ entry.end.toString(16) }}
          （长度 {{ entry.len }} 字节）</div>

        <div class="detail-field">文本（Shift-JIS 解码）</div>
        <div class="detail-val">{{ entry.text }}</div>

        <div class="detail-field">Hex</div>
        <pre class="detail-hex">{{ hex }}</pre>
      </template>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue';
import { store } from '../store';

const props = defineProps({
  entry: { type: Object, default: null },
  pair: { type: Object, default: null },
  pairMeta: { type: Array, default: null },
  drow: { type: Object, default: null },
  path: { type: String, default: null },
});

const hex = ref('');
const jaHex = ref('');
const zhHex = ref('');
const drowHex = ref('');

watch(
  () => [props.entry, props.pair, props.drow],
  async () => {
    hex.value = '';
    jaHex.value = '';
    zhHex.value = '';
    drowHex.value = '';
    if (props.drow && props.drow.hex) {
      drowHex.value = props.drow.hex.lines.join('\n');
      return;
    }
    if (!props.path) return;
    try {
      if (props.entry) {
        const d = await mhf.getHex(props.path, props.entry.start, Math.max(props.entry.len, 16));
        hex.value = d.lines.join('\n');
      } else if (props.pair && props.pairMeta) {
        const [dja, dzh] = await Promise.all([
          mhf.getHex(props.pairMeta[0], props.pair.ja.start, Math.max(props.pair.ja.len, 16)),
          mhf.getHex(props.pairMeta[1], props.pair.zh.start, Math.max(props.pair.zh.len, 16)),
        ]);
        jaHex.value = dja.lines.join('\n');
        zhHex.value = dzh.lines.join('\n');
      }
    } catch (e) {
      hex.value = 'Hex 读取失败: ' + e.message;
    }
  },
  { immediate: true }
);
</script>
