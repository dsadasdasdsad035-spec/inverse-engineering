"""Unit tests for codegraph_client."""
from unittest.mock import MagicMock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from skills.shared.codegraph_client import CodegraphClient


def test_files_returns_list():
    mcp = MagicMock(return_value=[{"path": "Foo.java"}])
    c = CodegraphClient(mcp)
    assert c.files("/src") == [{"path": "Foo.java"}]


def test_routes_filters_type():
    mcp = MagicMock(return_value=[
        {"id": "1", "name": "create", "type": "route"},
        {"id": "2", "name": "helper", "type": "function"},
    ])
    c = CodegraphClient(mcp)
    assert len(c.routes("/src")) == 1


def test_all_symbols_aggregates():
    calls = [
        [{"path": "A.java"}],          # files
        [{"id": "s1", "name": "foo"}], # search A.java
    ]
    mcp = MagicMock(side_effect=calls)
    c = CodegraphClient(mcp)
    result = c.all_symbols("/src")
    assert any(s["name"] == "foo" for s in result)
