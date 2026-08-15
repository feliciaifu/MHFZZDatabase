# -*- coding: utf-8 -*-
"""验证：在进程内存中定位 st200 文本区起点（用 ja/st200.bin 文件内容做特征）"""
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
    # st200 文件前 256 字节特征
    st200 = open(r'D:\Games\PC\MHF\MHF External tool 5.41_axibug_α\ja\stage\st200.bin', 'rb').read()
    print("st200 大小:", len(st200))
    # 用文件开头 200 字节做特征（跳过可能的单字节头）
    for feat_len in [256, 512, 1024]:
        feat = st200[:feat_len]
        print(f"特征长度 {feat_len}: 搜索...")
        hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, feat)
        print(f"  命中: {[hex(h) for h in hits[:10]]}")
        if hits:
            # 验证：从命中点读 st200 大小，对比文件内容
            h = hits[0]
            mem = read_memory(pid, h, min(len(st200), 0x40000))
            if mem:
                # 找最长匹配
                n = 0
                while n < len(mem) and n < len(st200) and mem[n] == st200[n]:
                    n += 1
                print(f"  起点 0x{h:08X}，与文件一致前缀 {n} 字节")
                if n > 1000:
                    print("  >>> st200 文本区起点 = 0x%08X" % h)
                    return
    print("未找到 st200 文本区起点")


if __name__ == '__main__':
    main()
