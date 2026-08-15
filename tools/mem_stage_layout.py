# -*- coding: utf-8 -*-
"""验证 st 文本区在内存中是否连续排列：
找 st133 起点 -> 检查 起点+133大小 处是否为 st173 内容 -> 依此类推
"""
import ctypes
import ctypes.wintypes as wt
import sys

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

STAGE_DIR = r'D:\Games\PC\MHF\MHF External tool 5.41_axibug_α\ja\stage'
STAGE_IDS = [133, 173, 174, 175, 200, 201, 202, 203, 204, 205, 210, 211, 244, 256,
             257, 260, 261, 262, 263, 264, 265, 282, 283, 286, 310, 340, 341, 379,
             397, 445]


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
    # 加载所有 st 文件
    files = {}
    for sid in STAGE_IDS:
        try:
            files[sid] = open(f'{STAGE_DIR}\\st{sid}.bin', 'rb').read()
        except FileNotFoundError:
            files[sid] = None
    # 找 st133 起点
    feat = files[133][:512]
    hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, feat)
    print("st133 特征命中:", [hex(h) for h in hits[:5]])
    if not hits:
        print("st133 未找到")
        return
    base = hits[0]
    # 验证 st133 起点内容
    mem = read_memory(pid, base, min(len(files[133]), 0x40000))
    n = 0
    while n < len(mem) and n < len(files[133]) and mem[n] == files[133][n]:
        n += 1
    print(f"st133 起点 0x{base:08X}，一致 {n}/{len(files[133])} 字节")
    if n < len(files[133]):
        print("st133 不完整，中止")
        return

    # 连续排列验证：base + len(st133) == st173 起点？
    pos = base
    print("\n连续排列验证:")
    for i, sid in enumerate(STAGE_IDS):
        data = files[sid]
        if data is None:
            continue
        mem = read_memory(pid, pos, min(len(data), 0x40000))
        if mem is None:
            print(f"  st{sid} @0x{pos:08X}: 读取失败")
            break
        n = 0
        while n < len(mem) and n < len(data) and mem[n] == data[n]:
            n += 1
        match = "OK" if n == len(data) else f"部分({n}/{len(data)})"
        print(f"  st{sid} @0x{pos:08X} ({len(data):7d}B): {match}")
        if n < len(data):
            print(f"   >>> 连续排列在第 {i} 个（st{sid}）断开")
            break
        pos += len(data)


if __name__ == '__main__':
    main()
