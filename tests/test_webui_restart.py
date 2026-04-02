import asyncio

from src.web.routes import settings as settings_routes


def test_write_reload_trigger_updates_python_file(tmp_path, monkeypatch):
    target = tmp_path / "reload_trigger.py"
    monkeypatch.setattr(settings_routes, "RELOAD_TRIGGER_PATH", target)

    token = settings_routes._write_reload_trigger()

    assert token.startswith("reload-")
    content = target.read_text(encoding="utf-8")
    assert token in content
    assert "RELOAD_TOKEN" in content


def test_write_reload_trigger_creates_parent_directory(tmp_path, monkeypatch):
    target = tmp_path / "nested" / "reload_trigger.py"
    monkeypatch.setattr(settings_routes, "RELOAD_TRIGGER_PATH", target)

    settings_routes._write_reload_trigger()

    assert target.exists()


def test_restart_webui_schedules_hot_reload(monkeypatch):
    class DummyBackgroundTasks:
        def __init__(self):
            self.tasks = []

        def add_task(self, fn, *args, **kwargs):
            self.tasks.append((fn, args, kwargs))

    async def runner():
        monkeypatch.setenv("WEBUI_HOT_RELOAD_ENABLED", "1")
        tasks = DummyBackgroundTasks()
        result = await settings_routes.restart_webui(tasks)
        assert result["success"] is True
        assert result["mode"] == "hot_reload"
        assert "热重载" in result["message"]
        assert tasks.tasks
        assert tasks.tasks[0][0] is settings_routes._write_reload_trigger

    asyncio.run(runner())


def test_restart_webui_schedules_process_restart(monkeypatch):
    class DummyBackgroundTasks:
        def __init__(self):
            self.tasks = []

        def add_task(self, fn, *args, **kwargs):
            self.tasks.append((fn, args, kwargs))

    async def runner():
        monkeypatch.setenv("WEBUI_HOT_RELOAD_ENABLED", "0")
        tasks = DummyBackgroundTasks()
        result = await settings_routes.restart_webui(tasks)
        assert result["success"] is True
        assert result["mode"] == "process_restart"
        assert "进程重启" in result["message"]
        assert tasks.tasks
        assert tasks.tasks[0][0] is settings_routes._restart_current_process

    asyncio.run(runner())
