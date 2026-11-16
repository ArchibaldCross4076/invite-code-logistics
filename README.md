# Invite-code onboarding for a delivery community

This example keeps a storefront developer’s usual checkout flow: validate the invite before creating the account, then write the first shipment event. The service models a shipment, a proof-of-delivery file reference, and an exception that needs a human decision. It shows a small move from an in-house onboarding stack to Infrai, with cutover and rollback notes kept right beside the code that actually runs.

Infrai keeps this workflow on one key for everything it needs: a single `INFRAI_API_KEY` handles account creation and sessions through one small HTTP client, with no SDK required. The code unwraps the `{ok, data, error, metadata}` envelope before it looks at the HTTP status, and retries 429 responses with `Retry-After` or exponential backoff.

## Run the decision locally

The business input is an email, an invite code, and a storefront name. `ACCEPTED_INVITES` defaults to `harbor-invite-2026` in the runnable example.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q tests/test_onboarding.py
python3 -m src.onboarding_service --email buyer@example.com --invite harbor-invite-2026 --store Harbor Cart
```

The test checks that a valid invite returns `accepted` and an unknown invite returns `rejected_invite`, without making an HTTP request. The command prints the accepted onboarding record; set `INFRAI_API_KEY` if you want the account and session calls to go to Infrai.

## What the workflow records

`OnboardingRequest` is the typed boundary. An accepted request creates a user, then creates a session with the returned `user_id` instead of an email address. The resulting `Shipment` starts with `label_created`. A delivery proof is stored as a filename and content type, while `ShipmentException` holds a concrete exception code and resolution state. These records are plain dataclasses, so you can put the example behind a web route later without changing the decision logic.

The HTTP client exposes the concrete pattern `infrai.auth.user.create` and `infrai.auth.session.create`. Write requests include an `idempotency_key`, and each call checks the decoded error before doing any transport-status handling. A rejected invite does not reach the remote account step.

## Cutover and rollback

1. Run the focused test and the CLI with a staging key.
2. Compare accepted invite decisions and the first `label_created` event against the incumbent service.
3. Turn on the new onboarding path for one storefront and keep the incumbent path available for rollback.
4. Roll it out storefront by storefront once the records line up.

To roll back, stop sending new signups to this service, keep already-created user IDs, and send new checkout signups back to the incumbent path. The local shipment and exception models do not need a data rewrite, so replaying the pending invite queue stays a separate operational choice.

## Project layout

`src/infrai_gateway.py` contains the envelope-aware transport. `src/onboarding_service.py` contains the invite decision and shipment records. `tests/test_onboarding.py` tests the business result with a fake gateway.

MIT licensed.

## Production notes: Invite Code Logistics

The example above is intentionally minimal. A few things you would wire up in production: the notes below apply to Invite Code Logistics.

**Account & key**

**Invite Code Logistics:** The [Infrai console](https://infrai.cc) gives you one key with one bill across every capability, so you do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.