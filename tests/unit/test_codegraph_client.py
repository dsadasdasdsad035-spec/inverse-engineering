"""CLI 版 CodegraphClient 单元测试。"""
from unittest.mock import MagicMock, patch
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from skills.shared.codegraph_client import CodegraphClient


def _mock_proc(stdout: str, returncode: int = 0, stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.returncode = returncode
    proc.stderr = stderr
    return proc


@patch("subprocess.run")
def test_files_returns_list(mock_run):
    """files() 返回 JSON 数组。"""
    mock_run.return_value = _mock_proc('[{"path": "Foo.java"}]')
    c = CodegraphClient()
    result = c.files("/src", "src/main", "**/*.java")
    assert result == [{"path": "Foo.java"}]
    # 确保调用的是 CLI 命令，不是 MCP 工具
    called_args = mock_run.call_args[0][0]
    assert called_args[0] == "codegraph"
    assert "files" in called_args


@patch("subprocess.run")
def test_files_no_match_returns_empty(mock_run):
    """files 无匹配时归一化为空数组。"""
    mock_run.return_value = _mock_proc("no matching files found", returncode=0)
    c = CodegraphClient()
    assert c.files("/src") == []


@patch("subprocess.run")
def test_query_filters_and_deduplicates(mock_run):
    """query() 按 node.filePath 过滤并按 node.id 去重。"""
    raw = [
        {"node": {"id": "1", "filePath": "A.java", "name": "foo"}},
        {"node": {"id": "2", "filePath": "B.java", "name": "bar"}},  # 不同文件，应过滤
        {"node": {"id": "1", "filePath": "A.java", "name": "foo"}},  # 重复 id，应去重
    ]
    import json
    mock_run.return_value = _mock_proc(json.dumps(raw))
    c = CodegraphClient()
    result = c.query("/src", "A.java", limit=1000)
    assert len(result) == 1
    assert result[0]["node"]["id"] == "1"


@patch("subprocess.run")
def test_routes_filters_type(mock_run):
    """routes() 只返回 kind==route 的符号（旧接口兼容）。"""
    import json
    # files 调用返回文件列表
    files_resp = [{"path": "api.ts"}]
    # query 调用返回节点列表
    nodes_resp = [
        {"node": {"id": "1", "filePath": "api.ts", "name": "create", "kind": "route"}},
        {"node": {"id": "2", "filePath": "api.ts", "name": "helper", "kind": "function"}},
    ]
    mock_run.side_effect = [
        _mock_proc(json.dumps(files_resp)),
        _mock_proc(json.dumps(nodes_resp)),
    ]
    c = CodegraphClient(source="/src")
    routes = c.routes("/src")
    assert len(routes) == 1
    assert routes[0]["name"] == "create"


@patch("subprocess.run")
def test_exec_json_nonzero_exit_returns_error(mock_run):
    """命令退出码非零时返回 (None, code, ...)。"""
    mock_run.return_value = _mock_proc("", returncode=1, stderr="索引不存在")
    c = CodegraphClient()
    data, code, _, err = c.exec_json(["codegraph", "status", "-j", "/src"])
    assert data is None
    assert code == 1
    assert "索引不存在" in err


@patch("subprocess.run")
def test_all_symbols_aggregates(mock_run):
    """all_symbols() 聚合所有文件的符号（旧接口兼容）。"""
    import json
    files_resp = [{"path": "A.java"}]
    nodes_resp = [{"node": {"id": "s1", "filePath": "A.java", "name": "foo"}}]
    mock_run.side_effect = [
        _mock_proc(json.dumps(files_resp)),
        _mock_proc(json.dumps(nodes_resp)),
    ]
    c = CodegraphClient()
    result = c.all_symbols("/src")
    assert any(s.get("name") == "foo" for s in result)
