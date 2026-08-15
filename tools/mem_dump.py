# -*- coding: utf-8 -*-
"""MHFZ 内存文本区 dump：确认命中地址的文本区布局"""
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


def decode(b):
    try:
        return b.decode('shift_jis', errors='replace')
    except Exception:
        return repr(b)


def dump_region(pid, addr, around=256):
    print(f"=== 0x{addr:08X} ===")
    data = read_memory(pid, addr - around, around * 2)
    if not data:
        print("读取失败")
        return None
    # 显示文本
    txt = decode(data)
    print(f"文本: ...{txt}...")
    # 找 00 边界（条目结构）
    print("条目（00 分隔）:")
    for part in data.split(b'\x00'):
        if len(part) > 0:
            print(f"  [{len(part):4d}B] {decode(part[:60])}")
    return data


def main():
    pid = int(sys.argv[1])
    addrs = [int(a, 16) for a in sys.argv[2:]]
    for a in addrs:
        dump_region(pid, a)


if __name__ == '__main__':
    main()
