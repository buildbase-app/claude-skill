# What BuildBase does, and which surface you reach it through

Twenty modules. The question that matters for an agent is not "does BuildBase have X" but **"through which surface do I reach X"**, because the answer decides whether you write React, call the org API, or tell the person to open the console.

Three surfaces:

- **SDK** - React hooks and components, plus the server client. Runs in the customer's app, acts as the signed-in end user. Since 0.0.73 the `@buildbase/sdk/server` entry also reads content and collections with an org API token (no end user involved).
- **Org API** - `/api/*` with an `orgId:secret` key, authorizing as a role. This is the console's own REST API. See [../http-api/org-api.md](../http-api/org-api.md).
- **Console** - configuration a human does once: plans, slugs, credentials, templates. Code cannot create these, and referencing a slug that does not exist fails silently.

## The map

| Module | SDK surface | Org API | Docs |
|---|---|---|---|
| Authentication | Yes. `useSaaSAuth`, auth gates | `/api/auth`, `/api/tokens` | `/authentication/overview` |
| Multi-tenant workspaces | Yes. `useSaaSWorkspaces`, `WorkspaceSwitcher` | `/api/workspaces` | `/workspaces/overview` |
| Billing and subscriptions | Yes. Subscription gates, `PricingPage`, `useSubscription` | `/api/subscriptions` | `/billing/overview` |
| Credits and usage metering | Yes. Credit and quota gates, `useConsumeCredits`, `useRecordUsage` | `/api/subscriptions/credits` | `/credits/overview` |
| Feature flags | Yes. `useUserFeatures`, workspace and user feature gates | `/api/features` | `/feature-flags/overview` |
| Access control (RBAC) | Yes. `usePermissions`, `WhenPermission`, `WhenRoles` | `/api/access-control` | `/permissions/overview` |
| Push notifications | Yes. `usePushNotifications` | `/api/organizations/push` | `/push-notifications/overview` |
| Slack and team notifications | Server client only. `notification.send` | - | `/notifications/overview` |
| User and audience management | Partial. `useUserAttributes` for the signed-in user | `/api/users`, `/api/audience` | `/users/overview` |
| SDK and API | n/a, this is the SDK itself | - | `/quick-start/installation` |
| Tracking and tags | Provider prop only. `tracking={{}}`, no hooks | `/api/organizations/tracking/scripts` | `/tracking/overview` |
| Webhooks and events | Verification helpers only. `parseWebhookEvent` | `/api/organizations/webhooks` | `/webhooks/overview` |
| **Email campaigns** | **None** | `/api/emails` | `/email/overview` |
| **Workflow automation** | **None** | `/api/workflows` | `/workflows/overview` |
| **Collections and custom data** | **No React surface.** Read-only from a server through `@buildbase/sdk/server` (org token, 0.0.73) | `/api/collections` | `/collections/overview` |
| **Content management** | **No React surface.** Read-only from a server through `@buildbase/sdk/server` (org token, 0.0.73): blogs, docs, FAQs, testimonials, rich content | `/api/blogs`, `/api/docs`, `/api/faqs` | `/content/overview` |
| **Forms** | **None** | `/api/forms` | `/forms/overview` |
| **Short links** | **None** | `/api/links` | `/links/overview` |
| **Assets and media** | **None** | `/api/assets` | `/assets/overview` |
| **Analytics and reporting** | **None** | varies by module | `/reference/reporting` |

Docs paths are relative to `https://docs.buildbase.app`.

## The rule this table exists to enforce

**Eight of the twenty modules have no React surface at all.** There is no `useCollections`, no `useWorkflows`, no `useEmailCampaigns`. If a developer asks for a hook for email, workflows, collections, content, forms, links, assets or reporting, say plainly that the SDK does not expose one and route them to the org API or the console. Two of the eight, content and collections, can be *read* from a server with an org token through `@buildbase/sdk/server` (see [../http-api/endpoints.md](../http-api/endpoints.md#org-token-content-client-buildbasesdkserver)); that is a server import, not a hook. Inventing a hook name is the failure mode this page prevents.

The inverse also holds. Before hand-building account, billing or membership UI, check [pre-built-ui.md](../sdk/pre-built-ui.md): 13 settings screens already exist.

## Console-first, always

Every slug-based feature needs its object created in the console before code referencing it works, and the failure is silent rather than loud:

| You reference | Must exist first |
|---|---|
| A plan or `PricingPage` slug | Plan, a **published** plan version, and a pricing group. Stripe connected under Billing then Credentials |
| A quota slug | The quota, defined on the plan |
| A feature slug | The feature, and it enabled on the relevant plans |
| A credit package | The package |
| A notification event slug | Optional since server release 22: a new slug registers itself on first send and counts toward the plan's custom-event limit. Creating it in the console first still lets you attach an email template before anything is sent |
| An API role for a key | The role, created as `kind: "api"` |

A correct slug that does not exist yet renders nothing and raises no error. When a gate "shows nothing", check this table before debugging code.

## Reading further

- Building against the SDK -> [../sdk/quick-start.md](../sdk/quick-start.md), then the file for the feature
- Driving the console by key -> [../http-api/org-api.md](../http-api/org-api.md)
- Making the app agent-ready -> [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md)
