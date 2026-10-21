"""
Tests for the study plan service and the GET /study-plan router.

Redis, Postgres and OpenAI are all mocked.

Author: Pritam
Date: 2026-10-21
"""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _redis(cache: dict | None = None):
    """A Redis mock whose get() reads from ``cache``."""
    store = dict(cache or {})
    r = AsyncMock()
    r.get = AsyncMock(side_effect=lambda k: store.get(k))
    r.set = AsyncMock()
    r.aclose = AsyncMock()
    return r


def _pool(rows):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=rows)

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool = MagicMock()
    pool.acquire = _acquire
    return pool, conn


def _start(topic, title=None):
    return {"content": json.dumps({"room": "room-ab12cd34", "topic": topic}), "title": title}


def _llm_reply(payload):
    """An OpenAI client mock returning ``payload`` as the message content."""
    content = payload if isinstance(payload, str) else json.dumps(payload)
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=content))]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    return client


GOOD_REPLY = {
    "topics": [
        {"topic": "Momentum", "reason": "Builds on Newton's laws"},
        {"topic": "Diffraction", "reason": "Follows Light"},
        {"topic": "Energy Conservation", "reason": "Extends Why do things fall?"},
    ]
}


class TestSessionHeaders:
    @pytest.mark.asyncio
    async def test_cache_miss_reads_db_and_caches_for_24h(self):
        from services import study_plan_service as sp

        r = _redis()
        pool, conn = _pool(
            [
                _start("Light"),
                _start("__open__"),
                _start("Why do things fall?", title="My falling notes"),
                _start("light"),  # duplicate, different case
                _start("__assess__"),
                {"content": "not json", "title": None},
            ]
        )
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "get_pool", AsyncMock(return_value=pool)),
        ):
            headers = await sp.get_session_headers("alice")

        assert headers == ["Light", "My falling notes"]
        assert conn.fetch.await_args.args[1] == "alice"
        r.set.assert_awaited_once_with(
            "study_plan:headers:alice", json.dumps(headers), ex=86400
        )

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db(self):
        from services import study_plan_service as sp

        r = _redis({"study_plan:headers:alice": json.dumps(["Light"])})
        get_pool = AsyncMock()
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "get_pool", get_pool),
        ):
            assert await sp.get_session_headers("alice") == ["Light"]
        get_pool.assert_not_awaited()
        r.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_headers_capped(self):
        from services import study_plan_service as sp

        pool, _ = _pool([_start(f"Topic {i}") for i in range(50)])
        with (
            patch.object(sp.aioredis, "from_url", return_value=_redis()),
            patch.object(sp, "get_pool", AsyncMock(return_value=pool)),
        ):
            headers = await sp.get_session_headers("alice")
        assert len(headers) == sp.MAX_HEADERS


class TestNextTopics:
    @pytest.mark.asyncio
    async def test_cache_miss_calls_llm_with_headers_only_and_caches(self):
        from services import study_plan_service as sp

        r = _redis({"study_plan:headers:alice": json.dumps(["Light", "Newton's laws"])})
        client = _llm_reply(GOOD_REPLY)
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "_openai", return_value=client),
        ):
            topics = await sp.get_next_topics("alice")

        assert [t["topic"] for t in topics] == ["Momentum", "Diffraction", "Energy Conservation"]
        kwargs = client.chat.completions.create.await_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["messages"][1]["content"] == json.dumps(
            {"studied": ["Light", "Newton's laws"]}
        )
        r.set.assert_awaited_once_with(
            "study_plan:topics:alice", json.dumps(topics), ex=86400
        )

    @pytest.mark.asyncio
    async def test_cache_hit_makes_no_llm_call(self):
        from services import study_plan_service as sp

        cached = [{"topic": "Momentum", "reason": "x"}]
        r = _redis({"study_plan:topics:alice": json.dumps(cached)})
        client = _llm_reply(GOOD_REPLY)
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "_openai", return_value=client),
        ):
            assert await sp.get_next_topics("alice") == cached
        client.chat.completions.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_lessons_returns_empty_without_llm(self):
        from services import study_plan_service as sp

        r = _redis({"study_plan:headers:alice": json.dumps([])})
        client = _llm_reply(GOOD_REPLY)
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "_openai", return_value=client),
        ):
            assert await sp.get_next_topics("alice") == []
        client.chat.completions.create.assert_not_awaited()
        r.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unusable_llm_reply_still_gives_three_topics(self):
        from services import study_plan_service as sp

        r = _redis({"study_plan:headers:alice": json.dumps(["Energy and work"])})
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "_openai", return_value=_llm_reply("not json")),
        ):
            topics = await sp.get_next_topics("alice")
        assert len(topics) == 3
        assert "Energy and work" not in [t["topic"] for t in topics]
        r.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_short_llm_reply_is_topped_up_to_three(self):
        """Regression: two valid suggestions used to be shown (and cached) as two."""
        from services import study_plan_service as sp

        reply = {
            "topics": [
                {"topic": "Friction and its effects", "reason": "a"},
                {"topic": "Momentum and collisions", "reason": "b"},
            ]
        }
        r = _redis({"study_plan:headers:alice": json.dumps(["Newton's three laws"])})
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "_openai", return_value=_llm_reply(reply)),
        ):
            topics = await sp.get_next_topics("alice")
        names = [t["topic"] for t in topics]
        assert len(names) == 3
        assert names[:2] == ["Friction and its effects", "Momentum and collisions"]
        assert len({n.lower() for n in names}) == 3

    @pytest.mark.asyncio
    async def test_asks_llm_for_spare_candidates(self):
        from services import study_plan_service as sp

        r = _redis({"study_plan:headers:alice": json.dumps(["Light"])})
        client = _llm_reply(GOOD_REPLY)
        with (
            patch.object(sp.aioredis, "from_url", return_value=r),
            patch.object(sp, "_openai", return_value=client),
        ):
            await sp.get_next_topics("alice")
        system = client.chat.completions.create.await_args.kwargs["messages"][0]["content"]
        assert "exactly 5" in system


class TestCleanTopics:
    def test_filters_invalid_and_already_studied(self):
        from services.study_plan_service import _clean_topics

        raw = json.dumps(
            {
                "topics": [
                    {"topic": "Light", "reason": "already studied"},
                    {"topic": "!!! ... :::", "reason": "nothing left after cleaning"},
                    {"topic": "A" * 81, "reason": "too long"},
                    {"topic": 42},
                    "nope",
                    {"topic": "  Momentum  ", "reason": "r" * 300},
                    {"topic": "momentum", "reason": "duplicate"},
                    {"topic": "Diffraction"},
                    {"topic": "Entropy", "reason": "ok"},
                    {"topic": "Fourth", "reason": "over the limit"},
                ]
            }
        )
        topics = _clean_topics(raw, ["Light"])
        assert [t["topic"] for t in topics] == ["Momentum", "Diffraction", "Entropy"]
        assert len(topics[0]["reason"]) == 100
        assert topics[1]["reason"] == ""

    def test_punctuation_is_stripped_not_dropped(self):
        """Regression: "Work, energy, and power" was rejected for its commas."""
        from services.study_plan_service import _clean_topics

        raw = json.dumps(
            {
                "topics": [
                    {"topic": "Work, energy, and power", "reason": "r"},
                    {"topic": "Optics: lenses (and mirrors)", "reason": "r"},
                ]
            }
        )
        assert [t["topic"] for t in _clean_topics(raw, [])] == [
            "Work energy and power",
            "Optics lenses and mirrors",
        ]

    @pytest.mark.parametrize("raw", ["", "not json", "[]", '{"topics": "x"}'])
    def test_malformed_reply_gives_empty_list(self, raw):
        from services.study_plan_service import _clean_topics

        assert _clean_topics(raw, []) == []


@pytest.fixture()
def plan_client():
    from dependencies import get_current_user
    from main import app

    app.dependency_overrides[get_current_user] = lambda: "alice"
    with (
        patch("routers.study_plan.hit_rate_limit", new_callable=AsyncMock, return_value=False) as rl,
        patch("routers.study_plan.get_next_topics", new_callable=AsyncMock) as nt,
    ):
        with TestClient(app) as c:
            yield c, nt, rl
    app.dependency_overrides.clear()


class TestStudyPlanRouter:
    def test_returns_topics(self, plan_client):
        client, nt, rl = plan_client
        nt.return_value = [{"topic": "Momentum", "reason": "x"}]
        resp = client.get("/study-plan/alice")
        assert resp.status_code == 200
        assert resp.json() == {"topics": [{"topic": "Momentum", "reason": "x"}]}
        nt.assert_awaited_once_with("alice")
        assert rl.await_args.kwargs["scope"] == "study_plan"

    def test_other_identity_forbidden(self, plan_client):
        client, nt, _ = plan_client
        assert client.get("/study-plan/bob").status_code == 403
        nt.assert_not_awaited()

    def test_rate_limited(self, plan_client):
        client, nt, rl = plan_client
        rl.return_value = True
        assert client.get("/study-plan/alice").status_code == 429
        nt.assert_not_awaited()

    def test_failure_returns_503(self, plan_client):
        client, nt, _ = plan_client
        nt.side_effect = ConnectionError("down")
        assert client.get("/study-plan/alice").status_code == 503

    def test_unauthenticated_returns_401(self, client):
        assert client.get("/study-plan/alice").status_code == 401
