# -*- coding: utf-8 -*-
"""对比 zh/mhfpac.bin 短条目 vs 内存对象表文本（验证顺序配对）"""
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
    # 1. zh/mhfpac.bin 短条目（NPC 名候选：长度 6-30 字节）
    zh = open(r'D:\Games\PC\MHF\MHF External tool 5.41_axibug_α\zh\mhfpac.bin', 'rb').read()
    zh_short = []
    for e in zh.split(b'\x00'):
        if 6 <= len(e) <= 30:
            zh_short.append(e)
    print(f"zh/mhfpac.bin 短条目: {len(zh_short)}")
    for i, e in enumerate(zh_short[:40]):
        print(f"  zh[{i}] {e.decode('shift_jis', errors='replace')}")

    # 2. 内存对象表（0x155F7000 附近 64KB）解析记录文本
    print("\n内存对象表记录文本:")
    base = 0x155F7000
    data = read_memory(pid, base, 0x10000)
    if not data:
        print("读取失败")
        return
    # 对象表结构：记录 = 头(23B) + 文本(00结尾)
    # 从已知记录起点 0x40 开始解析（0x155F7040 = data 偏移 0x40）
    pos = 0x40
    records = []
    while pos < len(data):
        # 头 23 字节后读文本
        tp = pos + 23
        if tp >= len(data):
            break
        end = tp
        while end < len(data) and data[end] != 0:
            end += 1
        text = data[tp:end]
        if len(text) >= 2 and len(text) <= 40:
            records.append((base + pos, text))
            print(f"  mem[{len(records)-1}] @0x{base+pos:08X}: {text.decode('shift_jis', errors='replace')}")
        # 跳到下一条：文本后填充（找下一个"头特征"：4 字节小值 + 指针？）
        # 简化：文本起点 + 文本长度 + 填充（找到下一个 0x40 对齐或头特征）
        pos = end + 1
        # 跳过填充 00
        while pos < len(data) and data[pos] == 0:
            pos += 1
        # 检查是否是记录头（第 6 字节 00 00 80 3F 特征？）
        if pos + 20 > len(data):
            break
        # 头特征：data[pos+8:pos+12] == 00 00 80 3F 或 类似
        if len(records) >= 40:
            break
    print(f"\n内存对象表记录数: {len(records)}")


if __name__ == '__main__':
    main()
