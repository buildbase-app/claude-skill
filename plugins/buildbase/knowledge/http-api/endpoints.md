# HTTP API - Endpoint Catalog

Every endpoint the `@buildbase/sdk` calls, extracted from source at **0.0.78** (`sdk/src/api/services/*.ts`, `sdk/src/lib/server-client.ts`, `sdk/src/tracking/*`, `sdk/src/lib/agent-discovery.ts`, `sdk/src/lib/server-content/client.ts`). Paths below are the part after the base. Unless noted, the full URL is:

```
{serverUrl}/api/{version}/public/{path}      e.g. https://api.console.buildbase.app/api/v1/public/workspaces
```

All session-authenticated calls send `x-session-id: <sessionId>` (the browser SDK also sends a best-effort `x-device-id`). Every interpolated path segment is URL-encoded. Bodies are JSON (`Content-Type: application/json`). See [overview.md](./overview.md) for envelope/error rules. Webhook event names are a separate catalog: [webhooks.md](./webhooks.md#event-catalog).

## Contents

- [Auth](#auth) - login request, code to session exchange, sign-out, device token
- [Profile & Users](#profile--users) - profile, attributes, user features
- [Passkeys, devices, sessions, connected agents](#passkeys-devices-sessions-connected-agents) - the signed-in user's own security surface
- [Settings (org-scoped, public path)](#settings-org-scoped-public-path) - org/OS settings
- [Workspaces & Members](#workspaces--members) - CRUD and membership
- [Workspace invitations](#workspace-invitations) - inviting an address that has no account yet (0.0.71)
- [Features](#features) - workspace feature definitions and toggles
- [Subscription](#subscription) - checkout, upgrade, cancel, billing portal
- [Plans](#plans) - plan groups and public plan lookups
- [Invoices](#invoices) - list and fetch invoices
- [Usage / Quota](#usage--quota) - record usage and quota status
- [Credits](#credits) - balance, consume, purchase, transactions
- [Notifications](#notifications) - send events, events, workspace defaults, the member's own preferences, delivered items
- [Push](#push) - VAPID key, subscribe, unsubscribe
- [Permissions](#permissions) - the server's answer, and the local fallback
- [Unauthenticated org-scoped routes](#unauthenticated-org-scoped-routes) - tracking, consent, checkout return, agent readiness, invitation preview
- [Beta](#beta) - the `beta` basePath
- [Org-token content client](#org-token-content-client-buildbasesdkserver) - `@buildbase/sdk/server`, a different base and header
- [Called by your app, not by the SDK](#called-by-your-app-not-by-the-sdk) - the two exchanges

---

## Auth

`/auth/request` is the one endpoint that sits **outside** `/public`.

| Purpose | Method | Path | Auth | Body / Query | Response |
|---|---|---|---|---|---|
| Start login - get the provider redirect URL | POST | `/api/{version}/auth/request` | none | `{ orgId, clientId, redirect: { success, error }, state?, trackingConsent?, trackingIdentity?, trackingAttribution?, invitationToken? }` (the tracking fields since 0.0.73, `invitationToken` since 0.0.75; all optional) | `{ success, data: { redirectUrl }, message }` |
| Get current user's profile (also validates the session) | GET | `public/profile` | `x-session-id` | - | `IUser` |
| Sign out: revoke the session server-side (0.0.70) | POST | `public/logout` | `x-session-id` | `{ all: true }` to revoke every session of the user; otherwise no body | empty. Idempotent; answers for an already-expired id too |
| Device token, echoed back as `x-device-id` (0.0.57) | GET | `public/device-token` | `x-session-id` | - | `{ deviceToken }`; `''` for agent/machine sessions. Best-effort: the SDK swallows failures |

> The secure **code to session exchange** (`POST /api/v1/auth/token` with `clientId`+`clientSecret`+`orgId`+`code`, answering `{ data: { sessionId, user } }`) is performed **server-side** and is how the official Next.js starter obtains the `sessionId`. Your app calls it; the SDK client package does not. It is the correct server flow for any backend - see [using-from-any-language.md](./using-from-any-language.md).

---

## Profile & Users

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Get profile | GET | `public/profile` | - | `IUser` |
| Update profile | PATCH | `public/profile` | `Partial<IUser>` | `IUser` |
| Get user attributes | GET | `public/users/attributes` | - | `Record<string, string\|number\|boolean>` |
| Bulk-update attributes | PATCH | `public/users/attributes` | `{ attributes: Record<string, …> }` | `IUser` |
| Update one attribute | PATCH | `public/users/attributes/{attributeKey}` | `{ value }` | `IUser` |
| Get resolved user feature flags | GET | `public/users/features` | - | `Record<string, boolean>` |

`IUser`: `{ _id, name, email, image?, role, country?, timezone?, language?, currency?, attributes?, createdAt, updatedAt }`.

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
| Remove member | DELETE | `public/workspaces/{workspaceId}/users/{userId}` | - | `{ userId, workspace, message }` |
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

There is **no "check" endpoint** - fetch the map and look up the slug. A feature is on if present and `true`.

---

## Subscription

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Get current subscription | GET | `public/workspaces/{workspaceId}/subscription` | - | `ISubscriptionResponse` |
| Create checkout session | POST | `public/workspaces/{workspaceId}/subscription/checkout` | `{ planVersionId, billingInterval?, currency?, successUrl?, cancelUrl?, stripeOptions? }` | `CheckoutResult` (checkout / trial_started / existing). The `checkout` shape also carries `amountTotal` (minor units, absent on older servers), `currency` and `trial` |
| Select a free plan | POST | `public/workspaces/{workspaceId}/subscription/select-free-plan` | `{ planVersionId }` | `{ success, message }` |
| Update (up/downgrade) | PATCH | `public/workspaces/{workspaceId}/subscription` | `{ planVersionId, billingInterval?, successUrl?, cancelUrl? }` | update result (with `prorated?` and `invoice?: { id, amount_due, status }` when the change was applied in place) **or** a checkout-session response (`amountTotal`, `currency`, `trial`) if payment is needed |
| Cancel at period end | POST | `public/workspaces/{workspaceId}/subscription/cancel-at-period-end` | - | `ISubscriptionResponse` |
| Resume | POST | `public/workspaces/{workspaceId}/subscription/resume` | - | `ISubscriptionResponse` |
| Stripe billing-portal URL | POST | `public/workspaces/{workspaceId}/subscription/billing-portal` | `{ returnUrl? }` | `{ url }` |

---

## Plans

| Purpose | Method | Path | Auth | Response |
|---|---|---|---|---|
| Get plan group (current/latest) | GET | `public/workspaces/{workspaceId}/subscription/plan-group` | session | `IPlanGroupResponse` |
| Plan group at a version | GET | `public/workspaces/{workspaceId}/subscription/plan-group?groupVersionId={id}` | session | `IPlanGroupResponse` |
| List group versions | GET | `public/workspaces/{workspaceId}/subscription/plan-group/versions` | session | `IPlanGroupVersionsResponse` |
| **Public** plans by slug | GET | `public/{orgId}/plans/{slug}` | none | `IPublicPlansResponse` (prices in cents) |
| **Public** plan-group-version by id | GET | `public/plan-group-versions/{groupVersionId}` | none | `IPlanGroupVersion` |

---

## Invoices

| Purpose | Method | Path | Query | Response |
|---|---|---|---|---|
| List invoices | GET | `public/workspaces/{workspaceId}/subscription/invoices` | `limit` (default 10), `starting_after?` | `IInvoiceListResponse` `{ invoices[], has_more }` |
| Get invoice | GET | `public/workspaces/{workspaceId}/subscription/invoices/{invoiceId}` | - | `IInvoiceResponse` |

`IInvoice`: `{ id, number, amount_due, amount_paid (cents), currency, status, created, due_date, hosted_invoice_url, invoice_pdf, description, subscription }`.

---

## Usage / Quota

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Record usage | POST | `public/workspaces/{workspaceId}/subscription/usage` | `{ quotaSlug, quantity, metadata?, source?, idempotencyKey? }` | `{ used, consumed, included, available, overage, billedAsync }` - note: **no `hasOverage`**, that is on the status shape below |
| Record usage batch (≤100) | POST | `public/workspaces/{workspaceId}/subscription/usage/batch` | `{ items: [{ quotaSlug, quantity, metadata?, source?, idempotencyKey? }] }` | `{ success, total, succeeded, failed, results[] }` |
| One quota status | GET | `public/workspaces/{workspaceId}/subscription/usage/status?quotaSlug={slug}` | - | `{ quotaSlug, consumed, included, available, overage, hasOverage, allowOverage? }` |
| All quota status | GET | `public/workspaces/{workspaceId}/subscription/usage/all` | - | `{ quotas: Record<slug, status> }` |
| Usage logs | GET | `public/workspaces/{workspaceId}/subscription/usage/logs` | `quotaSlug?, from?, to?, source?, page?, limit?` | paginated `{ docs[], totalDocs, page, totalPages, … }` |

---

## Credits

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Get balance | GET | `public/workspaces/{workspaceId}/credits` | - | `{ available, totalGranted, totalConsumed, totalExpired, totalRefunded }` |
| Consume credits | POST | `public/workspaces/{workspaceId}/credits/consume` | `{ amount, description?, idempotencyKey?, metadata? }` | `{ success, consumed, balanceAfter }` - **402** → insufficient (`{ available, requested }`) |
| Purchase package | POST | `public/workspaces/{workspaceId}/credits/purchase` | `{ creditPackageId, successUrl, cancelUrl, currency?, metadata? }` (`metadata` is written onto the Stripe session) | `{ sessionId, url, amountTotal?, currency? }` |
| List packages | GET | `public/workspaces/{workspaceId}/credits/packages` | - | `ICreditPackage[]` - raw wire response may be paginated `{ docs: ICreditPackage[] }` (the SDK flattens `docs ?? data`) |
| Transactions | GET | `public/workspaces/{workspaceId}/credits/transactions` | `type?, page?, limit?` | paginated |
| Buckets | GET | `public/workspaces/{workspaceId}/credits/buckets` | `status?, source?, page?, limit?` | paginated |
| Expiring credits | GET | `public/workspaces/{workspaceId}/credits/expiring?days={n}` | `days?` (1–90, default 7) | `{ days, expiringCredits, buckets[] }` |
| **Public** packages by org | GET | `public/{orgId}/credit-packages` | none | `IPublicCreditPackagesResponse` |

---

## Notifications

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Send/trigger an event | POST | `public/workspaces/{workspaceId}/notifications/send` | `{ event, userId?, data? }` (omit `userId` → notify all members) | `{ sent, channels: { email, push }, notifiedCount?, reason? }` |
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

Live updates ride a socket.io channel (`sdk/src/lib/inbox-socket.ts`) that carries only "your list changed"; reads still go through these routes.

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

## Unauthenticated org-scoped routes

No `x-session-id`. `orgId` is a path segment. All under `public/` unless noted.

| Purpose | Method | Path | Body / Query | Response | Since |
|---|---|---|---|---|---|
| Public tracking config for the `tracking` prop | GET | `public/{orgId}/tracking?clientId=` | - | tracking config (enveloped or bare) | 0.0.62 |
| Record a consent decision | POST | `public/{orgId}/consent` | consent record | empty | 0.0.73 |
| Read a checkout session's result after the Stripe return | GET | `public/{orgId}/checkout/{sessionId}` | - | the session's conversion data | 0.0.62 |
| Mark that conversion as reported to the vendors | POST | `public/{orgId}/checkout/{sessionId}/reported` | - | empty | 0.0.62 |
| The org's agent-readiness bundle (fail-soft, cached by the SDK) | GET | `public/{orgId}/agent-readiness` | - | discovery bundle for `llms.txt` and `.well-known` | 0.0.49 |
| Invitation preview | GET | `public/{orgId}/invitations/preview/{token}` | - | see [invitations](#workspace-invitations) | 0.0.71 |

---

## Beta

basePath `beta` instead of `public`, no auth headers: `GET /api/v1/beta/config?orgId=` returns the beta form configuration; `POST /api/v1/beta/submit` with `{ orgId, formData: { name, email, country?, language?, timezone?, currency?, context? } }` submits a beta request.

---

## Org-token content client (`@buildbase/sdk/server`)

Since 0.0.73 the `server` entry point reads **content** with an org API token, not a session. Different base and header: `{serverUrl}/api/...` (no `/v1/public`), `Authorization: Bearer <orgId>:<secret>`. Read-only. This is the org-token surface described in [org-api.md](./org-api.md), wrapped for Node; the paths are the console's own.

| Resource | Paths |
|---|---|
| Blog posts, docs pages | `GET /api/blogs`, `GET /api/docs`; each with `/{id}`, `/path?path=`, `/folders/tree`, `/tags`, `/authors` |
| FAQ collections | `GET /api/faqs/collections`, `/api/faqs/collections/{id}`, `/api/faqs/collections/slug/{slug}`, and `.../faqs?pagination=false` under either |
| Testimonials | `GET /api/testimonials`, `/api/testimonials/{id}` |
| Rich content | `GET /api/rich-content` (optionally `?filter[archived]=false`), `/api/rich-content/slug/{slug}` |
| Collections | `GET /api/collections`, `/api/collections/data/{slug}?latest=true` or `?version=N` |

List responses follow the shared `{ docs, ... }` contract; `pagination=false` still returns that object with `limit: 0`, never a bare array.

---

## Called by your app, not by the SDK

Two exchanges the catalog names for completeness. The SDK does not call either; `withSession(sessionId)` only binds an existing session id.

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Code to session exchange (your `/api/auth/token` route) | POST | `/api/v1/auth/token` | `{ code, clientId, clientSecret, orgId }` | `{ data: { sessionId, user } }` |
| Org API token to user session (backends and jobs) | POST | `public/token/exchange` | `{ token: "<orgId>:<secret>", expiresIn?, userId? }` | `{ sessionId, expiresIn, userId, orgId }`. See [using-from-any-language.md](./using-from-any-language.md#acting-for-one-of-your-app-users) |
