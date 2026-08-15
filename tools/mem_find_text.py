# -*- coding: utf-8 -*-
"""搜内存中指定文本的位置（NPC 名定位）"""
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


def main():
    pid = int(sys.argv[1])
    needle = sys.argv[2].encode('shift_jis')
    print("搜索:", sys.argv[2], needle.hex())
    hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, needle)
    print("命中:", [hex(h) for h in hits])
    # 展示每个命中点上下文
    for h in hits:
        data = read_memory(pid, h - 128, 256)
        if data:
            start = h - 128
            # 找条目边界
            s = 128
            while s > 0 and data[s-1] != 0:
                s -= 1
            e = 128
            while e < len(data) and data[e] != 0:
                e += 1
            txt = data[s:e].decode('shift_jis', errors='replace')
            print(f"  0x{h:08X}: {txt[:80]}")


if __name__ == '__main__':
    main()
