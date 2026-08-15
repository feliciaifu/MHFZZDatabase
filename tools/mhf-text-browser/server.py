# -*- coding: utf-8 -*-
"""MHFZ 文本数据浏览器 - 后端服务器

零依赖（Python 标准库）。启动: python server.py [--port 8765]
浏览器访问: http://127.0.0.1:8765
"""
import argparse
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

# ---------------------------------------------------------------------------
# 路径配置（可按需修改，或传入 --tool-dir / --game-dir）
# ---------------------------------------------------------------------------
TOOL_DIR = r"D:\Games\PC\MHF\MHF External tool 5.41_axibug_α"   # 汉化工具目录
GAME_DIR = r"D:\Games\PC\MHF"                                     # 游戏目录

# 已知名字表（位置来自 docs/mhf-text-data-guide.md 的逆向验证）
# 每项: (文件, 起始字节偏移, 表名, 说明, ID基址偏移量)
KNOWN_TABLES = [
    ("zh/mhfdat.bin", 2177907, "物品名表", "索引 = 游戏物品ID - 1（item_hid 为 ID 的十六进制）", 1),
    ("zh/mhfdat.bin", 221641,  "防具名表", "游戏防具ID顺序：每系列先脚后头，每部位男女2件", 1),
    ("zh/mhfdat.bin", 1142878, "武器名表", "游戏武器ID顺序", 1),
    ("zh/mhfdat.bin", 0,       "装备描述区", "头部装备描述碎片（00分隔）", None),
    ("zh/quests.bin", 0,       "任务文本(zh)", "与 ja/quests.bin 按序一一对应（5116条）", None),
    ("ja/quests.bin", 0,       "任务文本(ja)", "日文原文，索引与 zh/quests.bin 对应", None),
]

# 已知配对（ja 原文 ↔ zh 译文，按条目索引一一对应）
KNOWN_PAIRS = [
    ("ja/quests.bin", "zh/quests.bin", "任务文本配对", "5116 条一一对应（已验证）"),
    ("ja/shards/mhfdat.bin", "zh/shards/mhfdat.bin", "mhfdat 片段配对", "2332 条，带内存地址"),
    ("ja/shards/mhfpac.bin", "zh/shards/mhfpac.bin", "mhfpac 片段配对", "10 条，带内存地址"),
    ("ja/load/uc00_000_00.bin", "zh/load/uc00_000_00.bin", "事件文本配对", "近似对齐（条目数略有差异，需 LCS）"),
]

# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------
class TextFile:
    """按 0x00 切分条目的文本区文件（Shift-JIS 编码）"""

    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(path)
        self._data = None

    def data(self):
        if self._data is None:
            with open(self.path, "rb") as f:
                self._data = f.read()
        return self._data

    def entries(self, max_len=None):
        """返回 [(start, end, length, text)]，max_len 限制条目字节长度（0 表示不限）"""
        data = self.data()
        out = []
        start = 0
        i = 0
        n = len(data)
        while i < n:
            if data[i] == 0:
                ln = i - start
                if ln > 0 and (max_len is None or ln <= max_len):
                    out.append((start, i, ln, decode_sjis(data[start:i])))
                start = i + 1
            i += 1
        if n - start > 0 and (max_len is None or (n - start) <= max_len):
            out.append((start, n, n - start, decode_sjis(data[start:n])))
        return out


def decode_sjis(b):
    try:
        return b.decode("shift_jis")
    except UnicodeDecodeError:
        return b.decode("shift_jis", errors="replace")


def hexdump(data, pos):
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hexs = " ".join("%02X" % c for c in chunk)
        asc = "".join(chr(c) if 32 <= c <= 126 else "." for c in chunk)
        lines.append("%08X  %-47s  %s" % (pos + off, hexs, asc))
    return lines


# ---------------------------------------------------------------------------
# 文件发现
# ---------------------------------------------------------------------------
def scan_files():
    """扫描汉化工具 + 游戏目录，返回文件树"""
    groups = []
    if os.path.isdir(TOOL_DIR):
        for sub in ["zh", "ja", "ptr"]:
            d = os.path.join(TOOL_DIR, sub)
            if os.path.isdir(d):
                files = []
                for root, dirs, names in os.walk(d):
                    for name in sorted(names):
                        if name.lower().endswith(".bin"):
                            full = os.path.join(root, name)
                            rel = os.path.relpath(full, TOOL_DIR).replace("\\", "/")
                            files.append({"path": rel, "size": os.path.getsize(full)})
                if files:
                    groups.append({"name": "汉化工具/" + sub, "files": files})
    if os.path.isdir(GAME_DIR):
        d = os.path.join(GAME_DIR, "dat")
        if os.path.isdir(d):
            files = []
            for name in sorted(os.listdir(d)):
                full = os.path.join(d, name)
                if os.path.isfile(full) and name.lower().endswith((".bin", ".txb")):
                    files.append({"path": "GAME/dat/" + name, "size": os.path.getsize(full)})
            if files:
                groups.append({"name": "游戏目录/dat", "files": files})
    return groups


def resolve_path(rel):
    """把 API 里的相对路径解析为磁盘路径"""
    rel = rel.replace("\\", "/")
    if rel.startswith("GAME/"):
        return os.path.join(GAME_DIR, rel[5:])
    return os.path.join(TOOL_DIR, rel)


def table_entries(full, from_pos, max_len=40):
    """从 from_pos 开始提取连续短条目（遇到长条目/空条目即停），返回 [(start,end,len,text)]"""
    with open(full, "rb") as f:
        data = f.read()
    out = []
    p = from_pos
    n = len(data)
    while p < n:
        end = p
        while end < n - 1 and data[end] != 0:
            end += 1
        ln = end - p
        if ln <= 0 or ln > max_len:
            break
        text = decode_sjis(data[p:end])
        if len(text) < 2:
            break
        out.append((p, end, ln, text))
        p = end + 1
    return out


def pair_entries(ja_path, zh_path):
    """按索引配对两个文件的条目，返回 (ja_entries, zh_entries, aligned_count)"""
    je = TextFile(ja_path).entries()
    ze = TextFile(zh_path).entries()
    return je, ze


# ---------------------------------------------------------------------------
# HTTP 服务器
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "MHFZTextBrowser/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg, code=400):
        self._json({"error": msg}, code)

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        q = parse_qs(url.query)
        try:
            if path == "/":
                self._serve_static("index.html")
            elif path.startswith("/static/"):
                self._serve_static(path[len("/static/"):])
            elif path == "/api/files":
                self._json(scan_files())
            elif path == "/api/tables":
                self._json({"tables": KNOWN_TABLES, "pairs": KNOWN_PAIRS})
            elif path == "/api/table":
                self._api_table(q)
            elif path == "/api/pair":
                self._api_pair(q)
            elif path == "/api/entries":
                self._api_entries(q)
            elif path == "/api/search":
                self._api_search(q)
            elif path == "/api/hex":
                self._api_hex(q)
            elif path == "/api/fileinfo":
                self._api_fileinfo(q)
            else:
                self._error("unknown path: " + path, 404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._error(str(e), 500)

    def _serve_static(self, name):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        safe = os.path.normpath(name)
        if safe.startswith(".."):
            return self._error("bad path")
        full = os.path.join(base, safe)
        if not os.path.isfile(full):
            return self._error("not found: " + name, 404)
        ctype = "text/html; charset=utf-8" if full.endswith(".html") else (
            "application/javascript; charset=utf-8" if full.endswith(".js") else (
            "text/css; charset=utf-8" if full.endswith(".css") else "application/octet-stream"))
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_path(self, q):
        if "path" not in q:
            raise ValueError("missing path")
        rel = unquote(q["path"][0])
        full = resolve_path(rel)
        if not os.path.isfile(full):
            raise ValueError("file not found: " + rel)
        return rel, full

    def _api_fileinfo(self, q):
        rel, full = self._get_path(q)
        self._json({"path": rel, "size": os.path.getsize(full)})

    def _api_table(self, q):
        rel, full = self._get_path(q)
        from_pos = int(q.get("from", ["0"])[0])
        max_len = int(q.get("maxlen", ["40"])[0])
        offset = int(q.get("offset", ["0"])[0])
        limit = int(q.get("limit", ["200"])[0])
        entries = table_entries(full, from_pos, max_len)
        total = len(entries)
        page = entries[offset:offset + limit]
        self._json({
            "path": rel, "from": from_pos, "total": total,
            "offset": offset, "limit": limit,
            "entries": [{"idx": offset + i, "start": e[0], "end": e[1],
                         "len": e[2], "text": e[3]} for i, e in enumerate(page)],
        })

    def _api_pair(self, q):
        if "ja" not in q or "zh" not in q:
            return self._error("missing ja/zh")
        ja_rel = unquote(q["ja"][0])
        zh_rel = unquote(q["zh"][0])
        ja_full, zh_full = resolve_path(ja_rel), resolve_path(zh_rel)
        if not os.path.isfile(ja_full) or not os.path.isfile(zh_full):
            return self._error("file not found")
        offset = int(q.get("offset", ["0"])[0])
        limit = int(q.get("limit", ["100"])[0])
        je, ze = pair_entries(ja_full, zh_full)
        common = min(len(je), len(ze))
        page = range(offset, min(offset + limit, common))
        self._json({
            "ja": ja_rel, "zh": zh_rel, "ja_total": len(je), "zh_total": len(ze),
            "common": common, "offset": offset, "limit": limit,
            "pairs": [{"idx": i,
                       "ja": {"start": je[i][0], "len": je[i][2], "text": je[i][3]},
                       "zh": {"start": ze[i][0], "len": ze[i][2], "text": ze[i][3]}}
                      for i in page],
        })

    def _api_entries(self, q):
        rel, full = self._get_path(q)
        offset = int(q.get("offset", ["0"])[0])
        limit = int(q.get("limit", ["100"])[0])
        max_len = int(q.get("maxlen", ["0"])[0]) or None
        entries = TextFile(full).entries(max_len=max_len)
        total = len(entries)
        page = entries[offset:offset + limit]
        self._json({
            "path": rel, "total": total,
            "offset": offset, "limit": limit,
            "entries": [{"idx": offset + i, "start": e[0], "end": e[1],
                         "len": e[2], "text": e[3]} for i, e in enumerate(page)],
        })

    def _api_search(self, q):
        rel, full = self._get_path(q)
        needle = unquote(q.get("q", [""])[0])
        if not needle:
            return self._error("missing q")
        case_sensitive = q.get("case", ["0"])[0] == "1"
        max_hits = min(int(q.get("max", ["200"])[0]), 2000)
        tf = TextFile(full)
        hits = []
        for idx, (start, end, ln, text) in enumerate(tf.entries()):
            found = text.find(needle) if case_sensitive else text.lower().find(needle.lower())
            if found >= 0:
                hits.append({"idx": idx, "start": start, "len": ln, "text": text,
                             "pos": found})
                if len(hits) >= max_hits:
                    break
        self._json({"path": rel, "q": needle, "total": len(hits), "hits": hits})

    def _api_hex(self, q):
        rel, full = self._get_path(q)
        pos = int(q.get("pos", ["0"])[0])
        length = min(int(q.get("len", ["256"])[0]), 8192)
        with open(full, "rb") as f:
            f.seek(pos)
            data = f.read(length)
        self._json({"path": rel, "pos": pos, "length": len(data),
                    "lines": hexdump(data, pos)})


def main():
    global TOOL_DIR, GAME_DIR
    ap = argparse.ArgumentParser(description="MHFZ 文本数据浏览器")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--tool-dir", default=TOOL_DIR, help="汉化工具目录")
    ap.add_argument("--game-dir", default=GAME_DIR, help="游戏目录")
    args = ap.parse_args()
    TOOL_DIR, GAME_DIR = args.tool_dir, args.game_dir
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("MHFZ 文本数据浏览器: http://127.0.0.1:%d" % args.port)
    print("汉化工具目录: %s" % TOOL_DIR)
    print("游戏目录:     %s" % GAME_DIR)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
