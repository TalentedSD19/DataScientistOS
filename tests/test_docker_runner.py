from unittest.mock import MagicMock

import docker
import pytest

from backend import docker_runner


def test_container_name():
    assert docker_runner.container_name("abc123") == "ds-task-abc123"


def test_quote_escapes_single_quotes():
    assert docker_runner._quote("it's a test") == "'it'\"'\"'s a test'"


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(docker_runner, "_client", client)
    return client


def test_get_or_create_reuses_running_container(fake_client):
    running = MagicMock(status="running")
    fake_client.containers.get.return_value = running

    container = docker_runner.get_or_create("task1")

    assert container is running
    running.start.assert_not_called()


def test_get_or_create_starts_stopped_container(fake_client):
    stopped = MagicMock(status="exited")
    fake_client.containers.get.return_value = stopped

    docker_runner.get_or_create("task1")

    stopped.start.assert_called_once()


def test_get_or_create_creates_new_container_when_missing(fake_client, tmp_path, monkeypatch):
    fake_client.containers.get.side_effect = docker.errors.NotFound("no such container")
    monkeypatch.setattr(docker_runner, "workspace_dir", lambda _: tmp_path)

    docker_runner.get_or_create("task1")

    fake_client.containers.run.assert_called_once()
    assert fake_client.containers.run.call_args.kwargs["name"] == "ds-task-task1"


def test_exec_shell_decodes_demuxed_output(monkeypatch):
    container = MagicMock()
    container.exec_run.return_value = MagicMock(exit_code=0, output=(b"hello\n", b""))
    monkeypatch.setattr(docker_runner, "get_or_create", lambda _: container)

    result = docker_runner.exec_shell("task1", "echo hello")

    assert result == {"exit_code": 0, "stdout": "hello\n", "stderr": ""}


def test_destroy_removes_existing_container(fake_client):
    docker_runner.destroy("task1")
    fake_client.containers.get.return_value.remove.assert_called_once_with(force=True)


def test_destroy_ignores_missing_container(fake_client):
    fake_client.containers.get.side_effect = docker.errors.NotFound("no such container")
    docker_runner.destroy("task1")  # should not raise
