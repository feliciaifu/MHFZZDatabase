# -*- coding: utf-8 -*-
"""定位 quests.bin 文本池（NPC 名等）在进程内存中的位置"""
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
    tool = r'D:\Games\PC\MHF\MHF External tool 5.41_axibug_α'
    ja = open(f'{tool}\\ja\\quests.bin', 'rb').read()
    entries = ja.split(b'\x00')
    print("quests.bin 条目数:", len(entries))
    # 展示索引 5000+ 的条目（NPC 名）
    print("索引 5000+ 条目:")
    for i in range(5000, min(5117, len(entries))):
        e = entries[i]
        if len(e) > 1:
            print(f"  [{i}] {e.decode('shift_jis', errors='replace')[:30]}")
    # 用 NPC 名条目做特征搜内存
    print("\n搜索 NPC 名条目在内存中的位置:")
    for i in range(5000, min(5117, len(entries))):
        e = entries[i]
        if len(e) < 4:
            continue
        hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, e)
        if hits:
            print(f"  [{i}] '{e.decode('shift_jis', errors='replace')[:20]}' 命中: {[hex(h) for h in hits[:3]]}")
    # 也搜 quests.bin 的任务文本条目（0-100）
    print("\n搜索任务文本条目（索引 0-100）:")
    for i in range(0, 100):
        e = entries[i]
        if len(e) < 10:
            continue
        hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, e[:30])
        if hits:
            print(f"  [{i}] 命中: {[hex(h) for h in hits[:3]]}")
            break


if __name__ == '__main__':
    main()
