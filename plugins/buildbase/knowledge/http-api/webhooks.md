# Webhooks - Verify in Any Language

Buildbase POSTs webhook events to an endpoint you host. Before trusting one, verify its signature. The SDK's `verifyWebhookSignature` / `parseWebhookEvent` do this for you on any JavaScript runtime (Node, edge, Deno, Bun), and the algorithm is plain **HMAC-SHA256**, reproducible in any language. This recipe is extracted verbatim from `sdk/src/lib/webhook-verification.ts`.

## Contents

- [The algorithm](#the-algorithm) - headers, signed message, replay window
- [Steps](#steps) - the verification order
- [Python](#python) and [Go](#go) - drop-in verifiers
- [JavaScript (the SDK already does this)](#javascript-the-sdk-already-does-this)
- [Event catalog](#event-catalog) - every event name that exists
- [`payment.failed`](#paymentfailed) - the payload of the event most apps handle first

## The algorithm

- **Headers on the incoming request:**
  - `x-buildbase-signature` - format `sha256=<hex>`
  - `x-buildbase-timestamp` - Unix epoch **in seconds** (integer)
  - `x-buildbase-event` - the event name (for example `subscription.upgraded`), so you can route before parsing. Never trust it without verifying the signature first; it is a convenience, not a proof.
  - `x-buildbase-event-id` - the event's id, the same as the body's `id` (see step 6).
  - `webhook-id`, `webhook-timestamp`, `webhook-signature` - the same delivery signed a second way, by the [Standard Webhooks](https://www.standardwebhooks.com) scheme, so a Standard Webhooks library can verify it. See [Standard Webhooks headers](#standard-webhooks-headers). Verifying either scheme is enough.
- **Signed message:** the literal string `` `${timestamp}.${rawBody}` `` - the timestamp header value, a `.`, then the **raw request body exactly as received** (do not re-serialize parsed JSON; byte-for-byte matters).
- **MAC:** `HMAC_SHA256(key = your_webhook_secret, message = "{timestamp}.{rawBody}")`, hex-encoded (lowercase).
- **Compare:** constant-time equality between the hex from the header (after stripping `sha256=`) and your computed hex.
- **Replay window:** reject if `abs(now_seconds - timestamp) > 300` (5 minutes). Configurable; `0` disables the check.
- **Fail closed:** reject if any of signature / timestamp / secret / body is missing, the prefix is wrong, the timestamp isn't a number, it's expired, or any error occurs.

## Steps

1. Read the **raw** body (before JSON parsing) and the headers.
2. Require `x-buildbase-signature` to start with `sha256=`; take the rest as `sig_hex`.
3. Parse the timestamp as an integer; reject if `|now - ts| > 300`.
4. Compute `expected = hmac_sha256_hex(secret, f"{ts}.{rawBody}")`.
5. Constant-time compare `sig_hex` vs `expected`. Accept only if equal.
6. Only then `JSON.parse` the body. The event shape is `{ id: string, event: string, timestamp: number, data: {...} }` - switch on `event` (e.g. `subscription.created`, `workspace.member_added`), using only names from the [event catalog](#event-catalog) below. **Deduplicate on `id`.** It is an opaque string starting `evt_`, the same on every endpoint and on every retry, and equal to the `x-buildbase-event-id` header. Delivery is at-least-once, so store the ids you have processed and skip a repeat. A delivery sent by a platform release older than event ids has no `id`: for one of those, deduplicate on a hash of the raw body, which a retry sends unchanged (only the signature headers are re-signed for each attempt). The SDK types `id` as optional for that reason.

## Python

```python
import hmac, hashlib, time

def verify_buildbase_webhook(raw_body: str, sig_header: str, ts_header: str,
                             secret: str, max_age_seconds: int = 300) -> bool:
    if not (raw_body and sig_header and ts_header and secret):
        return False
    if not sig_header.startswith("sha256="):
        return False
    sig_hex = sig_header[len("sha256="):]
    try:
        ts = int(ts_header)
    except ValueError:
        return False
    if max_age_seconds > 0 and abs(int(time.time()) - ts) > max_age_seconds:
        return False
    expected = hmac.new(secret.encode(), f"{ts_header}.{raw_body}".encode(),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig_hex, expected)
```

Use the raw `ts_header` string in the signed message (not a reformatted int).

## Go

```go
import ("crypto/hmac"; "crypto/sha256"; "encoding/hex"; "strconv"; "strings"; "time")

func VerifyBuildbaseWebhook(rawBody, sigHeader, tsHeader, secret string, maxAge int64) bool {
    if rawBody == "" || sigHeader == "" || tsHeader == "" || secret == "" {
        return false
    }
    if !strings.HasPrefix(sigHeader, "sha256=") {
        return false
    }
    sigHex := strings.TrimPrefix(sigHeader, "sha256=")
    ts, err := strconv.ParseInt(tsHeader, 10, 64)
    if err != nil {
        return false
    }
    if maxAge > 0 {
        if d := time.Now().Unix() - ts; d > maxAge || -d > maxAge {
            return false
        }
    }
    mac := hmac.New(sha256.New, []byte(secret))
    mac.Write([]byte(tsHeader + "." + rawBody))
    expected := hex.EncodeToString(mac.Sum(nil))
    return hmac.Equal([]byte(sigHex), []byte(expected))
}
```

## JavaScript (the SDK already does this)

On any JavaScript runtime use the SDK: `parseWebhookEvent({ body, signature, timestamp, secret })` returns the parsed event (`{ id?, event, timestamp, data }`) or `null`. It is runtime-agnostic since 0.0.50 (pure-JS HMAC, no Node `crypto`). A complete Next.js route is Step 8 of [../sdk/quick-start.md](../sdk/quick-start.md#step-8---the-webhook-route); the options and the headers are explained in [../sdk/server-side.md](../sdk/server-side.md#webhook-verification). The event names are exported too: `WEBHOOK_EVENTS`, `WebhookEventName` and `isWebhookEvent` from `@buildbase/sdk` (see the note under [Event catalog](#event-catalog) on names newer than the SDK).

## Standard Webhooks headers

Every delivery also carries `webhook-id`, `webhook-timestamp` (Unix seconds) and `webhook-signature`, a space-separated list of `v1,<base64 HMAC-SHA256 of "{webhook-id}.{webhook-timestamp}.{rawBody}">` keyed with the bytes of the same endpoint secret. Any one `v1` entry matching is enough, which is how a secret rotates without downtime. A Standard Webhooks library takes the secret as `whsec_` followed by the secret in base64.

In JavaScript, `verifyStandardWebhook({ body, id, timestamp, signature, secret })` and `parseStandardWebhookEvent(...)` from `@buildbase/sdk` (1.x) check these headers; `secret` may be the raw endpoint secret or its `whsec_` form. A delivery from a platform release older than these headers has only the `x-buildbase-*` ones, so when `webhook-signature` is absent, fall back to `verifyWebhookSignature`.

## Event catalog

Each event's exact payload is in the generated reference, one page per event at `https://docs.buildbase.app/http-api/reference/webhooks/<name with dots and underscores as hyphens>` (for example [payment-failed](https://docs.buildbase.app/http-api/reference/webhooks/payment-failed)). Read it before reading a field you have not seen in this skill.

**Names newer than the SDK.** The catalog below follows the platform. `WEBHOOK_EVENTS` in `@buildbase/sdk` 1.8.0 and 1.9.0 holds 253 of these names: `user.passkey_added`, `user.passkey_removed` and `auth.domain_unverified` came after it, so `isWebhookEvent` returns `false` for them in those releases. A handler that drops every event `isWebhookEvent` rejects drops those three; switch on the string instead, with a `default` branch, if you need them.

<!-- webhook-catalog:start (generated by scripts/render-webhook-catalog.py, do not edit by hand) -->

All 256 event names, vendored from `packages/shared/src/constants/system-events.ts` (`SYSTEM_EVENTS (ALL_WEBHOOK_EVENTS)`) at commit `e11b48052f13` on 2026-11-24. A name that is not in this list does not exist; never invent one. The same list is machine-readable in [webhook-events.json](./webhook-events.json).

**User** (`user.*`)

- `user.registered`
- `user.logged_in`
- `user.new_device_login`
- `user.email_verified`
- `user.password_changed`
- `user.password_reset_requested`
- `user.profile_updated`
- `user.tag_added`
- `user.tag_removed`
- `user.blocked`
- `user.unblocked`
- `user.mfa_enrolled`
- `user.mfa_disabled`
- `user.mfa_reset_by_admin`
- `user.email_changed`
- `user.imported`
- `user.account_linked`
- `user.account_unlinked`
- `user.passkey_added`
- `user.passkey_removed`
- `user.phone_added`
- `user.phone_verified`
- `user.phone_removed`
- `user.deletion_scheduled`
- `user.deletion_cancelled`
- `user.deleted`

**Auth** (`auth.*`)

- `auth.login_failed`
- `auth.signup_challenged`
- `auth.sms_budget_exceeded`
- `auth.method_deleted`
- `auth.domain_added`
- `auth.domain_verified`
- `auth.domain_deleted`
- `auth.domain_unverified`
- `auth.client_self_registered`

**Organization** (`organization.*`)

- `organization.member_invited`
- `organization.member_accepted`
- `organization.member_role_changed`
- `organization.member_removed`
- `organization.public_write_limit_reached`
- `organization.end_user_ceiling_reached`

**Entitlement** (`entitlement.*`)

- `entitlement.ceiling_reached`

**Workspace** (`workspace.*`)

- `workspace.created`
- `workspace.updated`
- `workspace.deleted`
- `workspace.settings_updated`
- `workspace.features_updated`
- `workspace.member_added`
- `workspace.member_removed`
- `workspace.member_role_changed`
- `workspace.member_invited`
- `workspace.invitation_accepted`
- `workspace.invitation_declined`
- `workspace.invitation_revoked`
- `workspace.invitation_expired`

**Subscription** (`subscription.*`)

- `subscription.created`
- `subscription.updated`
- `subscription.upgraded`
- `subscription.canceled`
- `subscription.cancel_scheduled`
- `subscription.resumed`
- `subscription.suspended`
- `subscription.trial_started`
- `subscription.trial_will_end`
- `subscription.trial_extended`
- `subscription.trial_expired`
- `subscription.paused`
- `subscription.unpaused`
- `subscription.retention_accepted`
- `subscription.stripe_out_of_sync`
- `subscription.margin_below_threshold`
- `subscription.downgraded`
- `subscription.discount_applied`
- `subscription.discount_removed`
- `subscription.version_move_scheduled`
- `subscription.version_moved`
- `subscription.version_move_withdrawn`

**Payment** (`payment.*`)

- `payment.succeeded`
- `payment.failed`
- `payment.action_required`
- `payment.refunded`
- `payment.card_expiring`
- `payment.stripe_events_failed`

**Quota** (`quota.*`)

- `quota.limit_exceeded`
- `quota.threshold_reached`

**Credit** (`credit.*`)

- `credit.purchased`
- `credit.consumed`
- `credit.expired`
- `credit.granted`
- `credit.revoked`
- `credit.low_balance`
- `credit.reserved`
- `credit.settled`
- `credit.released`
- `credit.threshold_crossed`
- `credit.top_up_failed`
- `credit.plan_grant_failed`

**Add-on** (`addon.*`)

- `addon.purchased`
- `addon.expired`
- `addon.revoked`
- `addon.changed`

**Payer** (`payer.*`)

- `payer.subject_added`
- `payer.subject_removed`

**Workflow** (`workflow.*`)

- `workflow.created`
- `workflow.deleted`
- `workflow.published`
- `workflow.paused`
- `workflow.resumed`
- `workflow.instance_completed`
- `workflow.instance_failed`

**Audience** (`audience.*`)

- `audience.member_created`
- `audience.member_updated`
- `audience.added_to_list`
- `audience.removed_from_list`
- `audience.attribute_changed`
- `audience.tag_added`
- `audience.tag_removed`
- `audience.unsubscribed`
- `audience.resubscribed`
- `audience.email_invalidated`
- `audience.blocked`
- `audience.unblocked`
- `audience.import_completed`
- `audience.list_created`
- `audience.list_updated`
- `audience.list_deleted`

**Email** (`email.*`)

- `email.domain_added`
- `email.domain_verified`
- `email.sent`
- `email.opened`
- `email.clicked`
- `email.bounced`
- `email.complained`
- `email.unsubscribed`
- `email.campaign_sent`

**Push** (`push.*`)

- `push.campaign_sent`

**Enterprise** (`enterprise.*`)

- `enterprise.created`
- `enterprise.deleted`
- `enterprise.domain_verified`
- `enterprise.user_provisioned`
- `enterprise.user_deprovisioned`
- `enterprise.directory_synced`
- `enterprise.certificate_expiring`
- `enterprise.certificate_renewed`
- `enterprise.policy_updated`
- `enterprise.break_glass_used`
- `enterprise.sessions_revoked`
- `enterprise.connection_activated`
- `enterprise.connection_deactivated`
- `enterprise.connection_deleted`
- `enterprise.log_stream_failing`
- `enterprise.log_stream_recovered`
- `enterprise.admin_added`
- `enterprise.admin_removed`
- `enterprise.key_created`
- `enterprise.key_revoked`
- `enterprise.group_created`
- `enterprise.group_updated`
- `enterprise.group_deleted`
- `enterprise.group_members_changed`
- `enterprise.role_created`
- `enterprise.role_updated`
- `enterprise.role_deleted`
- `enterprise.person_joined`
- `enterprise.join_requested`
- `enterprise.join_request_declined`
- `enterprise.domain_removed`
- `enterprise.app_team_session`
- `enterprise.workos_roles_attention`
- `enterprise.workos_roles_recovered`
- `enterprise.agent_issuer_updated`
- `enterprise.agent_access`
- `enterprise.sso_routing_updated`
- `enterprise.workload_credential_updated`
- `enterprise.workload_access`
- `enterprise.workspace_policy_updated`

**OAuth** (`oauth.*`)

- `oauth.consent_granted`
- `oauth.consent_revoked`

**Invoice** (`invoice.*`)

- `invoice.sent`
- `invoice.overdue`

**Token** (`token.*`)

- `token.created`
- `token.updated`
- `token.revoked`

**Group version** (`group_version.*`)

- `group_version.published`

**Version move** (`version_move.*`)

- `version_move.completed`
- `version_move.cancelled`

**Form** (`form.*`)

- `form.submitted`

**Blog** (`blog.*`)

- `blog.published`
- `blog.updated`
- `blog.unpublished`
- `blog.deleted`

**Doc** (`doc.*`)

- `doc.published`
- `doc.updated`
- `doc.unpublished`
- `doc.deleted`

**FAQ** (`faq.*`)

- `faq.updated`

**FAQ collection** (`faq_collection.*`)

- `faq_collection.updated`

**Testimonial** (`testimonial.*`)

- `testimonial.updated`
- `testimonial.deleted`

**Rich content** (`rich_content.*`)

- `rich_content.updated`
- `rich_content.deleted`

**Collection** (`collection.*`)

- `collection.version_published`
- `collection.record_created`
- `collection.record_updated`
- `collection.record_deleted`

**Item** (`item.*`)

- `item.created`
- `item.updated`
- `item.published`
- `item.rejected`
- `item.archived`

**Order** (`order.*`)

- `order.created`
- `order.paid`
- `order.refunded`
- `order.fulfilled`
- `order.disputed`
- `order.part_paid`
- `order.part_failed`
- `order.shipped`

**Shipment** (`shipment.*`)

- `shipment.updated`

**Return** (`return.*`)

- `return.requested`
- `return.updated`

**Review** (`review.*`)

- `review.created`
- `review.updated`
- `review.hidden`

**Grant** (`grant.*`)

- `grant.created`
- `grant.revoked`
- `grant.gifted`
- `grant.claimed`

**License** (`license.*`)

- `license.rotated`

**Buyer** (`buyer.*`)

- `buyer.state_changed`

**Item subscription** (`item_subscription.*`)

- `item_subscription.created`
- `item_subscription.renewed`
- `item_subscription.past_due`
- `item_subscription.recovered`
- `item_subscription.canceled`
- `item_subscription.resumed`
- `item_subscription.ended`
- `item_subscription.changed`

**Booking** (`booking.*`)

- `booking.confirmed`
- `booking.cancelled`
- `booking.rescheduled`
- `booking.updated`
- `booking.requested`
- `booking.accepted`
- `booking.declined`
- `booking.expired`

**Affiliate** (`affiliate.*`)

- `affiliate.joined`
- `affiliate.approved`
- `affiliate.status_changed`

**Commission** (`commission.*`)

- `commission.created`
- `commission.paid`
- `commission.reversed`

**Seller** (`seller.*`)

- `seller.status_changed`

**Payout** (`payout.*`)

- `payout.created`
- `payout.paid`
- `payout.failed`

<!-- webhook-catalog:end -->

## `payment.failed`

The event most apps wire first, because it is the one Stripe cannot tell your product about on its own. The platform sends it when a Stripe invoice payment attempt fails while the subscription is still being retried. `data` carries:

| Field | What it is |
|---|---|
| `subject` | who the subscription bills: `{ type: 'workspace' \| 'user', id }`. Since SDK 1.x a person can hold a subscription as well as a workspace |
| `workspaceId` | the workspace whose subscription the invoice belongs to; present only when `subject.type` is `workspace` |
| `subscriptionId` | the Stripe subscription id |
| `invoiceId` | the Stripe invoice id |
| `dunningState` | where the retry sequence stands |
| `amount` | the amount still due, in the currency's minor unit |
| `currency` | the Stripe currency code |
| `failedAt` | ISO timestamp of the failed attempt |
| `nextRetryAt` | ISO timestamp of Stripe's next attempt, or `null` when there is none (always `null` for a declined plan change, which Stripe does not retry) |

Deliveries may also carry enriched objects added by the platform (`workspace`, `subscription`, `plan`, `planVersion`, `actor`) and optional invoice details (`billingReason`, `hostedInvoiceUrl`, `subtotal`, `discount`, `tax`); treat all of them as optional, and read the [reference page](https://docs.buildbase.app/http-api/reference/webhooks/payment-failed) for the full schema. Key your handling on `subject`, not on `workspaceId` alone, or a person's subscription is skipped. There is no `failureReason` field. When the retry sequence ends in suspension, the platform sends `subscription.suspended` instead of another `payment.failed`.

**Lifecycle email is not something the webhook handler sends.** The platform already emails the customer for a failed payment through the console's notification event for `payment.failed` (with the `payment-failed` email template), and the Workflows module can trigger on the same event. Your webhook handler is for your own side effects: flag the workspace in your database, pause a job, alert your team. Do not add a second email vendor to send a message the platform already sends.
