import pytest
import text_to_sql


class FakeLLM:
    """Queue-based fake: each .generate() call pops the next scripted
    response, or raises it if it's an Exception. Records every prompt it
    received in .prompts for assertions."""
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class FakeCursor:
    def __init__(self, cols, rows):
        self.description = [(c,) for c in cols]
        self._rows = rows
    def execute(self, sql):
        pass
    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, cols, rows):
        self._cols, self._rows = cols, rows
    def cursor(self):
        return FakeCursor(self._cols, self._rows)
    def close(self):
        pass


class QueuedConnFactory:
    """Each call returns a FakeConn seeded with the next (cols, rows) pair.
    Needed because run_query() is hit at up to 3 different call sites per
    ask() call (catalog fetch, fields fetch, actual query), each expecting
    different results."""
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.call_count = 0
    def __call__(self):
        self.call_count += 1
        cols, rows = self.responses.pop(0)
        return FakeConn(cols, rows)


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def fake_conn_factory():
    return QueuedConnFactory()


@pytest.fixture(autouse=True)
def reset_module_caches():
    """Runs before EVERY test automatically. text_to_sql caches _CATALOG,
    _FIELDS_CACHE, and _TABLE_CACHE at module level -- without this, a
    fake_conn_factory in one test can silently go unused because a previous
    test already populated the cache. This was a real gotcha hit by hand
    during development; this fixture makes it impossible to forget."""
    text_to_sql._CATALOG = None
    text_to_sql._FIELDS_CACHE.clear()
    text_to_sql._TABLE_CACHE.clear()
    yield
