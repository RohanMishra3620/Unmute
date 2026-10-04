import pytest
from app import create_app


class FakeClock:
    def __init__(self):
        self.t = 1_700_000_000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


@pytest.fixture
def app(tmp_path):
    return create_app({"DB_PATH": str(tmp_path / "t.db"), "LLM_API_KEY": "", "LLM_MODEL": "", "TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def clock(app):
    c = FakeClock()
    app.orchestrator.sessions.clock = c
    return c
