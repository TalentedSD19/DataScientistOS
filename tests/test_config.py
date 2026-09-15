from backend.config import task_dir, workspace_dir, STORAGE


def test_task_dir_is_under_storage():
    assert task_dir("abc123") == STORAGE / "abc123"


def test_workspace_dir_is_under_task_dir():
    assert workspace_dir("abc123") == task_dir("abc123") / "workspace"
