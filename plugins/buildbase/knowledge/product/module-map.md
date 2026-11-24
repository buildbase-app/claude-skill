# What BuildBase does, and which surface you reach it through

Twenty modules. The question that matters for an agent is not "does BuildBase have X" but **"through which surface do I reach X"**, because the answer decides whether you write React, call a server client, call the org API, or tell the person to open the console.

The surfaces:

- **SDK, React** - hooks, gates and components from `@buildbase/sdk/react`. Runs in the customer's app and acts as the signed-in end user.
- **SDK, server** - the `BuildBase()` factory from `@buildbase/sdk` acts for a signed-in user's session. `@buildbase/sdk/server` (`createServerClient` with an org API token, no end user involved) reads content and collections (0.0.73), sends transactional email and manages subscribers (`emails.*`, `subscribers.*`, 1.0.0), and runs the app's commerce back office (`commerce.*`, 1.2.0). See [../sdk/server-side.md](../sdk/server-side.md).
- **Org API** - `/api/*` with an `orgId:secret` key, authorizing as a role. This is the console's own REST API. See [../http-api/org-api.md](../http-api/org-api.md).
- **Console** - configuration: plans, slugs, credentials, templates. The app's code cannot create these, and referencing a slug that does not exist fails silently. Since 1.0.0 most of it can also live in one file, `buildbase.blueprint.json`, which an owner or admin checks, plans and applies with `npx @buildbase/sdk blueprint`, the console's "Set up from one file" screen, or the hosted MCP below ([docs](https://docs.buildbase.app/blueprints/overview)).
- **BuildBase Console MCP** - `https://api.console.buildbase.app/mcp`, BuildBase's own hosted MCP server. An agent signs in over OAuth as the person and reads and changes their BuildBase organizations (console reads and writes, blueprints, docs search, env templates), within the person's role and the organization's AI agents setting, with deletes and other destructive changes approved by the person ([docs](https://docs.buildbase.app/console/ai-agents)). It manages BuildBase itself. It is not the app's own MCP server, which the app builds with `@buildbase/sdk/mcp` ([../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md)).

## The map

| Module | SDK surface | Org API | Docs |
|---|---|---|---|
| Authentication | Yes. `useSaaSAuth`, auth gates; sign-in on the app's server with `exchangeAuthCode` / `createAuthHandler` (1.6.0); enterprise SSO and Directory Sync screens and hooks (`EnterpriseAccess`, `useEnterprise`), through the app owner's own WorkOS account | `/api/auth`, `/api/tokens` | `/authentication/overview` |
| Multi-tenant workspaces | Yes. `useSaaSWorkspaces`, `WorkspaceSwitcher` | `/api/workspaces` | `/workspaces/overview` |
| Billing and subscriptions | Yes. `useEntitlement`, `WhenEntitled`, subscription gates, `PricingPage`, `useSubscription`, add-on hooks (`useAddOns`, `usePurchaseAddOn`); most take `{ user: true }` to bill the person instead of a workspace (1.0.0); selling and buying through the app is commerce ([../sdk/commerce.md](../sdk/commerce.md)) | `/api/subscriptions` | `/billing/overview` |
| Credits and usage metering | Yes. Credit and quota gates, `useConsumeCredits`, `useRecordUsage`, `useReserveCredits` | `/api/subscriptions/credits` | `/credits/overview` |
| Feature flags | Yes. `useUserFeatures`, workspace and user feature gates | `/api/features` | `/feature-flags/overview` |
| Access control (RBAC) | Yes. `usePermissions`, `WhenPermission`, `WhenRoles` | `/api/access-control` | `/permissions/overview` |
| Push notifications | Yes. `usePushNotifications` | `/api/organizations/push` | `/push-notifications/overview` |
| Slack and team notifications | None. Console only: paste a Slack incoming webhook URL and pick the events | - | `/notifications/slack` |
| User and audience management | Partial. `useUserAttributes` for the signed-in user; `subscribers.*` from a server through `@buildbase/sdk/server`; `npx @buildbase/sdk import` moves users in from Clerk, Auth0, Firebase or Supabase | `/api/users`, `/api/audience` | `/users/overview` |
| SDK and API | n/a, this is the SDK itself | - | `/quick-start/installation` |
| Tracking and tags | Yes. `SaaSOSProvider tracking={...}`, or `BuildBaseTracking` and `useTracking` from `@buildbase/sdk/tracking` for a page without the provider | `/api/organizations/tracking/scripts` | `/tracking/overview` |
| Webhooks and events | Verification helpers and the event catalog. `parseWebhookEvent`, `verifyWebhookSignature`, `WEBHOOK_EVENTS` | `/api/organizations/webhooks` | `/webhooks/overview` |
| **Email campaigns** | **No React surface.** From a server through `@buildbase/sdk/server` (org token, 1.0.0): `emails.send` / `get` for one transactional email from a console template, `subscribers.*` for the audience. Campaigns themselves are console only | `/api/emails` | `/email/overview` |
| **Workflow automation** | **None** | `/api/workflows` | `/workflows/overview` |
| **Collections and custom data** | **No React surface.** Read-only from a server through `@buildbase/sdk/server` (org token, 0.0.73) | `/api/collections` | `/collections/overview` |
| **Content management** | **No React surface.** Read-only from a server through `@buildbase/sdk/server` (org token, 0.0.73): blogs, docs, FAQs, testimonials, rich content | `/api/blogs`, `/api/docs`, `/api/faqs` | `/content/overview` |
| **Forms** | **None** | `/api/forms` | `/forms/overview` |
| **Short links** | **None** | `/api/links` | `/links/overview` |
| **Assets and media** | **Narrow.** `useUpload` (0.0.84) lets the app's users upload a workspace image or a profile picture, stored in Assets. Nothing else | `/api/assets` | `/assets/overview` |
| **Analytics and reporting** | **Narrow.** Web analytics collection starts with the provider (`analytics` prop, on by default) or `BuildBaseTracking`; `trackGoal` from `@buildbase/sdk/tracking` records a goal. The reports are console only | `/api/analytics/web`, and per module | `/analytics/overview` |

Docs paths are relative to `https://docs.buildbase.app`.

Notification events are not a module of their own: `notification.send` on the server (and `NotificationBell` / `NotificationInbox` in React) reach a user or a workspace by email, push and the in-app inbox ([../sdk/notifications.md](../sdk/notifications.md), docs `/notifications/overview`).

## The rule this table exists to enforce

**Six of the twenty modules have no React surface at all**: email campaigns, workflows, collections, content, forms and short links. There is no `useCollections`, no `useWorkflows`, no `useEmailCampaigns`. If a developer asks for a hook for one of them, say plainly that the SDK does not expose one and route them to the right surface:

- Content and collections can be *read* from a server with an org token through `@buildbase/sdk/server` (see [../sdk/server-side.md](../sdk/server-side.md) and the routes in [../http-api/endpoints.md](../http-api/endpoints.md#org-token-routes-the-sdk-calls)).
- Transactional email and subscribers are *written* from a server through the same client (`emails.send`, `subscribers.upsert`), never from the browser.
- Everything else in those six is the org API or the console.

Those are server imports, not hooks. Two more modules have only a narrow SDK surface: assets (`useUpload`, for end-user uploads) and analytics (web analytics collection; reading the reports is console only). Inventing a hook name is the failure mode this page prevents.

The inverse also holds. Before hand-building account, billing or membership UI, check [pre-built-ui.md](../sdk/pre-built-ui.md): 18 settings screens already exist (`SETTINGS_SCREENS`).

## Console-first, always

Every slug-based feature needs its object created in the console (or in an applied blueprint) before code referencing it works, and the failure is silent rather than loud:

| You reference | Must exist first |
|---|---|
| A plan or `PricingPage` slug | Plan, a **published** plan version, and a pricing group. Stripe connected under Billing then Credentials |
| A quota slug | The quota, defined on the plan |
| A feature slug | The feature, and it enabled on the relevant plans |
| An entitlement slug (`useEntitlement`, `WhenEntitled`) | The feature, limit or quota on the plan, or an add-on that grants it |
| A credit package | The package |
| A notification event slug | Optional since server release 22: a new slug registers itself on first send and counts toward the plan's custom-event limit. Creating it in the console first still lets you attach an email template before anything is sent |
| An API role for a key | The role, created as `kind: "api"` |
| An environment key (`environment`) | The development or staging environment, created in the console or with `npx @buildbase/sdk env create` |

A correct slug that does not exist yet raises no error. Most gates then render nothing; the entitlement gates do the opposite, because a slug the plan does not mention reads as `unknown` and `whileUnknown` defaults to `'allow'` (pass `strictAbsent` to lock it). When a gate "shows nothing", or shows something it should not, check this table before debugging code.

## Reading further

- Building against the SDK -> [../sdk/quick-start.md](../sdk/quick-start.md), then the file for the feature
- Driving the console by key -> [../http-api/org-api.md](../http-api/org-api.md)
- Making the app agent-ready -> [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md)
