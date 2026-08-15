# -*- coding: utf-8 -*-
"""分析内存中 NPC 名区（mhfpac 文本区）的结构，找文本区起点"""
import ctypes
import ctypes.wintypes as wt
import sys

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


def main():
    pid = int(sys.argv[1])
    anchor = int(sys.argv[2], 16)  # NPC 名命中点
    print(f"锚点: 0x{anchor:08X}")

    # 向前读 128KB，分析条目结构
    back = 0x20000
    data = read_memory(pid, anchor - back, back + 0x2000)
    if not data:
        print("读取失败")
        return
    # 从 anchor 向前找文本区起点：从 anchor 往前扫描，找"连续的 00 分隔条目流"的起点
    # 方法：从 anchor 向前，标记所有"条目起点"（00 后的非 00 字节），找最长连续段起点
    rel = back  # anchor 在 data 中的偏移
    # 向前遍历：找 anchor 之前最近的"非条目"边界（大量 00 或二进制）
    pos = rel
    # 策略：向前走，统计每 4KB 的 00 比例，找到 00 密集区（文本区边界）
    print("向前分析（每 4KB 的 00 比例）:")
    for off in range(0, back, 0x1000):
        chunk = data[back - off - 0x1000: back - off]
        zeros = chunk.count(b'\x00')
        ratio = zeros / 0x1000
        mark = "  <== 00密集(边界?)" if ratio > 0.4 else ""
        if ratio > 0.4 or off < 0x2000:
            print(f"  0x{anchor-back+off:08X}: 00比例 {ratio:.2f}{mark}")
    # 打印 anchor 前 20 个条目
    print("\nanchor 前的条目:")
    s = rel
    for k in range(20):
        s2 = s
        while s2 > 0 and data[s2-1] != 0:
            s2 -= 1
        e = data[s2:s]
        if len(e) > 0:
            print(f"  [{-k}] 0x{anchor-s+s2:08X} ({len(e):4d}B): {e.decode('shift_jis', errors='replace')[:50]}")
        s = s2 - 1
        if s <= 0:
            break


if __name__ == '__main__':
    main()
