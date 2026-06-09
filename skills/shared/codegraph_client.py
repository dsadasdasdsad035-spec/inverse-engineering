"""codegraph CLI 客户端：通过 subprocess 执行 codegraph 命令，替代旧 MCP 调用。"""
import json
import subprocess
import time
from typing import Optional


class CodegraphClient:
    """封装 codegraph CLI 命令，所有交互通过 Bash 子进程完成，不依赖 MCP 服务。"""

    def __init__(self, binary: str = "codegraph", source: Optional[str] = None):
        self.binary = binary
        self.source = source

    def exec_json(self, args: list, timeout: int = 120):
        """执行命令并返回 (json_data, exit_code, duration_ms, stderr)。"""
        start = time.time()
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            duration_ms = int((time.time() - start) * 1000)
            if proc.returncode != 0:
                return None, proc.returncode, duration_ms, proc.stderr
            out = proc.stdout.strip()
            if not out:
                return [], proc.returncode, duration_ms, ""
            try:
                return json.loads(out), proc.returncode, duration_ms, ""
            except json.JSONDecodeError:
                # files 命令无匹配时返回信息文本而非 JSON，归一化为空数组
                lower = out.lower()
                if "no matching files" in lower or "no files" in lower:
                    return [], proc.returncode, duration_ms, ""
                return None, proc.returncode, duration_ms, f"非法 JSON: {out[:200]}"
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start) * 1000)
            return None, -1, duration_ms, "命令超时"
        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            return None, -1, duration_ms, f"执行异常: {exc}"

    def version(self) -> Optional[str]:
        """返回 codegraph 版本字符串，失败返回 None。"""
        data, code, _, _ = self.exec_json([self.binary, "--version"])
        if code != 0:
            return None
        if isinstance(data, dict):
            return data.get("version")
        return str(data) if data else None

    def status(self, source: str) -> Optional[dict]:
        """执行 codegraph status -j <source>，返回索引状态 dict。"""
        data, code, _, _ = self.exec_json([self.binary, "status", "-j", source])
        if code != 0 or not isinstance(data, dict):
            return None
        return data

    def files(self, source: str, entry_path: str = "", pattern: str = "**/*") -> list:
        """枚举入口下的源码文件列表。无匹配时返回空数组。"""
        args = [
            self.binary, "files", "-p", source,
            "--filter", entry_path,
            "--pattern", pattern,
            "--format", "flat", "-j",
        ]
        data, _, _, _ = self.exec_json(args)
        return data if isinstance(data, list) else []

    def query(self, source: str, file_path: str, limit: int) -> list:
        """精确路径查询：path:<file_path>，结果按 node.filePath 过滤并按 node.id 去重。"""
        args = [
            self.binary, "query", "-p", source,
            "-l", str(limit), "-j", f"path:{file_path}",
        ]
        data, _, _, _ = self.exec_json(args)
        if not isinstance(data, list):
            return []
        # 精确过滤：仅保留属于当前文件的节点
        filtered = [r for r in data if r.get("node", {}).get("filePath") == file_path]
        # 按 node.id 去重
        seen: set = set()
        unique = []
        for r in filtered:
            nid = r.get("node", {}).get("id")
            if nid not in seen:
                seen.add(nid)
                unique.append(r)
        return unique

    def callers(self, source: str, symbol: str, limit: int = 20) -> list:
        """查询调用者列表。"""
        args = [self.binary, "callers", "-p", source, "-l", str(limit), "-j", symbol]
        data, _, _, _ = self.exec_json(args)
        return data if isinstance(data, list) else []

    def callees(self, source: str, symbol: str, limit: int = 20) -> list:
        """查询被调用者列表。"""
        args = [self.binary, "callees", "-p", source, "-l", str(limit), "-j", symbol]
        data, _, _, _ = self.exec_json(args)
        return data if isinstance(data, list) else []

    # ---- 兼容旧 MCP 风格接口（转发到 CLI 实现）----

    def routes(self, source: str) -> list:
        """返回 kind==route 的所有节点（旧接口兼容）。"""
        all_sym = self.all_symbols(source)
        return [s for s in all_sym if s.get("type") == "route" or s.get("kind") == "route"]

    def all_symbols(self, source: str) -> list:
        """枚举 source 下所有文件的全部符号（旧接口兼容）。"""
        file_list = self.files(source)
        symbols = []
        seen: set = set()
        for f in file_list:
            path = f.get("path", "") if isinstance(f, dict) else str(f)
            results = self.query(source, path, limit=10000)
            for r in results:
                node = r.get("node", r)
                nid = node.get("id") or node.get("name")
                if nid not in seen:
                    seen.add(nid)
                    symbols.append(node)
        return symbols
