using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace MhfPatcher;

/// <summary>
/// MHFZ 内存汉化工具（兼容 mhf-launcher 启动方式）
/// 原理：轮询游戏进程内存，检测到 st 文本区（按地图按需加载）后，
/// 用汉化工具的 zh 数据覆写（与 MHF External tool 的内存补丁相同，但动态定位地址）。
/// </summary>
class Program
{
    // ---- Win32 API ----
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out int read);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool WriteProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out int written);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool VirtualProtectEx(IntPtr h, IntPtr addr, int size, uint newProtect, out uint oldProtect);
    [DllImport("kernel32.dll")]
    static extern bool CloseHandle(IntPtr h);

    const uint PROCESS_QUERY_INFORMATION = 0x0400;
    const uint PROCESS_VM_READ = 0x0010;
    const uint PROCESS_VM_WRITE = 0x0020;
    const uint PROCESS_VM_OPERATION = 0x0008;
    const uint PAGE_READWRITE = 0x04;
    const uint PAGE_EXECUTE_READWRITE = 0x40;

    const string ToolDir = @"D:\Games\PC\MHF\MHF External tool 5.41_axibug_α";
    static readonly int[] StageIds = { 133, 173, 174, 175, 200, 201, 202, 203, 204, 205, 210, 211, 244, 256,
        257, 260, 261, 262, 263, 264, 265, 282, 283, 286, 310, 340, 341, 379, 397, 445 };

    static IntPtr _proc = IntPtr.Zero;
    static long _readFail = 0;
    static long _readOk = 0;
    static readonly Dictionary<int, byte[]> JaCache = new();
    static readonly Dictionary<int, byte[]> ZhCache = new();

    static int FindGameProcess()
    {
        foreach (var p in Process.GetProcesses())
        {
            try
            {
                var name = p.ProcessName.ToLowerInvariant();
                if (name.Contains("mhf-launcher") || name.Contains("mhfz") || name.Contains("mhf-launcher"))
                    return p.Id;
            }
            catch { }
        }
        // 后备：扫描加载 mhfo-hd.dll 的进程
        foreach (var p in Process.GetProcesses())
        {
            try
            {
                if (p.Id == 0 || p.Id == 4) continue;
                var h = OpenProcess(PROCESS_QUERY_INFORMATION, false, p.Id);
                if (h == IntPtr.Zero) continue;
                var sb = new StringBuilder(260);
                // 检查主模块
                CloseHandle(h);
                if (p.ProcessName.ToLowerInvariant().Contains("mhf"))
                    return p.Id;
            }
            catch { }
        }
        return 0;
    }

    static bool ReadMem(IntPtr addr, byte[] buf, int size)
    {
        bool ok = ReadProcessMemory(_proc, addr, buf, size, out _);
        if (ok) _readOk++; else _readFail++;
        return ok;
    }

    static bool WriteMem(IntPtr addr, byte[] data)
    {
        if (!VirtualProtectEx(_proc, addr, data.Length, PAGE_EXECUTE_READWRITE, out var old))
            VirtualProtectEx(_proc, addr, data.Length, PAGE_READWRITE, out old);
        bool ok = WriteProcessMemory(_proc, addr, data, data.Length, out _);
        VirtualProtectEx(_proc, addr, data.Length, old, out _);
        return ok;
    }

    /// <summary>全空间搜索特征串，返回命中地址列表</summary>
    static List<long> FindFeature(byte[] needle, Action<long> progress = null)
    {
        var hits = new List<long>();
        const long start = 0x00010000, end = 0x7FFEFFFF;
        const int chunk = 0x400000;
        long pos = start;
        int overlap = needle.Length - 1;
        byte[] buf = new byte[chunk];
        while (pos < end)
        {
            int size = (int)Math.Min(chunk, end - pos);
            if (ReadMem((IntPtr)pos, buf, size))
            {
                int idx = IndexOf(buf, size, needle);
                while (idx >= 0)
                {
                    hits.Add(pos + idx);
                    idx = IndexOf(buf, size, needle, idx + 1);
                }
            }
            if (size <= overlap) break;
            pos += size - overlap;
            progress?.Invoke(pos);
        }
        return hits;
    }

    static int IndexOf(byte[] hay, int len, byte[] needle, int from = 0)
    {
        for (int i = from; i + needle.Length <= len; i++)
        {
            bool ok = true;
            for (int j = 0; j < needle.Length; j++)
                if (hay[i + j] != needle[j]) { ok = false; break; }
            if (ok) return i;
        }
        return -1;
    }

    static int VerifyMatch(IntPtr addr, byte[] fileData)
    {
        int n = 0;
        byte[] buf = new byte[Math.Min(fileData.Length, 0x40000)];
        if (!ReadMem(addr, buf, buf.Length)) return 0;
        while (n < buf.Length && n < fileData.Length && buf[n] == fileData[n]) n++;
        return n;
    }

    /// <summary>覆写一个 st 文本区：定位（特征扫描）→ 验证 → 写 zh 数据</summary>
    static bool PatchStage(int stageId)
    {
        if (!JaCache.TryGetValue(stageId, out var ja) || !ZhCache.TryGetValue(stageId, out var zh))
            return false;
        var feat = ja.Take(512).ToArray();
        var hits = FindFeature(feat);
        foreach (var h in hits)
        {
            int n = VerifyMatch((IntPtr)h, ja);
            if (n < ja.Length / 2) continue; // 不是完整文本区
            // 检查是否已汉化（内容 == zh 数据）
            var cur = new byte[Math.Min(zh.Length, 0x40000)];
            ReadMem((IntPtr)h, cur, cur.Length);
            if (cur.AsSpan(0, Math.Min(cur.Length, zh.Length)).SequenceEqual(zh.AsSpan(0, Math.Min(cur.Length, zh.Length))))
            {
                Console.WriteLine($"  st{stageId} @0x{h:X8}: 已汉化，跳过");
                return true;
            }
            if (WriteMem((IntPtr)h, zh))
            {
                Console.WriteLine($"  st{stageId} @0x{h:X8}: 已覆写 {zh.Length} 字节（{ja.Length} -> {zh.Length}）");
                return true;
            }
            Console.WriteLine($"  st{stageId} @0x{h:X8}: 写入失败");
            return false;
        }
        return false;
    }

    static void Main(string[] args)
    {
        Console.WriteLine("=== MHFZ 内存汉化工具（st 文本区）===");
        Console.WriteLine("用法: MhfPatcher [--pid <进程ID>] [--once] [--interval <毫秒>]");

        int pid = 0;
        bool once = args.Contains("--once");
        int interval = 2000;
        List<int> onlyStages = null;
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--pid" && i + 1 < args.Length) pid = int.Parse(args[i + 1]);
            if (args[i] == "--interval" && i + 1 < args.Length) interval = int.Parse(args[i + 1]);
            if (args[i] == "--stage" && i + 1 < args.Length)
                onlyStages = args[i + 1].Split(',').Select(int.Parse).ToList();
        }

        // 加载汉化工具数据
        foreach (var sid in StageIds)
        {
            try
            {
                JaCache[sid] = File.ReadAllBytes($@"{ToolDir}\ja\stage\st{sid}.bin");
                ZhCache[sid] = File.ReadAllBytes($@"{ToolDir}\zh\stage\st{sid}.bin");
            }
            catch { }
        }
        Console.WriteLine($"已加载 {JaCache.Count} 个 stage 文件（ja/zh）");

        if (pid == 0) pid = FindGameProcess();
        if (pid == 0)
        {
            Console.WriteLine("未找到游戏进程（mhf-launcher），请用 --pid 指定");
            return;
        }
        Console.WriteLine($"游戏进程: {pid}");
        _proc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION, false, pid);
        if (_proc == IntPtr.Zero)
        {
            Console.WriteLine("OpenProcess 失败（请用管理员运行）");
            return;
        }

        Console.WriteLine("开始轮询（Ctrl+C 退出）...");
        while (true)
        {
            int patched = 0;
            foreach (var sid in StageIds)
            {
                if (!JaCache.ContainsKey(sid)) continue;
                if (onlyStages != null && !onlyStages.Contains(sid)) continue;
                if (PatchStage(sid)) patched++;
            }
            if (patched == 0 && once)
            {
                Console.WriteLine("本次未发现未汉化的 st 文本区");
                break;
            }
            if (once) break;
            Thread.Sleep(interval);
        }
    }
}
