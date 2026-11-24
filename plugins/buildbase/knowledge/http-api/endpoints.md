# HTTP API - Endpoint Catalog

Every endpoint the `@buildbase/sdk` calls, extracted from source at **1.8.0** (`sdk/src/api/services/*-api.ts`, `sdk/src/lib/api-base.ts`, `sdk/src/lib/server-client.ts`, `sdk/src/lib/auth-code-exchange.ts`, `sdk/src/lib/checkout-status.ts`, `sdk/src/lib/resolve-server-url.ts`, `sdk/src/tracking/*`, `sdk/src/analytics/client.ts`, `sdk/src/lib/agent-discovery.ts`, `sdk/src/lib/server-content/client.ts`, `sdk/src/lib/server-messaging/client.ts`, `sdk/src/lib/server-commerce/client.ts`, `sdk/src/lib/inbox-socket.ts`). Paths below are the part after the base. Unless noted, the full URL is:

```
{serverUrl}/api/{version}/public/{path}      e.g. https://api.console.buildbase.app/api/v1/public/workspaces
```

All session-authenticated calls send `x-session-id: <sessionId>`, and since 1.2.0 also `x-org-id: <tenant>` (the org id, or `<orgId>-<key>` in a development or staging environment); the browser SDK also sends a best-effort `x-device-id`. Every interpolated path segment is URL-encoded, and an id that is `.` or `..` is refused before anything is sent. Bodies are JSON (`Content-Type: application/json`). Billing and commerce writes carry an `Idempotency-Key` header ([overview.md](./overview.md#6-idempotency)). See [overview.md](./overview.md) for envelope/error rules. Webhook event names are a separate catalog: [webhooks.md](./webhooks.md#event-catalog).

This is what the SDK sends, not everything the server has. For one operation's exact contract (auth, parameters, request and responses), read the generated reference at [docs.buildbase.app/http-api](https://docs.buildbase.app/http-api) (built from the platform's `openapi/public-v1.json`), or call the hosted BuildBase MCP server's `get_api_operation` tool with `METHOD /path`.

## Contents

- [Auth](#auth) - login request, code to session exchange, sign-out, device token, re-confirming
- [Profile & Users](#profile--users) - profile, attributes, user features
- [Account security](#account-security) - email, phone, password, username, two-step, connected accounts, deletion, guests
- [Passkeys, devices, sessions, connected agents](#passkeys-devices-sessions-connected-agents) - the signed-in user's own security surface
- [Settings (org-scoped, public path)](#settings-org-scoped-public-path) - org/OS settings
- [Workspaces & Members](#workspaces--members) - CRUD and membership
- [Workspace invitations](#workspace-invitations) - inviting an address that has no account yet (0.0.71)
- [Features](#features) - workspace feature definitions and toggles
- [Billing subjects: a workspace or `me`](#billing-subjects-a-workspace-or-me) - the same routes for a person's own plan
- [Subscription](#subscription) - checkout, change, cancel, pause, billing portal, cards, invoices
- [Plans](#plans) - plan groups and public plan lookups
- [Invoices](#invoices) - list, fetch, pay
- [Usage / Quota](#usage--quota) - record usage and quota status
- [Limits and entitlements](#limits-and-entitlements) - claims against limits, the composed entitlement
- [Credits](#credits) - balance, consume, holds, auto top-up, purchase
- [Add-ons](#add-ons) - offers, purchase, upgrade, decrease, cancel, grants
- [Notifications](#notifications) - send, schedule, events, preferences, delivered items
- [Push](#push) - VAPID key, subscribe, unsubscribe
- [Permissions](#permissions) - the server's answer, and the local fallback
- [Enterprise](#enterprise) - a workspace's company (SSO, directory, roles, audit)
- [Commerce](#commerce) - catalog, checkout, orders, holdings, bookings, selling, affiliates, reviews
- [Guests and licence checks](#guests-and-licence-checks) - the `guest` and `licenses` basePaths
- [Unauthenticated org-scoped routes](#unauthenticated-org-scoped-routes) - tracking, analytics, consent, checkout return, agent readiness, invitation preview
- [Beta](#beta) - the `beta` basePath
- [Org-token routes the SDK calls](#org-token-routes-the-sdk-calls) - a named person's billing, `@buildbase/sdk/server`, central
- [Called by your app, not by the SDK](#called-by-your-app-not-by-the-sdk) - the token exchange

---

## Auth

The `auth/*` routes sit **outside** `/public`.

| Purpose | Method | Path | Auth | Body / Query | Response |
|---|---|---|---|---|---|
| Start login - get the provider redirect URL | POST | `/api/{version}/auth/request` | none | `{ orgId, clientId, redirect: { success, error }, state?, trackingConsent?, trackingIdentity?, trackingAttribution?, invitationToken?, notice?: { reason, minutes? }, locale? }` (all but the first three optional; the SDK resends without the newer fields when an older server answers 400) | `{ success, data: { redirectUrl }, message }` |
| Code to session exchange (server-side, with the secret) | POST | `/api/v1/auth/token` | client secret in body | `{ code, orgId, clientId, clientSecret }` (`orgId` is `<orgId>-<key>` in an environment) | `{ data: { sessionId, user } }`. Called by `exchangeAuthCode` / `BuildBase().exchangeCode` (1.6.0) and `createAuthHandler` |
| The org's sign-in options (username policy, account-deletion grace days) | GET | `/api/{version}/auth/config?org={orgId}` | none | - | the org's public auth config |
| Redeem a sign-in-as ticket | POST | `/api/{version}/auth/impersonation/redeem` | none | `{ orgId, clientId, ticket, state }` | a read-only session for the support view |
| Get current user's profile (also validates the session) | GET | `public/profile` | `x-session-id` | - | the profile, identified by `id` (current servers send no `_id`; the SDK copies `id` into `_id`) |
| How and when this session was proved | GET | `public/session` | `x-session-id` | - | how it began, when its person last proved who they are (`amr`), whether it can be re-confirmed; 404 on an older server |
| Re-confirm the session (start / finish) | POST | `public/session/reverify`, `public/session/reverify/complete` | `x-session-id` | start: return URL, PKCE challenge, optional `purpose`; finish: `{ code, codeVerifier }` | refusals `reverify_unavailable`, `invalid_return_url`, `invalid_reverify_code` (400) |
| Sign out: revoke the session server-side (0.0.70) | POST | `public/logout` | `x-session-id` | `{ all: true }` to revoke every session of the user; otherwise no body | empty. Idempotent; answers for an already-expired id too |
| Device token, echoed back as `x-device-id` (0.0.57) | GET | `public/device-token` | `x-session-id` | - | `{ deviceToken }`; `''` for agent/machine sessions. Best-effort: the SDK swallows failures |

---

## Profile & Users

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Get profile | GET | `public/profile` | - | the profile (`id`, `name`, `email`, ...) |
| Update profile | PATCH | `public/profile` | `Partial<IUser>` | the profile |
| Get user attributes | GET | `public/users/attributes` | - | `Record<string, string\|number\|boolean>` |
| Bulk-update attributes | PATCH | `public/users/attributes` | `{ attributes: Record<string, …> }` | the user |
| Update one attribute | PATCH | `public/users/attributes/{attributeKey}` | `{ value }` | the user |
| Get resolved user feature flags | GET | `public/users/features` | - | `Record<string, boolean>` |

Profile fields: `{ id, name, email, image?, role, country?, timezone?, language?, currency?, attributes?, mfaEnabled?, canChangeEmail?, phone?, phoneVerified?, username?, claims?, isAnonymous?, createdAt, updatedAt }`. Read `id`; `_id` is kept within 1.x only for older code.

---

## Account security

The signed-in user's own account. All `x-session-id`, none take a workspace id. Several answer 401 for a refusal of their own (an expired code) while the session is fine; read the body's `code` before treating a 401 as signed out.

| Purpose | Method | Path |
|---|---|---|
| Change password | POST | `public/profile/password` |
| Change email: send a code, then confirm it | POST | `public/profile/email` (`{ newEmail }`), `public/profile/email/confirm` |
| Add a phone (SMS or WhatsApp code), confirm it, remove it | POST / POST / DELETE | `public/profile/phone` (`{ phone, channel? }`), `public/profile/phone/confirm`, `public/profile/phone` |
| Set or remove a username | PUT / DELETE | `public/profile/username` |
| Two-step status | GET | `public/mfa` |
| Authenticator app: enroll, confirm, disable | POST | `public/mfa/totp/enroll`, `public/mfa/totp/confirm`, `public/mfa/totp/disable` |
| SMS second step: enroll, confirm, disable | POST | `public/mfa/sms/enroll`, `public/mfa/sms/enroll/confirm`, `public/mfa/sms/disable` |
| New backup codes | POST | `public/mfa/backup-codes/regenerate` |
| Connected sign-in accounts: list, link, finish linking, unlink | GET / POST / POST / DELETE | `public/accounts`, `public/accounts`, `public/accounts/complete`, `public/accounts/{accountId}` |
| Link a wallet (nonce, then signed message) | POST | `public/accounts/wallet/nonce`, `public/accounts/wallet` |
| Request or cancel account deletion | POST | `public/account/delete`, `public/account/delete/cancel` |
| A guest becomes a full account (send, confirm) | POST | `public/guest/upgrade`, `public/guest/upgrade/confirm` |

---

## Passkeys, devices, sessions, connected agents

The signed-in user's own security surface. All take `x-session-id`; none take a workspace id.

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| List passkeys | GET | `public/passkeys` | - | `{ passkeys: IPasskeySummary[] }`. Enrollment is not here: WebAuthn credentials are bound to the hosted auth domain and registered during sign-in |
| Rename a passkey | PATCH | `public/passkeys/{passkeyId}` | `{ name }` | empty |
| Remove a passkey | DELETE | `public/passkeys/{passkeyId}` | - | empty |
| List devices signed in from (0.0.57) | GET | `public/devices` | - | `{ devices: IDeviceView[] }` |
| Rename a device | PATCH | `public/devices/{deviceId}` | `{ name }` | empty |
| Sign a device out (revoke its live sessions, keep the row) | DELETE | `public/devices/{deviceId}` | - | `{ revokedSessions }` |
| Forget a device (sign out and delete the row) | DELETE | `public/devices/{deviceId}?forget=true` | - | `{ revokedSessions }` |
| List live sessions (0.0.57) | GET | `public/sessions` | - | `{ sessions: ISessionView[] }` |
| Revoke one other session | DELETE | `public/sessions/{id}` | - | empty. Revoking the current one is `POST logout` |
| List connected agents (0.0.51) | GET | `public/connected-agents` | - | `{ agents: IConnectedAgent[] }` |
| Disconnect an agent | POST | `public/connected-agents/revoke` | `{ clientId }` | empty |
| Link this browser's analytics visitor to the user | POST | `public/analytics/link` | `{ vid }` | 200 when linked |
| Upload a file (end-user uploads) | POST, then PUT, then POST | `public/uploads` (an upload intent with a signed URL), the signed URL itself (no session sent), `public/uploads/{uploadId}/complete` | `{ purpose, name, size, contentType }`, then the file bytes | the stored file |

---

## Settings (org-scoped, public path)

| Purpose | Method | Path | Response |
|---|---|---|---|
| Get org/OS settings | GET | `public/{orgId}/settings` | `ISettings` (includes the workspace permission template) |

---

## Workspaces & Members

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| List workspaces | GET | `public/workspaces` | - | `IWorkspace[]` |
| Create workspace | POST | `public/workspaces` | `{ name, image?, trackingAttribution?: { params, capturedAt?, landingUrl? } }` (the SDK retries without `trackingAttribution` when an older server answers 400) | `IWorkspace` |
| Get one workspace | GET | `public/workspaces/{workspaceId}` | - | `IWorkspace` |
| Update workspace | PUT | `public/workspaces/{id}` | `Partial<IWorkspace>` | `IWorkspace` |
| Delete workspace | DELETE | `public/workspaces/{id}` | - | `{ success }` |
| List members | GET | `public/workspaces/{workspaceId}/users` | - | `IWorkspaceUser[]` |
| Add an **existing** account as a member | POST | `public/workspaces/{workspaceId}/users/add` | `{ email, role }` | `{ userId, workspace, message }`. **404 when the address has no account**; to reach someone without one, use [invitations](#workspace-invitations) |
| Remove member, or leave (your own user id) | DELETE | `public/workspaces/{workspaceId}/users/{userId}` | - | `{ userId, workspace, message }` |
| Update member (role) | PATCH | `public/workspaces/{workspaceId}/users/{userId}` | `Partial<IWorkspaceUser>` | `{ userId, workspace, message }` |
| Update workspace settings (permissions) | PATCH | `public/workspaces/settings` | `{ permissions: Record<role, string[]> }` | - |
| Update workspace permission matrix | PATCH | `public/workspaces/{workspaceId}/permissions` | `{ permissions: Record<role, string[]> }` | - |
| What the signed-in member may do here (0.0.73) | GET | `public/workspaces/{workspaceId}/permissions/me` | - | `{ role, isOwner, permissions: string[] }`, resolved by the server (platform and org-defined permissions). See [Permissions](#permissions) |

---

## Workspace invitations

Since 0.0.71. An invitation reaches an email address that may have no account; the link lands on the app's auth redirect URL (or `landingUrl`, which must be one of the auth client's allowed redirect URLs). A pending invitation bills a seat until accepted, declined, revoked or expired.

| Purpose | Method | Path | Auth | Body | Response |
|---|---|---|---|---|---|
| List a workspace's invitations, pending first (`MEMBERS_VIEW`) | GET | `public/workspaces/{workspaceId}/invitations` | session | - | `IWorkspaceInvitation[]` |
| Invite an address (`MEMBERS_INVITE`) | POST | `public/workspaces/{workspaceId}/invitations` | session | `{ email, role, landingUrl? }` | `IWorkspaceInvitation & { message }` |
| Resend (five-minute cooldown; revives an expired one) | POST | `public/workspaces/{workspaceId}/invitations/{invitationId}/resend` | session | - | `IWorkspaceInvitation & { message }` |
| Revoke a pending invitation | DELETE | `public/workspaces/{workspaceId}/invitations/{invitationId}` | session | - | `{ success, message }` |
| The signed-in user's own pending invitations | GET | `public/invitations` | session | - | `IWorkspaceInvitation[]` |
| Accept | PATCH | `public/invitations/{invitationId}/accept` | session | `{ token? }` - pass the link's token so a just-registered account is let in without a separate email verification | `{ invitation, workspace, message }` (`workspace` null only in a race) |
| Decline | PATCH | `public/invitations/{invitationId}/reject` | session | - | `{ invitation, message }` |
| Preview what a link resolves to, before sign-in | GET | `public/{orgId}/invitations/preview/{token}` | none | - | `IWorkspaceInvitationPreview` (`joinable: false` when the org has invitations off); 404 for an unknown or revoked token |

Error `code` values the server returns: `INVITATION_NOT_FOUND`, `INVITATION_EXPIRED`, `INVITATION_ALREADY_HANDLED`, `INVITATION_EMAIL_MISMATCH` (with the scrambled `invitedEmail`), `EMAIL_NOT_VERIFIED`, `WORKSPACE_INVITES_DISABLED`, `INVITATION_RATE_LIMITED` (with `retryAfterSeconds`), `INVITATION_EMAIL_FAILED`, `SEAT_LIMIT_REACHED` (with `currentUserCount` and `limit`), `USER_BLOCKED`, and `NO_SENDER_CONFIGURED` (503, the org has no usable email sender).

---

## Features

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| List workspace feature definitions | GET | `public/workspaces/features` | - | `IWorkspaceFeature[]` |
| Toggle a workspace feature | PATCH | `public/workspaces/{workspaceId}/features` | `{ features: { [slug]: boolean } }` | `IWorkspace` |
| Get resolved user features | GET | `public/users/features` | - | `Record<string, boolean>` |

There is no feature "check" endpoint - fetch the map and look up the slug (a feature is on if present and `true`). For a plan's feature, limit or quota, the composed answer is the entitlement: see [Limits and entitlements](#limits-and-entitlements).

---

## Billing subjects: a workspace or `me`

Plans can belong to a workspace or to a person (account-level billing, since 1.0.0). Every route in [Subscription](#subscription), [Invoices](#invoices), the `quotas` / `limits` routes, [Credits](#credits) and [Add-ons](#add-ons) is written below with the prefix `{subject}`, which is either:

- `workspaces/{workspaceId}` - the workspace's plan, or
- `me` - the signed-in person's own plan. Same bodies, same answer fields.

The older usage routes (`subscription/usage/status`, `/all`, `/logs`) and the plan-group version routes exist only under `workspaces/{workspaceId}`.

---

## Subscription

Every write in this table sends an `Idempotency-Key` header (a new UUID per call unless you pass one); the platform keys each Stripe call on it, so a retry with the same key gets the first try's checkout or change.

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Get current subscription | GET | `public/{subject}/subscription` | - | `ISubscriptionResponse` (for `me`: with the person's standing and entitlement) |
| Create checkout session | POST | `public/{subject}/subscription/checkout` | `{ planVersionId, billingInterval?, currency?, successUrl?, cancelUrl?, stripeOptions? }` | `CheckoutResult` (checkout / trial_started / existing). The `checkout` shape also carries `amountTotal` (minor units, absent on older servers), `currency` and `trial` |
| Select a free plan | POST | `public/{subject}/subscription/select-free-plan` | `{ planVersionId }` | `{ success, message }` |
| Preview a change (or a trial's end) | POST | `public/{subject}/subscription/preview` | the change | the prorated amounts, without changing anything |
| Update (up/downgrade) | PATCH | `public/{subject}/subscription` | `{ planVersionId, billingInterval?, successUrl?, cancelUrl? }` | update result (with `prorated?` and `invoice?: { id, amount_due, status }` when the change was applied in place) **or** a checkout-session response (`amountTotal`, `currency`, `trial`) if payment is needed |
| Trial eligibility | GET | `public/{subject}/subscription/trial-eligibility` | - | whether a trial is still offered |
| Upcoming invoice | GET | `public/{subject}/subscription/upcoming-invoice` | - | the next invoice's amounts |
| Cancel at period end | POST | `public/{subject}/subscription/cancel-at-period-end` | optional feedback | `ISubscriptionResponse` |
| Cancel now | POST | `public/{subject}/subscription/cancel-now` | optional feedback | the ended subscription |
| Retention offer: read, accept | GET / POST | `public/{subject}/subscription/retention-offer`, `.../retention-offer/accept` | accept: `{ offerId, feedback?, comment? }` | the offer, then the changed subscription |
| Pause | POST | `public/{subject}/subscription/pause` | months, or a pause request | the paused subscription |
| Resume | POST | `public/{subject}/subscription/resume` | - | `ISubscriptionResponse` |
| End a trial and pay now | POST | `public/{subject}/subscription/convert-to-paid` | - | the paid subscription |
| Hand the workspace's bill to another payer | POST | `public/workspaces/{workspaceId}/subscription/transfer-payer` | the new payer | the subscription |
| Stripe billing-portal URL | POST | `public/{subject}/subscription/billing-portal` | `{ returnUrl?, flow? }` | `{ url }` |
| Start saving a card / make one the default | POST | `public/{subject}/billing/payment-method/setup`, `public/{subject}/billing/payment-method/default` | - / the card | a setup session; the default card |
| A payer's roll-up across the workspaces it pays for | GET | `public/billing/payers/{payerId}/rollup` | - | the payer's totals |
| Check a promotion code before checkout (no auth) | GET | `public/{orgId}/promotions/{code}?...` | the plan version, interval and currency, or the credit pack and currency, in the query | `valid` and the discount; an unknown code is `valid: false`, not an error |

---

## Plans

| Purpose | Method | Path | Auth | Response |
|---|---|---|---|---|
| Get plan group (current/latest) | GET | `public/{subject}/subscription/plan-group` (`me` adds `?ifNone=empty`) | session | `IPlanGroupResponse` |
| The person's plan group by slug | GET | `public/me/subscription/plan-group?slug={slug}` | session | `IPlanGroupResponse` |
| Plan group at a version | GET | `public/workspaces/{workspaceId}/subscription/plan-group?groupVersionId={id}` | session | `IPlanGroupResponse` |
| List group versions | GET | `public/workspaces/{workspaceId}/subscription/plan-group/versions` | session | `IPlanGroupVersionsResponse` |
| **Public** plans by slug | GET | `public/{orgId}/plans/{slug}` | none | `IPublicPlansResponse` (prices in minor units) |
| **Public** plan-group-version by id | GET | `public/{orgId}/plan-group-versions/{groupVersionId}` | none | `IPlanGroupVersion` |

---

## Invoices

| Purpose | Method | Path | Query | Response |
|---|---|---|---|---|
| List invoices | GET | `public/{subject}/subscription/invoices` | `limit` (default 10), `starting_after?` | `IInvoiceListResponse` `{ invoices[], has_more }` |
| Get invoice | GET | `public/{subject}/subscription/invoices/{invoiceId}` | - | `IInvoiceResponse` |
| Pay an open invoice with the saved card | POST | `public/{subject}/subscription/invoices/{invoiceId}/pay` | - | the invoice (sends an `Idempotency-Key`) |

`IInvoice`: `{ id, number, amount_due, amount_paid (minor units), currency, status, created, due_date, hosted_invoice_url, invoice_pdf, description, subscription }`.

---

## Usage / Quota

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Record usage | POST | `public/{subject}/subscription/usage` | `{ quotaSlug, quantity, metadata?, source?, idempotencyKey? }` | `{ used, consumed, included, available, overage, billedAsync }` - note: **no `hasOverage`**, that is on the status shape below |
| Record usage batch (≤100) | POST | `public/{subject}/subscription/usage/batch` | `{ items: [{ quotaSlug, quantity, metadata?, source?, idempotencyKey? }] }` | `{ success, total, succeeded, failed, results[] }` |
| One quota as the subject stands this period | GET | `public/{subject}/quotas/{quotaSlug}` | `member=1` (a per-member quota's own standing), `partitionKey?` | the standing (`usage`, which the SDK calls `consumed`) |
| One quota status (older route) | GET | `public/workspaces/{workspaceId}/subscription/usage/status?quotaSlug={slug}` | - | `{ quotaSlug, consumed, included, available, overage, hasOverage, allowOverage? }` |
| All quota status | GET | `public/workspaces/{workspaceId}/subscription/usage/all` | - | `{ quotas: Record<slug, status> }` |
| Usage logs | GET | `public/workspaces/{workspaceId}/subscription/usage/logs` | `quotaSlug?, from?, to?, source?, page?, limit?` | paginated `{ docs[], totalDocs, page, totalPages, … }` |

---

## Limits and entitlements

Since 1.0.0. A limit is a ceiling on things held (seats, projects, devices); a claim holds one unit against it.

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| One limit and what the subject holds | GET | `public/{subject}/limits/{slug}` | `partitionKey?` | the standing |
| Claim a unit | POST | `public/{subject}/limits/{slug}/claim` | `{ resourceId, partitionKey?, metadata? }` | 201 with the claim, 200 when already held; **402 `PLAN_LIMIT_REACHED`** at the ceiling; 409 `CLAIM_LINKED` for a limit another module claims |
| Release a claim | POST | `public/{subject}/limits/{slug}/release` | `{ resourceId, partitionKey? }` | the release |
| List claims | GET | `public/{subject}/limits/{slug}/claims` | paging | the claims |
| The person's own composed entitlement | GET | `public/me/subscription/entitlement` | - | `{ entitlement }` (features, limits, quotas as the server composed them); 404 on an older server |

The workspace's entitlement comes with its subscription read; `entitlements.get` / `check` in the server factory and `useEntitlement` in React read these. A named person's entitlement from your backend is an [org-token route](#org-token-routes-the-sdk-calls).

---

## Credits

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Get balance | GET | `public/{subject}/credits` | - | `{ available, held?, totalGranted, totalConsumed, totalExpired, totalRefunded, autoTopUp? }` |
| Consume credits | POST | `public/{subject}/credits/consume` | `{ amount, description?, idempotencyKey?, metadata? }` | `{ success, consumed, balanceAfter }` - **402** → insufficient (`{ available, requested }`) |
| Reserve (hold) credits | POST | `public/{subject}/credits/reserve` | `{ amount, ttlSeconds?, description?, idempotencyKey?, metadata? }` | `{ holdId, amount, status, expiresAt, available, held, replayed? }` |
| Settle a hold (charge what was used) | POST | `public/{subject}/credits/holds/{holdId}/settle` | `{ amount, description?, metadata? }` | the settled hold |
| Release a hold | POST | `public/{subject}/credits/holds/{holdId}/release` | - | the released hold |
| List holds | GET | `public/{subject}/credits/holds` | status, paging | the holds |
| Auto top-up: read, change (or accept a new package version) | GET / PATCH | `public/{subject}/credits/auto-top-up` | the setting, or `{ acceptVersion }` | the setting |
| Purchase package | POST | `public/{subject}/credits/purchase` | `{ creditPackageId, successUrl, cancelUrl, currency?, metadata? }` (`metadata` is written onto the Stripe session) | `{ sessionId, url, amountTotal?, currency? }` (sends an `Idempotency-Key`) |
| Save a card for top-ups | POST | `public/{subject}/credits/payment-method-setup` | success and cancel URLs | a setup session (sends an `Idempotency-Key`) |
| List packages | GET | `public/{subject}/credits/packages` | - | `ICreditPackage[]` - raw wire response may be paginated `{ docs: ICreditPackage[] }` (the SDK flattens `docs ?? data`) |
| Transactions | GET | `public/{subject}/credits/transactions` | `type?, page?, limit?` | paginated |
| Buckets | GET | `public/{subject}/credits/buckets` | `status?, source?, page?, limit?` | paginated |
| Expiring credits | GET | `public/{subject}/credits/expiring?days={n}` | `days?` (1 to 90, default 7) | `{ days, expiringCredits, buckets[] }` |
| **Public** packages by org | GET | `public/{orgId}/credit-packages` | none | `IPublicCreditPackagesResponse` |

---

## Add-ons

Since 1.0.0. What a subject holds beyond its plan. Writes send an `Idempotency-Key`.

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Add-ons on sale to the subject, with what it holds | GET | `public/{subject}/billing/offers` | `currency?` | `IAddOnOffers` |
| Preview, then buy | POST | `public/{subject}/billing/checkout/preview`, `public/{subject}/billing/checkout` | the add-on, quantity, currency | the amounts; then a checkout or the grant |
| Lower the units (preview, apply) | POST | `public/{subject}/billing/add-ons/{grantId}/decrease/preview`, `.../decrease` | `{ quantity, expectedQuantity? }` | 409 `QUANTITY_CHANGED` when another change moved the units first |
| Cancel (preview, apply) | POST | `public/{subject}/billing/add-ons/{grantId}/cancel/preview`, `.../cancel` | `{ expectedQuantity? }` | the cancelled grant |
| Upgrade to the version on sale (quote, apply) | GET / POST | `public/{subject}/billing/add-ons/{grantId}/upgrade` | - | the quote; the upgraded grant |
| Future versions of a lifetime add-on | POST | `public/{subject}/billing/add-ons/{grantId}/future-versions` | - | the grant |
| What the subject holds (grants) | GET | `public/{subject}/grants` | - | `IEntitlementGrant[]` |
| **Public** add-ons by org | GET | `public/{orgId}/add-ons` | `currency?` | the catalog |

---

## Notifications

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Send/trigger an event | POST | `public/workspaces/{workspaceId}/notifications/send` | `{ event, userId?, data? }` (omit `userId` → notify all members) | `{ sent, channels: { email, push }, notifiedCount?, reason? }`; with a future `data.scheduledAt` (at most 365 days ahead), `scheduled: true`, `scheduledAt` and `scheduledId` |
| Cancel a scheduled send (1.6.0) | DELETE | `public/workspaces/{workspaceId}/notifications/scheduled/{scheduledId}` | - | 404 for an unknown id, 409 `SCHEDULED_SEND_NOT_PENDING` once it has gone |
| List manageable events | GET | `public/workspaces/{workspaceId}/notification-events` | - | `NotificationEvent[]` |
| Workspace **defaults** for every member (`SETTINGS_VIEW`) | GET | `public/workspaces/{workspaceId}/notification-preferences` | - | wrapped: `{ notificationPreferences: Record<slug, { email?, push?, required? }> }` (the SDK unwraps it). Since 0.0.71 these are the defaults, not any one member's choices |
| Update the defaults (`SETTINGS_EDIT`; merged per event) | PATCH | `public/workspaces/{workspaceId}/notification-preferences` | `{ notificationPreferences: Record<slug, { email?, push?, required? }> }` | same wrapped shape as GET |
| The signed-in member's **own** preferences (0.0.71) | GET | `public/workspaces/{workspaceId}/notification-preferences/me` | - | `{ defaults: Record<slug, { email?, push?, required? }>, mine: Record<slug, { email?, push? }> }` |
| Update the member's own preferences | PATCH | `public/workspaces/{workspaceId}/notification-preferences/me` | `{ notificationPreferences: Record<slug, { email?: boolean \| null, push?: boolean \| null }> }` (`null` goes back to the default) | same shape as GET; a `required` event answers 409 `NOTIFICATION_PREFERENCE_REQUIRED` |

`data` (NotificationData) supports: `title, message, icon, image, badge, url, tag, actions[≤2], silent, requireInteraction, renotify, timestamp, dir, ttl, urgency, scheduledAt, channels`, plus arbitrary merge-tag keys.

A slug the console has never seen **registers itself on first send** (server release 22) and counts toward the plan's custom-event limit; at that limit a new slug answers 403 `NOTIFICATION_EVENT_NOT_SET_UP`.

### Delivered items (0.0.71)

Every notification sent to the signed-in user, by email, push or both, is also kept as a record the user can read back. These routes are user-scoped (`x-session-id`, no workspace in the path); `workspaceId` in the query or body narrows the scope, and `'none'` selects account-level notices.

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| A page of items, newest first | GET | `public/notifications?workspaceId&unread&archived&page&limit` | query, all optional | `{ notifications, page, limit, total, hasNextPage }` |
| Unread and unseen counts | GET | `public/notifications/unread-count?workspaceId` | - | `{ unread, unseen }` |
| Mark one read / unread | POST | `public/notifications/{id}/read`, `public/notifications/{id}/unread` | - | the item |
| Archive / unarchive one | POST / DELETE | `public/notifications/{id}/archive` | - | the item |
| Mark everything in scope read | POST | `public/notifications/read-all` | `{ workspaceId? }` | empty |
| Mark the list seen (clears "new" without reading) | POST | `public/notifications/seen` | `{ workspaceId? }` | empty |

Live updates ride a socket.io channel (`sdk/src/lib/inbox-socket.ts`, WebSocket transport, the session in the handshake's `auth`) that carries only "your list changed"; reads still go through these routes.

---

## Push

`PushApi` requires `orgId` to be configured.

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Get VAPID public key | GET | `public/push/vapid-public-key` | - | `{ publicKey }` |
| Subscribe a device | POST | `public/push/subscribe` | `{ endpoint, keys: { p256dh, auth }, userAgent }` | empty (server may send a welcome push) |
| Unsubscribe a device | DELETE | `public/push/unsubscribe` | `{ endpoint }` | empty |

---

## Permissions

**Since 0.0.73 there is a permission endpoint:** `GET public/workspaces/{workspaceId}/permissions/me` answers `{ role, isOwner, permissions }` for the signed-in member, resolved by the server from the platform's permissions and the organization's own (defined in the console under workspace settings as `customPermissions`). The server factory exposes it as `workspace.permissions(id)` and `workspace.can(id, permission)`. A backend should ask this rather than trust a flag the browser sent, and from another language it is one GET.

The older **local computation** is still what the React hooks and `permissions.check` / `permissions.resolve` do, and it is the fallback against a server older than the endpoint. It uses three GETs:

1. `GET public/workspaces/{workspaceId}` - the workspace (has `permissions: Record<role, string[]>`)
2. `GET public/{orgId}/settings` - org settings (the `settings.workspace.permissions` template and the `settings.workspace.customPermissions` catalog)
3. `GET public/workspaces/{workspaceId}/users` - to find the caller's role

Resolution is three-tier, the same as the server: a workspace override, then the organization's matrix from the console, then the SDK defaults (and for app permissions, the `defaultPermissions` the app passed to the provider, but only for keys the org has not catalogued). Platform permissions look like `workspace:*`; app permissions are your own strings (e.g. `reports:export`). The write side is `PATCH public/workspaces/{workspaceId}/permissions`.

---

## Enterprise

A workspace's company: Enterprise SSO and Directory Sync through the app owner's own WorkOS account, company roles and groups, audit. Session-authenticated; a member needs the workspace settings permission and company roles for most reads. All under `public/workspaces/{workspaceId}/enterprise`:

| Area | Paths after the prefix |
|---|---|
| Status and setup | `GET ''` (`?refresh=1`; 404 means no company, read as `{ available: false }`), `POST /setup-link`, `POST /claim`, `GET /unclaimed`, `POST /domains/sync` |
| Sign-in routing and policy | `PUT /sso/routing`, `GET` / `PUT /policy`, `GET /policy/workspaces`, `GET` / `PUT` / `DELETE /policy/workspaces/{id}` |
| People | `GET /people`, `GET /people/{id}/sessions`, `DELETE /people/{id}/sessions/{sessionId}`, `POST /people/{id}/passkeys/reset`, `POST /sign-out`, `GET /outsiders`, `GET /join-requests`, `POST /join-requests/{id}/approve` / `decline` |
| Admins, roles, groups | `/admins` (`GET`, `POST`, `PATCH` / `DELETE /{id}`), `/roles` (same), `GET /workos-roles`, `POST /workos-roles/refresh`, `/groups` (`GET`, `POST`, `GET` / `PATCH` / `DELETE /{id}`, `GET /{id}/people`, `GET /{id}/candidates`, `POST /{id}/members`, `POST /{id}/managers`, `DELETE /{id}/managers/{userId}`) |
| Audit and log streams | `GET /audit`, `GET /audit/export`, `POST /audit/exports`, `GET /audit/exports/{id}`, `GET /log-stream`, `/log-streams` (`GET`, `POST`, `PATCH` / `DELETE /{id}`, `POST /{id}/rotate-secret`, `POST /{id}/test`), `GET /insights?days=` |
| Apps, keys, machines, agents | `GET /connected-apps`, `GET /connected-apps/{id}`, `POST /connected-apps/revoke`, `/keys` (`GET`, `POST`, `DELETE /{id}`), `/service-accounts` (`GET`, `POST`, `PATCH` / `DELETE /{id}`), `GET /workload-identity`, `POST /workload-identity/check`, `POST /workload-identity/credentials`, `PATCH` / `DELETE /workload-identity/credentials/{id}`, `GET` / `PATCH /agent-access`, `PUT` / `DELETE /agent-access/issuer`, `POST /agent-access/check` |

Refusals carry codes from the `ENTERPRISE_*` constants (`docs/ERROR_CODES.md` in the package). Never quote a WorkOS price.

---

## Commerce

Selling through Stripe Connect (since 1.2.0, grown through 1.8.0). Session routes; the buyer side is the signed-in person (`me`), the seller side is a workspace or the person selling, written `{seller}` = `workspaces/{workspaceId}` or `me`.

| Area | Routes (all under `public/`) |
|---|---|
| Published catalog | `GET items?...`, `GET items/{itemId}`, `GET item-types`, `GET items/{itemId}/slots?from&to` (bookable times), `GET items/{itemId}/reviews?...`, `POST items/{itemId}/reviews/{reviewId}/report` |
| Buying | `POST items/{itemId}/checkout`, `POST cart/checkout`, `POST cart/coupon`, `POST items/{itemId}/shipping-quote`, `POST cart/shipping-quote`, `GET me/carts/{cartId}`, `POST me/carts/{cartId}/next` |
| The buyer's orders and holdings | `GET me/orders`, `GET me/orders/{id}`, `POST me/orders/{id}/parts/{index}/pay`, `GET` / `POST me/orders/{id}/returns`, `GET me/orders/{id}/reviews`, `POST` / `PATCH me/orders/{id}/lines/{lineKey}/review`, `GET me/holdings`, `POST me/holdings/{grantId}/downloads`, `POST me/holdings/{grantId}/deactivate`, `POST me/holdings/{grantId}/seats/assign` / `free`, `GET me/access`, `POST me/gifts/{giftId}/claim` |
| Item subscriptions | `GET me/item-subscriptions`, `GET me/item-subscriptions/{id}`, `POST .../{id}/cancel`, `POST .../{id}/resume`, `GET .../{id}/change-preview`, `POST .../{id}/change` |
| The buyer's bookings | `GET me/bookings`, `GET me/bookings/{id}`, `POST me/bookings/{id}/cancel`, `POST me/bookings/{id}/reschedule` |
| Affiliates (the affiliate's side) | `GET` / `POST me/affiliates`, `GET me/affiliates/{id}`, `PUT me/affiliates/{id}/code` / `contact-consent` / `payout-method`, `GET me/affiliates/commissions`, `GET me/affiliates/payouts`, `POST me/affiliates/payout-account`, `POST me/affiliates/payout-account/sync`, `GET me/affiliate-invitations`, `POST me/affiliate-invitations/{id}/accept` / `decline` |
| Seller: items and calendars | `{seller}/items` (list, `POST`, `GET` / `PUT` / `DELETE /{id}`, `POST /{id}/{action}` such as publish or archive, `POST /{id}/booking/calendar-move` and `/preview`), `{seller}/calendars` (list, `POST`, `GET` / `PUT` / `DELETE /{id}`) |
| Seller: sales | `{seller}/sales` (list, `GET /{id}`, `POST /{id}/refund`, `POST /{id}/lines/{lineKey}/fulfil`, `POST /{id}/parts/{index}/charge`, `GET /export`, `GET /stats`, `GET /subscriptions`, `GET /subscriptions/{id}`, `POST /subscriptions/{id}/cancel`, `GET /{id}/reviews`, `POST` / `PATCH /{id}/lines/{lineKey}/review`, `POST /{id}/reviews/{reviewId}/reply`), shipments and returns under `/{id}`, `{seller}/sales/bookings` (list, `GET /{id}`, `POST /{id}/cancel` / `reschedule` / `accept` / `decline`, `PUT /{id}/attendance`) |
| Seller: setup | `{seller}/selling` (`POST /session`, `POST /sync`, `GET` / `PUT /tax`, `POST /debit-terms/accept`, co-sellers: `GET /co-sellers?direction=`, `POST /co-sellers`, `POST /co-sellers/{id}/accept` / `decline` / `withdraw`), `{seller}/selling/shipping`, `{seller}/shipping-rates`, `{seller}/coupons`, `{seller}/files` and `{seller}/releases` (with `/uploads` and `/uploads/{id}/complete`), `{seller}/affiliate-programs` (programs, their affiliates, invitations, commissions, payouts, `POST /payouts/{id}/mark-paid`) |

Writes that refund, charge, ship, return, cancel or mark a payout paid take an `Idempotency-Key` and replay the first answer for 24 hours (409 `IDEMPOTENCY_IN_PROGRESS`, 422 `IDEMPOTENCY_KEY_REUSED`). The app's own back office (every seller, an API key, no session) is `/api/v1/server/commerce` in [Org-token routes](#org-token-routes-the-sdk-calls).

---

## Guests and licence checks

Two more basePaths, both with **no session and no secret**, both requiring `orgId`:

- **`guest`** (`/api/v1/guest/{orgId}/...`, `GuestApi`): buying without signing in, once the app owner lets guests buy (`GUESTS_NOT_ALLOWED` otherwise). `GET items`, `GET items/{id}`, `POST items/{id}/checkout`, `POST cart/checkout`, `POST cart/coupon`, `GET carts/{cartId}`, `POST carts/{cartId}/next`, `GET orders/{id}`, `POST orders/{id}/downloads`, `POST orders/{id}/subscription/cancel`, `POST orders/{id}/parts/{index}/pay`, `GET items/{id}/slots`, `GET orders/{id}/booking` with `/cancel` and `/reschedule`, `GET affiliate-programs/{id}`, `POST referrals/click` (`{ code }`, also sent by the tracking referral capture), `POST items/{id}/shipping-quote`, `POST cart/shipping-quote`, `GET` / `POST orders/{id}/returns`, `GET gifts/{giftId}`, `POST gifts/{giftId}/claim`, `POST gifts/{giftId}/downloads`. An order or cart is opened with its token in `x-order-token`.
- **`licenses`** (`/api/v1/licenses/{orgId}/{action}`, `LicensesApi`): a seller's software checking a licence key from a customer's machine. `POST validate`, `activate`, `deactivate` with `{ key, instance? }` in the body (never the URL). Every answer is `{ valid, reason }`; too many checks from one place is 429 `LICENSE_CHECKS_LIMITED`.

---

## Unauthenticated org-scoped routes

No `x-session-id`. `orgId` is a path segment (`<orgId>-<key>` in an environment). All under `public/` unless noted.

| Purpose | Method | Path | Body / Query | Response | Since |
|---|---|---|---|---|---|
| Public tracking config for the `tracking` prop | GET | `public/{orgId}/tracking?clientId=` | - | tracking config (enveloped or bare) | 0.0.62 |
| Record a consent decision | POST | `public/{orgId}/consent` | consent record | empty | 0.0.73 |
| First-party web analytics events (the analytics script) | POST | `public/{orgId}/e` | one event, sent by keepalive `fetch` (or `sendBeacon`) | empty | 1.0.0 |
| Read a checkout session's result after the Stripe return | GET | `public/{orgId}/checkout/{sessionId}` | - | the session's conversion data | 0.0.62 |
| Mark that conversion as reported to the vendors | POST | `public/{orgId}/checkout/{sessionId}/reported` | - | empty | 0.0.62 |
| Whether that checkout is complete (polled after the return) | GET | `public/{orgId}/checkout/{sessionId}/status` | `nudge=1` asks the server to check Stripe again | the checkout's state; the server factory's `checkout.status` adds the org API token when it has one | 1.2.0 |
| The org's agent-readiness bundle (fail-soft, cached by the SDK) | GET | `public/{orgId}/agent-readiness` | - | `{ enabled, authorizationServer }` for `llms.txt` and `.well-known` | 0.0.49 |
| Invitation preview | GET | `public/{orgId}/invitations/preview/{token}` | - | see [invitations](#workspace-invitations) | 0.0.71 |
| Public plans, credit packages, add-ons, promotion codes | GET | `public/{orgId}/plans/{slug}`, `/credit-packages`, `/add-ons`, `/promotions/{code}` | - | see the billing sections | |

---

## Beta

basePath `beta` instead of `public`, no auth headers: `GET /api/v1/beta/config?orgId=` returns the beta form configuration; `POST /api/v1/beta/submit` with `{ orgId, formData: { name, email, country?, language?, timezone?, currency?, context? } }` submits a beta request.

---

## Org-token routes the SDK calls

These authenticate with an org API token (`Authorization: Bearer <orgId>:<secret>`), not a session, and sit outside `/v1/public`. Never from a browser. The rest of the org-token surface is in [org-api.md](./org-api.md).

**A named person's billing** (`BuildBase({ apiToken })`, `users.subscription` / `users.usage` / `users.limits` / `users.credits`, `entitlements` with `user: '<userId>'`, since 1.0.0). Base `{serverUrl}/api/subscriptions/users`: `GET /{userId}/subscription`, `GET /{userId}/entitlement`, `GET /{userId}/limits/{slug}`, `POST .../claim`, `POST .../release`, `GET .../claims`, `POST /{userId}/usage`, `GET /{userId}/credits`, `GET /{userId}/credits/holds`, `POST /{userId}/credits/holds/{holdId}/release`, and `GET /entitlements/check?slug=&subjects=user:<id>,workspace:<id>` (up to five subjects). A person from another org is 404.

**`@buildbase/sdk/server`** (`createServerClient({ serverUrl, apiToken })`):

| Resource | Paths |
|---|---|
| Blog posts, docs pages (0.0.73) | `GET /api/blogs`, `GET /api/docs`; each with `/{id}`, `/path?path=`, `/folders/tree`, `/tags`, `/authors` |
| FAQ collections | `GET /api/faqs/collections`, `/api/faqs/collections/{id}`, `/api/faqs/collections/slug/{slug}`, and `.../faqs` under either (every page, 500 a request) |
| Testimonials | `GET /api/testimonials`, `/api/testimonials/{id}` |
| Rich content | `GET /api/rich-content`, `/api/rich-content/slug/{slug}` |
| Collections | `GET /api/collections`, `/api/collections/data/{slug}?latest=true` or `?version=N`, paged with `$page` / `$limit` |
| Transactional email (1.0.0) | `POST /api/v1/server/emails/send` (`{ to: { email, name? }, templateId? \| subject + html/text, data?, senderId? }`, optional `Idempotency-Key`) → `{ id, status: 'queued', replayed }`; `GET /api/v1/server/emails/{id}` |
| Subscribers (1.0.0) | `PUT /api/v1/server/subscribers` (upsert by email: `{ email, name?, tags?, removeTags?, attributes?, lists?, timezone?, language?, country?, currency? }`), `GET` / `DELETE /api/v1/server/subscribers/{email}`, `POST .../{email}/unsubscribe`, `POST .../{email}/resubscribe` |
| Commerce back office (1.2.0) | `/api/v1/server/commerce/` + `items` (with `/bulk`, `/{id}/publish` / `unlist` / `archive` / `approve` / `reject`, calendar-move), `orders` (with `/export`, `/stats`, `/{id}/refund`, lines fulfil, parts charge and stop), `subscriptions` (cancel, resume, change-preview, change), `bookings` (cancel, reschedule, accept, decline, attendance), `calendars`, `affiliates` (approve, pause, resume, ban), `commissions`, `shipments` (status, label), `shipping-rates`, `shipping-settings/{sellerId}`, `returns` (approve, reject, refund), `grants` (access, revoke, deactivate, keys rotate / disable / enable, seats assign / free), `licenses/validate` / `activate` / `deactivate`, `files` (uploads), `releases` (publish), `buyers/state` |

Content list responses follow the shared `{ docs, ... }` contract; `pagination=false` still returns that object, never a bare array. Content reads answer with `ETag`; send `If-None-Match` and a `304` means your copy is current. Every request from this client carries `X-BuildBase-Client: sdk/<version>; runtime=<...>`.

**Central** (`https://central.console.buildbase.app` when hosted), called by server-side helpers and the CLI:

- `GET /api/organizations/orgs/{orgId}/region` (`resolveServerUrl`, with the org API key) answers `{ orgId, region, cellId, serverUrl }`. Without the key it answers the default cell for every id, on purpose.
- `POST /api/organizations/agent/identity` (`npx @buildbase/sdk init --claim`, `@buildbase/sdk/keyless`) creates a claimable organization with no account: `{ name, email? }` in, an API key, a claim URL and a claim code out, once. Deleted after 72 hours unless a person claims it. `POST /api/organizations/agent/identity/claim-code` (with that key) issues a fresh code.

---

## Called by your app, not by the SDK

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Org API token to user session (backends and jobs) | POST | `public/token/exchange` | `{ token: "<orgId>:<secret>", expiresIn?, userId?, workspaceId? }` | `{ sessionId, expiresIn, userId, orgId }`. See [using-from-any-language.md](./using-from-any-language.md#acting-for-one-of-your-app-users) |

`withSession(sessionId)` only binds an existing session id; the SDK never calls the token exchange. The code to session exchange (`POST /api/v1/auth/token`) used to sit here too: since 1.6.0 the SDK does it for you ([Auth](#auth)).
