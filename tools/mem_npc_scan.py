# -*- coding: utf-8 -*-
"""扫描内存区域内的短文本序列（NPC 名），不依赖记录结构
用法: python mem_npc_scan.py <pid> <区域起点hex> [输出json]
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


def is_text(data, i):
    b = data[i]
    if 0x20 <= b <= 0x7E:
        return 1
    if 0x81 <= b <= 0xFC and i + 1 < len(data):
        b2 = data[i + 1]
        if (0x40 <= b2 <= 0x7E) or (0x80 <= b2 <= 0xFC):
            return 2
    return 0


def scan_short_texts(data, min_len=2, max_len=40):
    """扫描数据中所有 短文本序列（连续 SJIS 可读字节）"""
    out = []
    i = 0
    while i < len(data):
        w = is_text(data, i)
        if w:
            start = i
            while i < len(data) and is_text(data, i):
                i += is_text(data, i)
            ln = i - start
            if min_len <= ln <= max_len:
                out.append((start, data[start:i]))
            continue
        i += 1
    return out


def main():
    pid = int(sys.argv[1])
    base = int(sys.argv[2], 16)
    out = sys.argv[3] if len(sys.argv) > 3 else None
    size = 0x4000
    data = read_memory(pid, base, size)
    if not data:
        print("读取失败")
        return
    texts = scan_short_texts(data)
    print(f"区域 0x{base:08X} 短文本: {len(texts)} 个")
    names = []
    for i, (off, t) in enumerate(texts):
        s = t.decode('shift_jis', errors='replace')
        # 过滤明显非名字（含控制符/过长空白）
        if s.strip():
            names.append(s)
            print(f"  [{i}] @0x{base+off:08X} ({len(t):2d}B): {s}")
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump({"base": hex(base), "names": names}, f, ensure_ascii=False, indent=1)
        print(f"已保存: {out}")


if __name__ == '__main__':
    main()
