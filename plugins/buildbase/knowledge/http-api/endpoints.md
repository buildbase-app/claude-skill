# HTTP API — Endpoint Catalog

Every endpoint the `@buildbase/sdk` calls, extracted from source (`sdk/src/api/services/*.ts`, `sdk/src/lib/server-client.ts`). Paths below are the part after the base. Unless noted, the full URL is:

```
{serverUrl}/api/{version}/public/{path}      e.g. https://api.console.buildbase.app/api/v1/public/workspaces
```

All authenticated calls send `x-session-id: <sessionId>`. Bodies are JSON (`Content-Type: application/json`). See [overview.md](./overview.md) for envelope/error rules.

## Contents

- [Auth](#auth) — login request and code→session exchange
- [Profile & Users](#profile--users) — profile, attributes, user features
- [Settings (org-scoped, public path)](#settings-org-scoped-public-path) — org/OS settings
- [Workspaces & Members](#workspaces--members) — CRUD and membership
- [Features](#features) — workspace feature definitions and toggles
- [Subscription](#subscription) — checkout, upgrade, cancel, billing portal
- [Plans](#plans) — plan groups and public plan lookups
- [Invoices](#invoices) — list and fetch invoices
- [Usage / Quota](#usage--quota) — record usage and quota status
- [Credits](#credits) — balance, consume, purchase, transactions
- [Notifications](#notifications) — send events, events, preferences
- [Push](#push) — VAPID key, subscribe, unsubscribe
- [Permissions](#permissions) — local computation from three GETs

---

## Auth

`/auth/request` is the one endpoint that sits **outside** `/public`.

| Purpose | Method | Path | Auth | Body / Query | Response |
|---|---|---|---|---|---|
| Start login — get the provider redirect URL | POST | `/api/{version}/auth/request` | none | `{ orgId, clientId, redirect: { success, error } }` | `{ success, data: { redirectUrl }, message }` |
| Get current user's profile (also validates the session) | GET | `public/profile` | `x-session-id` | — | `IUser` |

> The secure **code→session exchange** (`POST /api/v1/auth/token` with `clientId`+`clientSecret`+`orgId`+`code` → `{ data: { sessionId, user } }`) is performed **server-side** and is how the official Next.js starter obtains the `sessionId`. It is not called by the SDK client package itself but is the correct server flow for any backend — see [using-from-any-language.md](./using-from-any-language.md).

---

## Profile & Users

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Get profile | GET | `public/profile` | — | `IUser` |
| Update profile | PATCH | `public/profile` | `Partial<IUser>` | `IUser` |
| Get user attributes | GET | `public/users/attributes` | — | `Record<string, string\|number\|boolean>` |
| Bulk-update attributes | PATCH | `public/users/attributes` | `{ attributes: Record<string, …> }` | `IUser` |
| Update one attribute | PATCH | `public/users/attributes/{attributeKey}` | `{ value }` | `IUser` |
| Get resolved user feature flags | GET | `public/users/features` | — | `Record<string, boolean>` |

`IUser`: `{ _id, name, email, image?, role, country?, timezone?, language?, currency?, attributes?, createdAt, updatedAt }`.

---

## Settings (org-scoped, public path)

| Purpose | Method | Path | Response |
|---|---|---|---|
| Get org/OS settings | GET | `public/{orgId}/settings` | `ISettings` (includes the workspace permission template) |

---

## Workspaces & Members

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| List workspaces | GET | `public/workspaces` | — | `IWorkspace[]` |
| Create workspace | POST | `public/workspaces` | `{ name, image? }` | `IWorkspace` |
| Get one workspace | GET | `public/workspaces/{workspaceId}` | — | `IWorkspace` |
| Update workspace | PUT | `public/workspaces/{id}` | `Partial<IWorkspace>` | `IWorkspace` |
| Delete workspace | DELETE | `public/workspaces/{id}` | — | `{ success }` |
| List members | GET | `public/workspaces/{workspaceId}/users` | — | `IWorkspaceUser[]` |
| Invite / add member | POST | `public/workspaces/{workspaceId}/users/add` | `{ email, role }` | `{ userId, workspace, message }` |
| Remove member | DELETE | `public/workspaces/{workspaceId}/users/{userId}` | — | `{ userId, workspace, message }` |
| Update member (role) | PATCH | `public/workspaces/{workspaceId}/users/{userId}` | `Partial<IWorkspaceUser>` | `{ userId, workspace, message }` |
| Update workspace settings (permissions) | PATCH | `public/workspaces/settings` | `{ permissions: Record<role, string[]> }` | — |
| Update workspace permission matrix | PATCH | `public/workspaces/{workspaceId}/permissions` | `{ permissions: Record<role, string[]> }` | — |

---

## Features

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| List workspace feature definitions | GET | `public/workspaces/features` | — | `IWorkspaceFeature[]` |
| Toggle a workspace feature | PATCH | `public/workspaces/{workspaceId}/features` | `{ features: { [slug]: boolean } }` | `IWorkspace` |
| Get resolved user features | GET | `public/users/features` | — | `Record<string, boolean>` |

There is **no "check" endpoint** — fetch the map and look up the slug. A feature is on if present and `true`.

---

## Subscription

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Get current subscription | GET | `public/workspaces/{workspaceId}/subscription` | — | `ISubscriptionResponse` |
| Create checkout session | POST | `public/workspaces/{workspaceId}/subscription/checkout` | `{ planVersionId, billingInterval?, currency?, successUrl?, cancelUrl?, stripeOptions? }` | `CheckoutResult` (checkout / trial_started / existing) |
| Select a free plan | POST | `public/workspaces/{workspaceId}/subscription/select-free-plan` | `{ planVersionId }` | `{ success, message }` |
| Update (up/downgrade) | PATCH | `public/workspaces/{workspaceId}/subscription` | `{ planVersionId, billingInterval?, successUrl?, cancelUrl? }` | update result **or** checkout-session response if payment needed |
| Cancel at period end | POST | `public/workspaces/{workspaceId}/subscription/cancel-at-period-end` | — | `ISubscriptionResponse` |
| Resume | POST | `public/workspaces/{workspaceId}/subscription/resume` | — | `ISubscriptionResponse` |
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
| Get invoice | GET | `public/workspaces/{workspaceId}/subscription/invoices/{invoiceId}` | — | `IInvoiceResponse` |

`IInvoice`: `{ id, number, amount_due, amount_paid (cents), currency, status, created, due_date, hosted_invoice_url, invoice_pdf, description, subscription }`.

---

## Usage / Quota

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Record usage | POST | `public/workspaces/{workspaceId}/subscription/usage` | `{ quotaSlug, quantity, metadata?, source?, idempotencyKey? }` | `{ used, consumed, included, available, overage, billedAsync }` |
| Record usage batch (≤100) | POST | `public/workspaces/{workspaceId}/subscription/usage/batch` | `{ items: [{ quotaSlug, quantity, metadata?, source?, idempotencyKey? }] }` | `{ success, total, succeeded, failed, results[] }` |
| One quota status | GET | `public/workspaces/{workspaceId}/subscription/usage/status?quotaSlug={slug}` | — | `{ quotaSlug, consumed, included, available, overage, hasOverage, allowOverage? }` |
| All quota status | GET | `public/workspaces/{workspaceId}/subscription/usage/all` | — | `{ quotas: Record<slug, status> }` |
| Usage logs | GET | `public/workspaces/{workspaceId}/subscription/usage/logs` | `quotaSlug?, from?, to?, source?, page?, limit?` | paginated `{ docs[], totalDocs, page, totalPages, … }` |

---

## Credits

| Purpose | Method | Path | Body / Query | Response |
|---|---|---|---|---|
| Get balance | GET | `public/workspaces/{workspaceId}/credits` | — | `{ available, totalGranted, totalConsumed, totalExpired, totalRefunded }` |
| Consume credits | POST | `public/workspaces/{workspaceId}/credits/consume` | `{ amount, description?, idempotencyKey?, metadata? }` | `{ success, consumed, balanceAfter }` — **402** → insufficient (`{ available, requested }`) |
| Purchase package | POST | `public/workspaces/{workspaceId}/credits/purchase` | `{ creditPackageId, successUrl, cancelUrl, currency? }` | `{ sessionId, url }` |
| List packages | GET | `public/workspaces/{workspaceId}/credits/packages` | — | `ICreditPackage[]` — raw wire response may be paginated `{ docs: ICreditPackage[] }` (the SDK flattens `docs ?? data`) |
| Transactions | GET | `public/workspaces/{workspaceId}/credits/transactions` | `type?, page?, limit?` | paginated |
| Buckets | GET | `public/workspaces/{workspaceId}/credits/buckets` | `status?, source?, page?, limit?` | paginated |
| Expiring credits | GET | `public/workspaces/{workspaceId}/credits/expiring?days={n}` | `days?` (1–90, default 7) | `{ days, expiringCredits, buckets[] }` |
| **Public** packages by org | GET | `public/{orgId}/credit-packages` | none | `IPublicCreditPackagesResponse` |

---

## Notifications

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Send/trigger an event | POST | `public/workspaces/{workspaceId}/notifications/send` | `{ event, userId?, data? }` (omit `userId` → notify all members) | `{ sent, channels: { email, push }, notifiedCount?, reason? }` |
| List manageable events | GET | `public/workspaces/{workspaceId}/notification-events` | — | `NotificationEvent[]` |
| Get preferences | GET | `public/workspaces/{workspaceId}/notification-preferences` | — | wire response is wrapped: `{ notificationPreferences: Record<slug, { email?, push? }> }` (the SDK unwraps `.notificationPreferences`) |
| Update preferences | PATCH | `public/workspaces/{workspaceId}/notification-preferences` | `{ notificationPreferences: Record<slug, { email?, push? }> }` | same wrapped shape as GET |

`data` (NotificationData) supports: `title, message, icon, image, badge, url, tag, actions[≤2], silent, requireInteraction, renotify, timestamp, dir, ttl, urgency, scheduledAt, channels`, plus arbitrary merge-tag keys.

---

## Push

`PushApi` requires `orgId` to be configured.

| Purpose | Method | Path | Body | Response |
|---|---|---|---|---|
| Get VAPID public key | GET | `public/push/vapid-public-key` | — | `{ publicKey }` |
| Subscribe a device | POST | `public/push/subscribe` | `{ endpoint, keys: { p256dh, auth }, userAgent }` | empty (server may send a welcome push) |
| Unsubscribe a device | DELETE | `public/push/unsubscribe` | `{ endpoint }` | empty |

---

## Permissions

There is **no permission-check endpoint.** The SDK computes permissions locally from three GETs:

1. `GET public/workspaces/{workspaceId}` → the workspace (has `permissions: Record<role, string[]>`)
2. `GET public/{orgId}/settings` → org settings (workspace permission template)
3. `GET public/workspaces/{workspaceId}/users` → to find the caller's role

Then: find the user's role in (3), and check whether the requested permission is in the role's set from (1)/(2). Platform permissions look like `workspace:*`; app permissions are your own strings (e.g. `reports:export`). The write side is `PATCH public/workspaces/{workspaceId}/permissions`. To do this from another language, fetch the three and replicate the lookup — there is nothing to call for a single boolean answer.
