from src.onboarding_service import LogisticsOnboarding, OnboardingRequest


class FakeGateway:
    def __init__(self) -> None:
        self.user_calls = []
        self.session_calls = []

    def auth_user_create(self, request):
        self.user_calls.append(request)
        return {"ok": True, "data": {"user_id": "user-42"}, "error": None, "metadata": {}}

    def auth_session_create(self, request):
        self.session_calls.append(request)
        return {"ok": True, "data": {"session_id": "session-42"}, "error": None, "metadata": {}}


def test_valid_invite_accepts_and_starts_shipment():
    gateway = FakeGateway()
    result = LogisticsOnboarding({"harbor-invite-2026"}, gateway).enroll(
        OnboardingRequest("buyer@example.com", "harbor-invite-2026", "Harbor Cart")
    )

    assert result.decision == "accepted"
    assert result.shipment_events[0].name == "label_created"
    assert result.proof.filename == "delivery-photo.jpg"
    assert result.exception.resolved is False
    assert gateway.session_calls[0]["user_id"] == "user-42"


def test_unknown_invite_rejects_before_account_creation():
    gateway = FakeGateway()
    result = LogisticsOnboarding({"harbor-invite-2026"}, gateway).enroll(
        OnboardingRequest("buyer@example.com", "wrong-code", "Harbor Cart")
    )

    assert result.decision == "rejected_invite"
    assert gateway.user_calls == []
