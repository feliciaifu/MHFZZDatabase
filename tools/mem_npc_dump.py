# -*- coding: utf-8 -*-
"""解析 NPC 名对象表（固定 0x40 字节记录），输出全部 NPC 名
用法: python mem_npc_dump.py <pid> [输出文件]
"""
import ctypes
import ctypes.wintypes as wt
import sys
import json

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


def read_memory(pid, addr, size):
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return None
    try:
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        if kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
            return buf.raw[:read.value]
        return None
    finally:
        kernel32.CloseHandle(h)


def find_in_range(pid, start, end, needle, chunk=0x400000):
    hits = []
    pos = start
    overlap = len(needle) - 1
    while pos < end:
        size = min(chunk, end - pos)
        data = read_memory(pid, pos, size)
        if data:
            idx = data.find(needle)
            while idx >= 0:
                hits.append(pos + idx)
                idx = data.find(needle, idx + 1)
        if size <= overlap:
            break
        pos += size - overlap
    return hits


def dump_table(pid, anchor):
    """从锚点（某条记录内文本位置）解析对象表：对齐记录起点 → 向前向后收集记录"""
    # 记录起点 = 文本位置 - 23（头长），再 0x40 对齐
    rec = anchor - 23
    base = rec - (rec % 0x40)  # 对齐 0x40
    # 验证 base 处是记录头（文本在 base+23 处为合法 SJIS）
    names = []
    pos = base
    while True:
        data = read_memory(pid, pos, 0x40)
        if not data:
            break
        tp = 23
        end = tp
        while end < 0x40 and data[end] != 0:
            end += 1
        text = data[tp:end]
        if 2 <= len(text) <= 40:
            names.append((pos, text))
        else:
            break  # 记录结构破坏，结束
        pos += 0x40
    return names


def main():
    pid = int(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    # 定位对象表（用已知 NPC 名特征）
    anchor_hits = []
    for kw in ['航路クエスト受付', '各種クエスト受付']:
        hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, kw.encode('shift_jis'))
        print(f"'{kw}' 命中: {[hex(h) for h in hits]}")
        anchor_hits.extend(hits)
    if not anchor_hits:
        print("未找到对象表")
        return

    # 从第一个锚点向前找对象表起点（连续 0x40 记录）
    anchor = anchor_hits[0]
    # 记录起点 = 文本位置 - 23（头长），向前 0x40 步进找连续记录区起点
    rec = anchor - 23
    start_rec = rec
    # 向前验证：每条记录头 23 字节后是合法文本（2-40 字节）
    while start_rec >= 0x10000:
        prev = read_memory(pid, start_rec - 0x40, 0x40)
        if not prev:
            break
        tp = 23
        end = tp
        while end < 0x40 and prev[end] != 0:
            end += 1
        if 2 <= len(prev[tp:end]) <= 40:
            start_rec -= 0x40
        else:
            break
    print(f"对象表起点: 0x{start_rec:08X}")

    names = []
    pos = start_rec
    while pos < start_rec + 0x20000:  # 最多 2048 条记录
        data = read_memory(pid, pos, 0x40)
        if not data:
            break
        tp = 23
        end = tp
        while end < 0x40 and data[end] != 0:
            end += 1
        text = data[tp:end]
        if 2 <= len(text) <= 40:
            names.append(text.decode('shift_jis', errors='replace'))
        else:
            break
        pos += 0x40
    print(f"NPC 名总数: {len(names)}")
    for i, n in enumerate(names):
        print(f"  [{i}] {n}")

    if out:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump({"base": hex(start_rec), "names": names}, f, ensure_ascii=False, indent=1)
        print(f"已保存: {out}")


if __name__ == '__main__':
    main()
