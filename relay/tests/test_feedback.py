"""POST /feedback (tester mode, D19), with telemetry mocked. OWNER: A (potencialbg). No Azure packages, no keys."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from audiostands.qa.bundle import load_bundle
from relay.app import create_app
from relay.feedback import MAX_BYTES, TEXT_MAX, FeedbackCaps, Invalid, validate
from relay.telemetry import make_tracker

B = load_bundle()
SITE = "https://lively-ocean-0efe4ae0f.2.azurestaticapps.net"
OK = {"v": 1, "kind": "clip", "tester": "t-0123abcd", "eid": "89abcdef", "group": "A", "clip": 1,
      "where": "left_close", "side": "far", "danger": "navy", "scored": "navy",
      "where_ok": 1, "side_ok": 1, "danger_ok": 1, "scored_ok": 1, "enjoy": 4, "access": 3, "follow": 5}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("FEEDBACK_ORIGINS", SITE)
    events: list[tuple[str, dict]] = []

    def make(caps: FeedbackCaps | None = None, track=None):
        async def fail():
            raise ConnectionError("no voice live in tests")
        a = create_app(bundle=B, connect=fail, mount_mcp=False, feedback_caps=caps,
                       track=track or (lambda name, props: events.append((name, props))))
        return TestClient(a), events
    return make


def post(c: TestClient, body, origin: str = SITE, **kw):
    data = body if isinstance(body, (bytes, str)) else json.dumps(body)
    return c.post("/feedback", content=data, headers={"origin": origin, "content-type": "text/plain;charset=UTF-8", **kw})


def test_valid_event_is_logged_as_tester_feedback_without_the_ip(app):
    c, events = app()
    r = post(c, OK, **{"x-forwarded-for": "203.0.113.7"})
    assert r.status_code == 202 and r.json() == {"ok": True}
    assert r.headers["access-control-allow-origin"] == SITE
    [(name, props)] = events
    assert name == "tester_feedback"
    assert props["tester"] == "t-0123abcd" and props["enjoy"] == "4" and props["where_ok"] == "1"
    assert all(isinstance(v, str) for v in props.values())
    assert "203.0.113.7" not in json.dumps(props)


@pytest.mark.parametrize("bad", [
    {**OK, "email": "a@b.c"},                 # no free-form keys
    {**OK, "kind": "spam"},
    {**OK, "enjoy": 6},
    {**OK, "enjoy": True},                    # a bool is not a 1-5 answer
    {**OK, "tester": "Nikolay"},
    {k: v for k, v in OK.items() if k != "eid"},
    [OK],
])
def test_bad_events_are_refused(app, bad):
    c, events = app()
    r = post(c, bad)
    assert r.status_code == 400 and r.json()["error"] == "invalid"
    assert events == []


def test_not_json(app):
    c, events = app()
    assert post(c, b"\xff\xfe").status_code == 400
    assert post(c, "{nope").status_code == 400
    assert events == []


def test_text_is_trimmed_capped_and_cleaned():
    props = validate({**OK, "kind": "overall", "confusing": "  " + "Ж" * (TEXT_MAX + 50) + "  ",
                      "liked": "the\x00 crowd\n", "would_use": "   "})
    assert props["confusing"] == "Ж" * TEXT_MAX
    assert props["liked"] == "the crowd"
    assert "would_use" not in props            # empty after trimming: left out


def test_body_over_4_kb_is_refused(app):
    c, events = app()
    big = json.dumps({**OK, "kind": "overall", "confusing": "x" * MAX_BYTES})
    assert post(c, big).status_code == 413
    assert events == []


def test_other_origins_may_not_post(app):
    c, events = app()
    assert post(c, OK, origin="https://evil.example").status_code == 403
    r = c.post("/feedback", content=json.dumps(OK))   # no Origin at all (not a browser on our page)
    assert r.status_code == 403
    assert events == []


def test_preflight_allows_post_for_the_site_only(app):
    c, _ = app()
    ok = c.options("/feedback", headers={"origin": SITE, "access-control-request-method": "POST"})
    assert ok.status_code == 204
    assert ok.headers["access-control-allow-origin"] == SITE
    assert ok.headers["access-control-allow-methods"] == "POST"
    bad = c.options("/feedback", headers={"origin": "https://evil.example", "access-control-request-method": "POST"})
    assert bad.status_code == 403 and "access-control-allow-origin" not in bad.headers


def test_other_routes_still_allow_only_get_in_cors(app, monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", SITE)
    c, _ = app()
    r = c.options("/health", headers={"origin": SITE, "access-control-request-method": "POST"})
    assert r.status_code == 400                  # Starlette's CORS refuses the method: unchanged from before


def test_rate_limit_per_ip(app):
    now = [1_000_000.0]
    c, events = app(caps=FeedbackCaps(per_ip=3, window_s=600, clock=lambda: now[0]))
    ip = {"x-forwarded-for": "198.51.100.1"}
    assert [post(c, OK, **ip).status_code for _ in range(4)] == [202, 202, 202, 429]
    assert post(c, OK, **{"x-forwarded-for": "198.51.100.2"}).status_code == 202   # another IP is not affected
    now[0] += 601
    assert post(c, OK, **ip).status_code == 202
    assert len(events) == 5


def test_daily_cap(app):
    c, events = app(caps=FeedbackCaps(daily=2))
    codes = [post(c, OK, **{"x-forwarded-for": f"192.0.2.{i}"}).status_code for i in range(3)]
    assert codes == [202, 202, 429]


def test_telemetry_failure_is_503_so_the_browser_keeps_the_answers(app):
    def boom(name, props):
        raise RuntimeError("exporter down")
    c, _ = app(track=boom)
    assert post(c, OK).status_code == 503


def test_every_schema_choice_the_browser_can_send_is_valid():
    # The same names as web/src/tester/questions.ts; a drift there fails here or in vitest.
    validate({"v": 1, "kind": "problem", "tester": "t-00000000", "eid": "00000000", "problem_kind": "stuck",
              "problem_text": "It stopped", "ctx_task": 2, "ctx_playhead": 701.25, "ctx_playing": True,
              "ctx_club": "A", "ctx_crowd": 50, "ctx_haptics": "events", "ctx_browser": "samsung",
              "ctx_os": "android", "ctx_viewport": "390x844", "ctx_relay": False})
    validate({"v": 1, "kind": "settings", "tester": "t-00000000", "eid": "00000001",
              "settings_changed": "club,crowd,haptics", "settings_easy": "partly"})
    with pytest.raises(Invalid):
        validate({"v": 1, "kind": "settings", "tester": "t-00000000", "eid": "00000002", "settings_changed": "club,"})


def test_tracker_without_a_connection_string_writes_stdout(capsys):
    track, where = make_tracker({})
    assert where.startswith("stdout")
    track("tester_feedback", {"tester": "t-0123abcd"})
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line == {"event": "tester_feedback", "tester": "t-0123abcd"}
