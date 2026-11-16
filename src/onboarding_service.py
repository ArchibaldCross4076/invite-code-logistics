from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from .infrai_gateway import InfraiGateway


@dataclass(frozen=True)
class OnboardingRequest:
    email: str
    invite_code: str
    storefront: str


@dataclass(frozen=True)
class ShipmentEvent:
    name: str
    occurred_at: str


@dataclass(frozen=True)
class ProofOfDelivery:
    filename: str
    content_type: str


@dataclass(frozen=True)
class ShipmentException:
    code: str
    note: str
    resolved: bool = False


@dataclass
class OnboardingResult:
    decision: str
    user_id: str | None = None
    shipment_events: list[ShipmentEvent] = field(default_factory=list)
    proof: ProofOfDelivery | None = None
    exception: ShipmentException | None = None


class AccountGateway(Protocol):
    def auth_user_create(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def auth_session_create(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class LogisticsOnboarding:
    def __init__(self, invites: set[str], gateway: AccountGateway) -> None:
        self.invites = invites
        self.gateway = gateway

    def enroll(self, request: OnboardingRequest) -> OnboardingResult:
        if request.invite_code not in self.invites:
            return OnboardingResult(decision="rejected_invite")
        user = self.gateway.auth_user_create({
            "email": request.email,
            "password": os.environ.get("ONBOARDING_PASSWORD", "change-me"),
            "name": request.storefront,
            "metadata": {"storefront": request.storefront},
            "vendor": "in-house",
            "mode": "default_vendor",
            "idempotency_key": f"invite:{request.email}:{request.invite_code}",
        })
        user_id = str(user["data"]["user_id"])
        self.gateway.auth_session_create({
            "user_id": user_id,
            "method": "password",
            "mfa_factor": None,
            "require_mfa": False,
        })
        return OnboardingResult(
            decision="accepted",
            user_id=user_id,
            shipment_events=[ShipmentEvent("label_created", "2026-10-25T00:00:00Z")],
            proof=ProofOfDelivery("delivery-photo.jpg", "image/jpeg"),
            exception=ShipmentException("address_review", "Confirm dock number before dispatch"),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--invite", required=True)
    parser.add_argument("--store", required=True)
    args = parser.parse_args()
    result = LogisticsOnboarding(
        set(filter(None, os.environ.get("ACCEPTED_INVITES", "harbor-invite-2026").split(","))),
        InfraiGateway(),
    ).enroll(OnboardingRequest(args.email, args.invite, args.store))
    print(result)


if __name__ == "__main__":
    main()
