import asyncio

import httpx
import pytest

from app.core.config import settings
from app.utils import sms


@pytest.fixture
def providers(monkeypatch):
    calls = []

    def make(name, fail=False):
        async def send(phone, otp):
            calls.append(name)
            if fail:
                raise RuntimeError(f"{name} down")
        return send

    def install(brevo_fails=False, termii_fails=False):
        monkeypatch.setitem(sms.PROVIDERS, "brevo", make("brevo", brevo_fails))
        monkeypatch.setitem(sms.PROVIDERS, "termii", make("termii", termii_fails))
    monkeypatch.setattr(settings, "SMS_PROVIDERS", "brevo,termii")
    return calls, install


def test_brevo_is_used_first_and_termii_is_not_called(providers):
    calls, install = providers
    install()
    assert asyncio.run(sms.send_sms_otp("+2347054675026", "123456")) == "brevo"
    assert calls == ["brevo"]


def test_falls_back_to_termii_when_brevo_fails(providers):
    calls, install = providers
    install(brevo_fails=True)
    assert asyncio.run(sms.send_sms_otp("+2347054675026", "123456")) == "termii"
    assert calls == ["brevo", "termii"]


def test_raises_when_every_provider_fails(providers):
    calls, install = providers
    install(brevo_fails=True, termii_fails=True)
    with pytest.raises(Exception) as exc:
        asyncio.run(sms.send_sms_otp("+2347054675026", "123456"))
    assert "brevo: brevo down" in str(exc.value) and "termii: termii down" in str(exc.value)


def test_provider_order_is_configurable(providers, monkeypatch):
    calls, install = providers
    install()
    monkeypatch.setattr(settings, "SMS_PROVIDERS", "termii,brevo")
    assert asyncio.run(sms.send_sms_otp("+2347054675026", "123456")) == "termii"
    assert calls == ["termii"]


@pytest.mark.parametrize("raw,expected", [("+2347054675026", "2347054675026"), ("07054675026", "2347054675026"),
                                          ("234 705 467 5026", "2347054675026")])
def test_normalize_phone(raw, expected):
    assert sms.normalize_phone(raw) == expected


def _brevo_transport(events, sent):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            sent.append(request.read())
            return httpx.Response(201, json={"messageId": 99})
        return httpx.Response(200, json={"events": events})
    return httpx.MockTransport(handler)


def _run_brevo(monkeypatch, events):
    sent = []
    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(transport=_brevo_transport(events, sent), **kw))

    async def no_sleep(_):
        return None

    monkeypatch.setattr(sms.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-test")
    monkeypatch.setattr(settings, "BREVO_SMS_VERIFY_SECONDS", 4)
    asyncio.run(sms.send_via_brevo("07054675026", "123456"))
    return sent


def test_brevo_send_is_accepted_when_no_failure_event(monkeypatch):
    sent = _run_brevo(monkeypatch, [{"messageId": "99", "event": "delivered"}])
    assert b"2347054675026" in sent[0] and b"123456" in sent[0]


def test_brevo_rejected_event_raises_so_termii_can_take_over(monkeypatch):
    with pytest.raises(RuntimeError, match="rejected"):
        _run_brevo(monkeypatch, [{"messageId": "99", "event": "rejected", "reason": ""}])


def test_brevo_without_api_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "BREVO_API_KEY", "")
    with pytest.raises(RuntimeError):
        asyncio.run(sms.send_via_brevo("07054675026", "123456"))
