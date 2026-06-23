from agent import __main__


def test_main_loads_dotenv_before_running(monkeypatch):
    calls = []

    monkeypatch.setattr(__main__, "load_dotenv", lambda: calls.append("dotenv"))
    monkeypatch.setattr(
        __main__.asyncio,
        "run",
        lambda coroutine: (calls.append("run"), coroutine.close()),
    )

    __main__.main()

    assert calls == ["dotenv", "run"]
