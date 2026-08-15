# -*- coding: utf-8 -*-
"""测试：原位替换 NPC 名对象表的文本（総合クエスト受付 -> 綜合櫃台）"""
import ctypes
import ctypes.wintypes as wt
import sys

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PAGE_EXECUTE_READWRITE = 0x40


def open_proc(pid):
    return kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION, False, pid)


def read_memory(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    if kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
        return buf.raw[:read.value]
    return None


def write_memory(h, addr, data):
    old = ctypes.c_uint32(0)
    kernel32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old))
    written = ctypes.c_size_t(0)
    ok = kernel32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(written))
    kernel32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old, ctypes.byref(ctypes.c_uint32()))
    return ok


def find_in_range(pid, start, end, needle, chunk=0x400000):
    h = open_proc(pid)
    hits = []
    pos = start
    overlap = len(needle) - 1
    while pos < end:
        size = min(chunk, end - pos)
        data = read_memory(h, pos, size)
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
    src = sys.argv[2]
    dst = sys.argv[3]
    src_b = src.encode('shift_jis')
    dst_b = dst.encode('shift_jis')
    print(f"替换: {src} ({len(src_b)}B) -> {dst} ({len(dst_b)}B)")
    if len(dst_b) > len(src_b):
        print("目标比源长，无法原位替换")
        return
    hits = find_in_range(pid, 0x00010000, 0x7FFEFFFF, src_b)
    print("命中:", [hex(h) for h in hits])
    h = open_proc(pid)
    for addr in hits:
        # 写入新文本 + 00 填充到原长度
        data = dst_b + b'\x00' * (len(src_b) - len(dst_b))
        if write_memory(h, addr, data):
            print(f"  0x{addr:08X}: 已替换")
        else:
            print(f"  0x{addr:08X}: 写入失败")
    kernel32.CloseHandle(h)
    print("完成。请重新打开对话窗口查看效果。")


if __name__ == '__main__':
    main()
