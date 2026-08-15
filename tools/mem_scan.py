# -*- coding: utf-8 -*-
"""MHFZ 内存文本区定位验证脚本

用法（管理员 PowerShell）:
    python mem_scan.py <特征串>

在加载了 mhfo.dll/mhfo-hd.dll 的进程中搜索特征串（Shift-JIS），
确认看板娘对话文本区在 launcher 模式下的内存位置。
"""
import ctypes
import ctypes.wintypes as wt
import sys
from ctypes import wintypes

# --- Windows API ---
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_ALL_ACCESS = 0x1F0FFF

MAX_PATH = 260
LIST_MODULES_ALL = 0x03
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = "SeDebugPrivilege"


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", wintypes.DWORD),
        ("EntryPoint", ctypes.c_void_p),
    ]


def enable_debug_privilege():
    """提升 SeDebugPrivilege（管理员运行时）"""
    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", ctypes.c_long)]

    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [("PrivilegeCount", wintypes.DWORD),
                    ("Privileges", LUID_AND_ATTRIBUTES * 1)]

    hToken = wintypes.HANDLE()
    TOKEN_ADJUST_PRIVILEGES = 0x20
    TOKEN_QUERY = 0x08
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(hToken)):
        return False
    luid = LUID()
    advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid))
    tp = TOKEN_PRIVILEGES(1, (LUID_AND_ATTRIBUTES(luid, SE_PRIVILEGE_ENABLED),))
    ok = advapi32.AdjustTokenPrivileges(hToken, False, ctypes.byref(tp),
                                        ctypes.sizeof(tp), None, None)
    kernel32.CloseHandle(hToken)
    return bool(ok)


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * MAX_PATH),
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * MAX_PATH),
        ("szExePath", ctypes.c_char * MAX_PATH),
    ]


def list_processes():
    procs = []
    h = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h == -1:
        return procs
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    if kernel32.Process32First(h, ctypes.byref(entry)):
        while True:
            procs.append((entry.th32ProcessID, entry.szExeFile.decode('utf-8', errors='replace')))
            if not kernel32.Process32Next(h, ctypes.byref(entry)):
                break
    kernel32.CloseHandle(h)
    return procs


def process_modules(pid):
    """用 EnumProcessModulesEx 枚举模块（可靠支持 64 位调用者枚举 32 位进程）"""
    mods = []
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return mods
    try:
        buf = (ctypes.c_void_p * 1024)()
        needed = wintypes.DWORD(0)
        if not psapi.EnumProcessModulesEx(h, buf, ctypes.sizeof(buf), ctypes.byref(needed), LIST_MODULES_ALL):
            return mods
        count = needed.value // ctypes.sizeof(ctypes.c_void_p)
        for i in range(count):
            hmod = buf[i]
            name_buf = ctypes.create_unicode_buffer(MAX_PATH)
            if psapi.GetModuleBaseNameW(h, hmod, name_buf, MAX_PATH):
                mi = MODULEINFO()
                psapi.GetModuleInformation(h, hmod, ctypes.byref(mi), ctypes.sizeof(mi))
                mods.append((name_buf.value, mi.lpBaseOfDll, mi.SizeOfImage))
    finally:
        kernel32.CloseHandle(h)
    return mods


def read_memory(pid, addr, size):
    """打开进程句柄后读取内存"""
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


def find_in_range(pid, start, end, needle, chunk=0x400000, on_progress=None):
    """分段读内存并搜索特征串"""
    hits = []
    pos = start
    overlap = len(needle) - 1
    total = end - start
    last_pct = -1
    while pos < end:
        size = min(chunk, end - pos)
        data = read_memory(pid, pos, size)
        if data:
            idx = data.find(needle)
            while idx >= 0:
                hits.append(pos + idx)
                idx = data.find(needle, idx + 1)
        if size <= overlap:
            break  # 最后一块已读完，避免死循环
        pos += size - overlap
        if on_progress:
            pct = int((pos - start) * 100 / total)
            if pct // 5 != last_pct:
                last_pct = pct // 5
                on_progress(pct)
    return hits


def main():
    import argparse
    ap = argparse.ArgumentParser(description="MHFZ 内存文本区定位")
    ap.add_argument("needle", help="特征串（Shift-JIS）")
    ap.add_argument("--pid", type=int, default=0, help="直接指定进程 PID")
    args = ap.parse_args()
    needle = args.needle.encode('shift_jis')
    print("特征串(Shift-JIS):", needle.hex())
    if enable_debug_privilege():
        print("SeDebugPrivilege: 已启用")
    else:
        print("SeDebugPrivilege: 未启用（建议管理员运行）")

    if args.pid:
        targets = [(args.pid, f"pid-{args.pid}", [], [])]
    else:
        procs = list_processes()
        print("进程数:", len(procs))
        targets = []
        for pid, name in procs:
            try:
                mods = process_modules(pid)
            except Exception as e:
                continue
            mhfo = [m for m in mods if 'mhfo' in m[0].lower()]
            if mhfo:
                targets.append((pid, name, mods, mhfo))
                print(f"  [{pid}] {name}: mhfo 模块 {[m[0] for m in mhfo]}")

    if not targets:
        print("未找到目标进程。请用管理员 PowerShell 运行，或指定 --pid <进程ID>。")
        print("游戏进程 PID 可通过任务管理器查看（含 mhfo.dll 的进程）。")
        return

    for pid, name, mods, mhfo in targets:
        print(f"\n=== 扫描进程 [{pid}] {name} ===")
        # 获取模块列表（验证权限）
        try:
            mods = process_modules(pid)
            if mods:
                print(f"模块数: {len(mods)}，mhfo: {[m[0] for m in mods if 'mhfo' in m[0].lower()]}")
            else:
                print("模块枚举失败（权限不足？请用管理员运行）")
        except Exception as e:
            print("模块枚举异常:", e)
        # 优先扫描 mhfo-hd.dll / mhfo.dll 模块的内存范围
        scan_ranges = []
        for mn, mb, ms in mods:
            if 'mhfo' in mn.lower():
                scan_ranges.append((mb, mb + ms, mn))
        if not scan_ranges:
            scan_ranges = [(0x00010000, 0x7FFEFFFF, "全空间")]
            print("mhfo 模块不可见，扫描整个 32 位地址空间（建议用管理员运行）")
        else:
            print(f"扫描模块范围: {[(r[2], hex(r[0]), hex(r[1])) for r in scan_ranges]}")
        all_hits = []
        for start, end, label in scan_ranges:
            hits = find_in_range(pid, start, end, needle,
                                 on_progress=lambda p: print(f"  [{label}] 扫描进度: {p}%", flush=True))
            if hits:
                print(f"[{label}] 找到 {len(hits)} 处:")
                for h in hits[:20]:
                    owner = "?"
                    for mn, mb, ms in mods:
                        if mb <= h < mb + ms:
                            owner = f"{mn}+0x{h-mb:X}"
                            break
                    print(f"  0x{h:08X} ({owner})")
                all_hits.extend(hits)
        if not all_hits:
            print("未找到特征串（进程可能无读取权限，请用管理员运行）")


if __name__ == '__main__':
    main()
