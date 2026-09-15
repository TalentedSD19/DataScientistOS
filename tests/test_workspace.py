import json
import os

import pytest

from backend import workspace


@pytest.fixture
def fake_ws(tmp_path, monkeypatch):
    """Point workspace.py at a temp folder instead of storage/tasks/."""
    monkeypatch.setattr(workspace, "workspace_dir", lambda task_id: tmp_path / task_id)
    return tmp_path


def test_create_workspace_makes_all_subdirs(fake_ws):
    ws = workspace.create_workspace("task1")
    for name in workspace.SUBDIRS:
        assert (ws / name).is_dir()


def test_add_input_file_copies_and_returns_name(fake_ws, tmp_path):
    workspace.create_workspace("task1")
    source = tmp_path / "data.csv"
    source.write_text("a,b\n1,2\n")

    name = workspace.add_input_file("task1", str(source))

    assert name == "data.csv"
    assert (fake_ws / "task1" / "input" / "data.csv").read_text() == "a,b\n1,2\n"


def test_list_workspace_files_lists_relative_paths(fake_ws):
    ws = workspace.create_workspace("task1")
    (ws / "input" / "data.csv").write_text("x")
    (ws / "outputs" / "result.txt").write_text("y")

    files = workspace.list_workspace_files("task1")

    expected = sorted([os.path.join("input", "data.csv"), os.path.join("outputs", "result.txt")])
    assert files == expected


def test_save_state_writes_json(fake_ws):
    workspace.create_workspace("task1")
    path = workspace.save_state("task1", {"verifier_status": "SUFFICIENT"})

    assert path.exists()
    assert json.loads(path.read_text()) == {"verifier_status": "SUFFICIENT"}
