# Glossary

**Org (Organization)** - A company or product that uses Buildbase. Identified by `orgId` (24 hex characters). Contains all workspaces, users, plans, and settings.

**Claimable organization** - An organization an agent or a CLI creates with no account (`npx @buildbase/sdk init --claim --yes`, or keyless development through `@buildbase/sdk/keyless`). It works at once on an unclaimed organization's caps and is deleted after 72 hours unless a person claims it with the claim link and code.

**Environment** - A development or staging copy of an org, with its own database, users and sign-in client, named by an eight-letter lowercase key. Pass it as `environment` on `SaaSOSProvider`, `BuildBase()`, `createAgentStack` or `BuildBaseTracking`; the SDK then sends `<orgId>-<key>` wherever it sent `orgId`. Unset is production, and it is never inferred from `NODE_ENV`.

**Workspace** - The tenant/team unit. Subscriptions, quotas, credits, and feature flags belong to workspaces by default. Similar to a "team" in Slack or "organization" in GitHub.

**User** - A person who authenticates. Can belong to multiple workspaces with different roles in each. Since 1.0.0 a user can also hold a plan, a credit wallet and add-ons of their own (the `{ user: true }` subject), never merged with a workspace's.

**Session** - Authentication state for a user. Represented as a `sessionId` - an opaque token string issued by the Buildbase server after OAuth login.

**sessionId** - The Buildbase authentication token. Your server keeps it in an httpOnly cookie; the browser SDK restores it through `getSession` and sends it on its API calls.

**SaaSOSProvider** - The root React provider for the Buildbase SDK. Must wrap your entire application. Configures auth, server URL, org ID, environment, and locale. `BuildBaseProvider` is the same component under its brand name.

**BuildBase()** - The server-side factory function, the default export of `@buildbase/sdk`. Called once to create action modules (workspace, subscription, entitlements, usage, credits, etc.) for API routes and background jobs.

**Server client** - `createServerClient({ serverUrl, apiToken })` from `@buildbase/sdk/server`, with an org API token and no end user: content and collection reads, transactional email (`emails.send`), subscribers, and the commerce back office.

**Plan** - A subscription tier (Free, Pro, Enterprise). Defined in Buildbase dashboard, connected to Stripe. Plans have prices, quotas, features, and trial settings. A plan belongs to a workspace or, in a pricing group whose payer is a person, to a user.

**Plan Group** - A collection of plans shown together (e.g., "main-pricing" might have Free, Pro, Enterprise). Referenced by slug in `usePublicPlans` and `PricingPage`.

**Entitlement** - What a workspace or person may use right now, answered by slug from the server: the plan plus anything granted on top (add-ons, overrides). Read with `useEntitlement` / `useLimit` or gate with `WhenEntitled`; prefer these to plan-name checks.

**Add-on** - Something sold beside a plan (one-time, lifetime, consumable or recurring) that grants entitlements on top of it. Hooks: `useAddOns`, `usePurchaseAddOn`, `useGrants`.

**Quota** - A usage limit included in a plan (API calls, storage, emails). Resets each billing period. Can have overage pricing.

**Quota Slug** - The identifier for a quota (e.g., `api_calls`, `emails`, `storage`). Must match dashboard configuration.

**Credit** - A prepaid unit purchased separately from subscriptions. Does not reset automatically. Used for AI tokens, compute, one-off actions.

**Feature Flag** - A boolean toggle per workspace or user. Defined in dashboard, toggled via SDK or dashboard.

**Gate Component** - A conditional render component that shows/hides content based on state. Examples: `WhenEntitled`, `WhenSubscription`, `WhenQuotaAvailable`, `WhenCreditsAvailable`.

**ClientId** - OAuth app identifier. Public-safe (used on client side). Created in Buildbase dashboard → Auth.

**ClientSecret** - OAuth app secret. Server-side only. NEVER expose to client. Used in `/api/auth/token` endpoint (`exchangeAuthCode`).

**redirectUrl** - The URL Buildbase sends users back to after OAuth login. Must match what's configured in the OAuth app.

**httpOnly Cookie** - A browser cookie not readable by JavaScript. Used to keep `sessionId` on your server's side (`bb-session-id` in the routes `init` writes).

**Pricing Variant** - A currency-specific version of a plan's pricing. Enables multi-currency billing.

**Overage** - Usage beyond the included quota amount. Billed per-unit automatically via Stripe if configured.

**Workspace Mode** - Either "Personal" (one user, one workspace) or "Platform" (multi-user, multi-workspace). Set in dashboard under Workspaces, Settings. A new org starts in Personal.

**Service Session** - A `sessionId` a background job passes to `withSession(...)` instead of the request's cookie. For server work that needs no signed-in person, the server client's org API token is often the better fit.

**Org API token** - An `<orgId>:<secret>` key with an API role, for the org API and `@buildbase/sdk/server`. Server-only, like the client secret.

**Token Exchange** - The process of swapping `code` (from OAuth redirect) for a `sessionId`. Happens server-side in `/api/auth/token`, with `exchangeAuthCode` (or `BuildBase().exchangeCode`).

**RBAC** - Role-Based Access Control. Users have a role within each workspace. `admin`, `editor` and `viewer` are built in and the org can add its own. No member's role is ever `owner`: the workspace's creator starts as `admin`, and "is this the creator?" is `usePermissions().isOwner`. Gates: `WhenWorkspaceRoles`, `WhenPermission`.

**Event Emitter** - The SDK's internal system for dispatching events (`workspace:changed`, `user:created`, etc.) that can be listened to via `handleEvent` callback.

**Workspace Settings Provider** - Internal SDK provider that powers the built-in workspace settings dialog (users, billing, features, permissions).

**Push Service Worker** - A JavaScript file served at `/push-sw.js` for browser push notifications. The SDK ships it as `PUSH_SERVICE_WORKER_SCRIPT`; write it into `public/` at build time.

**Ad-hoc Notification** - A notification sent with an event slug that was not created in the dashboard first. Since server release 22 the slug registers itself on first send and counts toward the plan's custom-event limit.

**Blueprint** - The org's console configuration as one JSON file (`buildbase.blueprint.json`): settings, sign-in, email, billing, roles, webhooks and workflows. Validated, planned and applied by an owner or admin with `npx @buildbase/sdk blueprint`, in the console, or through the hosted MCP.

**BuildBase Console MCP** - BuildBase's own hosted MCP server at `https://api.console.buildbase.app/mcp`. An agent signs in as the person and works in their BuildBase organizations. Not the same as the app's own MCP server, built with `@buildbase/sdk/mcp` (`createAgentStack`).

**Regional serverUrl** - Each org lives in one cell, and `serverUrl` must be that cell's URL. Today every org is on `https://api.console.buildbase.app`; an app serving many orgs resolves the URL per request with `resolveServerUrl`. A request sent to the wrong cell gets `421 misdirected_request`.

**Enterprise SSO and Directory Sync** - A customer company's own identity provider (SAML or OIDC) and directory (SCIM), connected through the app owner's own WorkOS account. The SDK's `EnterpriseAccess` screen and `useEnterprise*` hooks manage it.
