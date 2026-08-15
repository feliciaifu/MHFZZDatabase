# -*- coding: utf-8 -*-
"""扫描内存中所有已加载的 st 文本区 + quests 文本池"""
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


def verify(pid, addr, file_data):
    """验证 addr 处内容与文件一致，返回一致字节数"""
    mem = read_memory(pid, addr, min(len(file_data), 0x40000))
    if mem is None:
        return 0
    n = 0
    while n < len(mem) and n < len(file_data) and mem[n] == file_data[n]:
        n += 1
    return n


def main():
    pid = int(sys.argv[1])
    print("=== st 文本区扫描 ===")
    for sid in STAGE_IDS:
        try:
            data = open(f'{STAGE_DIR}\\st{sid}.bin', 'rb').read()
        except FileNotFoundError:
            continue
        feat = data[:512]
        hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, feat)
        if hits:
            for h in hits[:2]:
                n = verify(pid, h, data)
                status = "完整加载" if n == len(data) else f"部分({n}/{len(data)})"
                print(f"  st{sid} @0x{h:08X} ({len(data):7d}B): {status}")
        else:
            print(f"  st{sid}: 未加载")

    print("\n=== quests 文本池扫描 ===")
    for fname, needle in [("quests.bin", None)]:
        ja = open(rf'D:\Games\PC\MHF\MHF External tool 5.41_axibug_α\ja\{fname}', 'rb').read()
        entries = ja.split(b'\x00')
        # 用第 2-3 个较长条目做特征（跳过首条）
        feats = [e for e in entries if len(e) >= 20][:3]
        print(f"quests.bin 特征条目: {[e[:20] for e in feats]}")
        for i, feat in enumerate(feats):
            hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, feat)
            if hits:
                print(f"  特征{i}: 命中 {[hex(h) for h in hits[:5]]}")
                # 验证：命中点向前找文本池起点（特征条目前面的 00 边界）
                for h in hits[:1]:
                    # 向前找 00 边界
                    pos = h
                    while pos > 0x10000:
                        chunk = read_memory(pid, pos - 0x1000, 0x1000)
                        if chunk is None:
                            break
                        # 在 chunk 里找最后一个 00 之前的边界
                        idx = chunk.rfind(b'\x00')
                        if idx >= 0:
                            # 特征前 0x1000 范围内找
                            pass
                        break
            else:
                print(f"  特征{i}: 未找到")


if __name__ == '__main__':
    main()
