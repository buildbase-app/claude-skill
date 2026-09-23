# Org API - drive the console with an API key

This is the **operator's** half of BuildBase. An org API key authorizes as a role you choose and reaches the console's own REST API, so everything a person does by clicking, a script or an agent can do by calling. Use this page when the user is an org owner or admin asking to *run* their BuildBase, not a developer integrating the SDK into an app.

Wrong page if: they are wiring auth into their product (that is [../sdk/quick-start.md](../sdk/quick-start.md)), or acting on behalf of one of *their* end users (that is [using-from-any-language.md](./using-from-any-language.md#acting-for-one-of-your-app-users)).

> **Source:** [docs.buildbase.app/reference/admin-api](https://docs.buildbase.app/reference/admin-api). Every base path below is mirrored from `API_ROUTES` in the platform's shared constants.

## Contents

- [Get a key](#get-a-key) - console or API, and give it a role
- [Authenticate](#authenticate) - one header
- [What a key can reach](#what-a-key-can-reach) - and the limits that are real
- [Response and error shapes](#response-and-error-shapes) - three of them, branch on status
- [Listing and pagination](#listing-and-pagination) - one contract for every module
- [Module map](#module-map) - which base path serves which module
- [Before you act for someone](#before-you-act-for-someone) - the autonomy rule

---

## Get a key

Console: **Settings -> API tokens**. Or over the API:

```bash
curl -X POST https://api.console.buildbase.app/api/tokens \
  -H "Authorization: $BUILDBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"changelog-bot","role":"content-editor"}'
```

The body accepts `name` (required), `description`, `expiresAt` and `role`. Nothing else - `scopes` was removed and is rejected with a message pointing at API Roles.

**`POST` is the only response that ever contains the full secret.** A listing returns a masked `tokenPreview` and omits `token` entirely, so a key that is lost cannot be read back; delete it and make another.

### Give it a role, or it inherits yours

`role` is how a key gets *less* access than the person creating it. Three rules on create: the role must already exist, it must be an **API role** rather than a user role (the built-ins `owner`, `admin` and `user` count as both), and it may not exceed what the creator holds.

Create API roles under **Settings -> API Roles**, or `POST /api/access-control/save-role` with `"kind": "api"`. List what a key may be given with `GET /api/access-control/roles?kind=api`.

Two consequences worth stating to the user before they mint anything:

- **Omitting `role` is not a narrow key, it is a full one.** It falls back to the creator's role, so a key an admin creates without a role is an admin credential.
- **The role is fixed once issued.** `PATCH` will not change it, deliberately: re-pointing a live credential is a privilege change on something already deployed. To change what a key can do, either edit the permissions of the role it carries - which applies immediately to every key on that role, with no re-issue - or issue a new key and deactivate the old one.

`expiresAt` is optional, validated as a future date, and re-checked on the cached path as well as the database, so an expired key stops working when it expires. Set one where you can.

---

## Authenticate

One header. A `Bearer ` prefix is stripped if present, so both forms work:

```bash
curl https://api.console.buildbase.app/api/links \
  -H "Authorization: 665f1a2b3c4d5e6f7a8b9c0d:your-token-secret"
```

The token is `<orgId>:<secret>` - the org's ObjectId, a colon, then a 60-character secret. The router decides which credential it holds by looking for a colon, so an API token always contains one and a session JWT never may.

Keep the key server-side. It carries real permissions and must never reach a browser.

---

## What a key can reach

**The whole tenant API, organization administration included** - settings, outbound webhooks, push campaigns and credentials, Stripe credentials - and the control plane too: members and invitations, installations, and the shared email template library.

The limits that are actually real:

- **The role governs organization permissions, not workspace ones.** Workspace permissions resolve from the person who created the key, and resource ownership treats the key as owning what they own. So a key issued as `viewer` by an admin is a viewer across the org and still an admin inside the workspaces that person belongs to. For a key that must be narrow inside a workspace too, create it from an account whose membership is already limited.
- **A few actions are closed to custom roles by design**, for a person and a key alike: claiming ownership of a shared template, resetting a system template. Those need owner or admin however the permission is granted.
- **Control-plane calls resolve through the server that owns the key.** Keys live in the org's own database, so the control plane asks that server rather than reading it. The result is cached, but if the tenant server is unreachable, control-plane calls made with a key fail closed while a browser session keeps working.
- **Permission coverage is not uniform.** Authentication and authorization are separate layers: every `/api` route needs a valid token, but only routes that opt in check a specific permission. Some groups authenticate without a permission check, so a valid key reaches them whatever role it carries. A key created by an `admin` bypasses permission checks entirely.

Where a guard is present it maps the HTTP method to the action: `GET` needs `read`, `POST` needs `create`, `PATCH`/`PUT` need `update`, `DELETE` needs `delete`. **The action comes from the method, not the intent** - pausing, resuming, retrying and cancelling are all `POST`, so they need `create`, and granting `update` does not let a role pause anything.

Workflows are split across eight resources (`workflows`, `workflows_versions`, `workflows_instances`, `workflows_actions`, `workflows_logs`, `workflows_templates`, `workflows_trigger_events`, `workflows_metrics`), so a support role that should see runs without touching definitions needs `read` on `workflows_instances` and nothing else.

---

## Response and error shapes

**There is no envelope.** A success returns the resource directly. Update-style endpoints return `{ "success": true, "message": "updated" }`.

Three different error shapes, depending on which layer rejected the request:

| Shape | Comes from |
|---|---|
| `{ error: true, message, path? }` | Shared validation and error helpers. Most 400, 404 and 409 |
| `{ success: false, message }` | Rate limiting, read-only impersonation, several hand-written handlers |
| Plain text `Unauthorized` | Every 401. Sent with `sendStatus`, so **no JSON body** |

**Branch on the HTTP status, not the body shape.** Reading `body.error` alone misses the `success: false` family, and calling `.json()` on a 401 throws.

Two more traps:

- **`503`, not `500`, is the server-error code** in the shared error map. Retry logic keyed on 500 misses BuildBase server errors.
- **A `200` does not always mean success.** Some handlers report failure in the body while returning 200. Workflow publishing is the clearest case: a validation failure is a `200` carrying `{ "success": false }`. Check `success` wherever it appears.

Rate limits are **500 requests per 3 seconds per IP** globally, with stricter per-minute limits on auth (20/min login, 10/min OTP, 10/min token exchange), usage recording (60/min) and credit consumption (30/min). **Limits count per IP, not per token**, so every key behind one egress address shares a budget. A 429 carries the standard `RateLimit-*` headers; the legacy `X-RateLimit-*` ones are disabled.

---

## Listing and pagination

Every collection endpoint runs the same handler, so this works identically across modules.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `$page` | number | `1` | Page number, 1-indexed |
| `$limit` | number | controller default (10) | Items per page. Capped at 1000 |
| `filter` | object | `{}` | Mongo-style query, flattened before use |
| `sort` | object | - | Field to direction, e.g. `{"createdAt":-1}` |
| `populate` | string | `''` | Space-separated reference fields to expand |
| `projection` | object | `{}` | Fields to include or exclude |
| `pagination` | boolean | `true` | `false` returns every match, unpaged |

Note the `$` on `$page` and `$limit` and its absence on the others. Neither has a route-level default, so set `$limit` explicitly.

**`$limit` is clamped, not refused.** Ask for more than 1000 and you get 1000, with nothing in the response saying so - the `limit` field reports what you were given, not what you asked for. A `0`, a negative or an unparseable value falls back to the controller default rather than erroring. Page through on `hasNextPage` rather than on arithmetic over a limit you assumed you had.

```bash
curl -G https://api.console.buildbase.app/api/links \
  -H "Authorization: $BUILDBASE_TOKEN" \
  --data-urlencode '$page=2' \
  --data-urlencode '$limit=25' \
  --data-urlencode 'filter={"active":true}' \
  --data-urlencode 'sort={"createdAt":-1}'
```

**`filter` is not passed to Mongo verbatim.** It is flattened to dot-notation then re-nested one level, so operators survive (`{"status":{"$in":["a","b"]}}` works) but a path two or more levels deep does not round-trip. For a deep field send the dotted path yourself as a flat key: `{"owner.profile.city":"X"}`.

A paged response uses `mongoose-paginate-v2` labels: `{ docs, totalDocs, limit, page, totalPages, pagingCounter, hasPrevPage, hasNextPage, prevPage, nextPage }`, with `prevPage`/`nextPage` null at the ends.

**`pagination=false` does not change that shape.** It returns every match, still wrapped in the same object, reporting `limit: 0`. The rows are always at `.docs`, there is no array form, and code that branches on `Array.isArray` takes the wrong branch every time.

---

## Module map

Which base path serves which module, and where its docs are. Mirrored from `API_ROUTES`.

| Module | Base paths | Docs |
|---|---|---|
| Access Control (RBAC) | `/api/access-control` | [/permissions/overview](https://docs.buildbase.app/permissions/overview) |
| Assets & Media | `/api/assets` | [/assets/overview](https://docs.buildbase.app/assets/overview) |
| Authentication | `/api/auth` `/api/tokens` | [/authentication/overview](https://docs.buildbase.app/authentication/overview) |
| Billing & Subscriptions | `/api/subscriptions` `/api/subscriptions/plans` `/api/payments` | [/billing/overview](https://docs.buildbase.app/billing/overview) |
| Collections & Custom Data | `/api/collections` | [/collections/overview](https://docs.buildbase.app/collections/overview) |
| Content Management | `/api/blogs` `/api/docs` `/api/faqs` `/api/rich-content` `/api/testimonials` | [/content/overview](https://docs.buildbase.app/content/overview) |
| Credits & Usage Metering | `/api/subscriptions/credits` `/api/subscriptions/credit-packages` | [/credits/overview](https://docs.buildbase.app/credits/overview) |
| Email Campaigns | `/api/emails` `/api/emails/campaigns` `/api/emails/templates` `/api/emails/senders` `/api/emails/domains` | [/email/overview](https://docs.buildbase.app/email/overview) |
| Feature Flags | `/api/features` | [/feature-flags/overview](https://docs.buildbase.app/feature-flags/overview) |
| Forms & Data Collection | `/api/forms` | [/forms/overview](https://docs.buildbase.app/forms/overview) |
| Multi-Tenant Workspaces | `/api/workspaces` | [/workspaces/overview](https://docs.buildbase.app/workspaces/overview) |
| Push Notifications | `/api/organizations/push` `/api/organizations/push/campaigns` | [/push-notifications/overview](https://docs.buildbase.app/push-notifications/overview) |
| Short Links | `/api/links` `/api/links-analytics` | [/links/overview](https://docs.buildbase.app/links/overview) |
| Tracking & Tags | `/api/organizations/tracking/scripts` | [/tracking/overview](https://docs.buildbase.app/tracking/overview) |
| User & Audience Management | `/api/users` `/api/audience` `/api/audience-lists` `/api/users-list` | [/users/overview](https://docs.buildbase.app/users/overview) |
| Webhooks & Events | `/api/organizations/webhooks` | [/webhooks/overview](https://docs.buildbase.app/webhooks/overview) |
| Workflow Automation | `/api/workflows` `/api/workflows/templates` `/api/workflows/definitions` `/api/workflows/instances` | [/workflows/overview](https://docs.buildbase.app/workflows/overview) |

There is **no endpoint that lists endpoints**, and no OpenAPI document, so do not promise the user a machine-readable catalog. `GET /api/workflows/definitions` is the one self-describing exception: it publishes the workflow node catalog with inputs and outputs. For anything else, read the module's docs page and the shared list contract above.

---

## Before you act for someone

An API key is a real credential with real permissions, so treat what you do with it by blast radius rather than by how easy the call is.

| Autonomy | What it covers | Rule |
|---|---|---|
| **Answer** | Explaining a flow, showing the curl | Always fine |
| **Guide** | Reads. `GET` anything the key can reach | Fine to run. Show what you ran |
| **Act** | Reversible writes: create a link, a draft, a template, a tag | Only with the user's explicit go-ahead **in this conversation**. Show the exact request first |
| **Never alone** | Irreversible or outward-facing: `DELETE` anything, sending a campaign, checkout, cancelling a subscription, revoking a key, editing a role's permissions | Explain it, show the request, and let the person run it |

Two specifics that are easy to get wrong:

- **Editing a role's permissions is not a small write.** It applies immediately to every key carrying that role, with no re-issue and no per-key audit of what changed.
- **A key the user pastes into chat is a live secret.** Use it for the calls they asked for, do not write it into a file, and suggest rotating it if it may have been shared more widely.

---

## Read next

- Acting for one of *their* end users -> [using-from-any-language.md](./using-from-any-language.md#acting-for-one-of-your-app-users)
- The SDK's own HTTP surface -> [overview.md](./overview.md), [endpoints.md](./endpoints.md)
- Verifying inbound webhooks -> [webhooks.md](./webhooks.md)
