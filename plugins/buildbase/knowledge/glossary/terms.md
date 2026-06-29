# Glossary

**Org (Organization)** — A company or product that uses Buildbase. Identified by `orgId`. Contains all workspaces, users, plans, and settings.

**Workspace** — The tenant/team unit. Subscriptions, quotas, credits, and feature flags belong to workspaces. Similar to a "team" in Slack or "organization" in GitHub.

**User** — A person who authenticates. Can belong to multiple workspaces with different roles in each.

**Session** — Authentication state for a user. Represented as a `sessionId` — an opaque token string issued by the Buildbase server after OAuth login.

**sessionId** — The Buildbase authentication token. Stored in an httpOnly cookie. Used in all SDK API calls.

**SaaSOSProvider** — The root React provider for the Buildbase SDK. Must wrap your entire application. Configures auth, server URL, org ID, and locale.

**BuildBase()** — The server-side factory function. Called once to create action modules (workspace, subscription, usage, etc.) for API routes and background jobs.

**Plan** — A subscription tier (Free, Pro, Enterprise). Defined in Buildbase dashboard, connected to Stripe. Plans have prices, quotas, features, and trial settings.

**Plan Group** — A collection of plans shown together (e.g., "main-pricing" might have Free, Pro, Enterprise). Referenced by slug in `usePublicPlans` and `PricingPage`.

**Quota** — A usage limit included in a plan (API calls, storage, emails). Resets each billing period. Can have overage pricing.

**Quota Slug** — The identifier for a quota (e.g., `api_calls`, `emails`, `storage`). Must match dashboard configuration.

**Credit** — A prepaid unit purchased separately from subscriptions. Does not reset automatically. Used for AI tokens, compute, one-off actions.

**Feature Flag** — A boolean toggle per workspace or user. Defined in dashboard, toggled via SDK or dashboard.

**Gate Component** — A conditional render component that shows/hides content based on state. Examples: `WhenSubscription`, `WhenQuotaAvailable`, `WhenCreditsAvailable`.

**ClientId** — OAuth app identifier. Public-safe (used on client side). Created in Buildbase dashboard → Auth.

**ClientSecret** — OAuth app secret. Server-side only. NEVER expose to client. Used in `/api/auth/token` endpoint.

**redirectUrl** — The URL Buildbase sends users back to after OAuth login. Must match what's configured in the OAuth app.

**httpOnly Cookie** — A browser cookie not readable by JavaScript. Used to store `sessionId` securely (prevents XSS attacks on session tokens).

**Pricing Variant** — A currency-specific version of a plan's pricing. Enables multi-currency billing.

**Overage** — Usage beyond the included quota amount. Billed per-unit automatically via Stripe if configured.

**Workspace Mode** — Either "Personal" (one user, one workspace) or "Platform" (multi-user, multi-workspace). Set in dashboard.

**Service Session** — A `sessionId` used for background jobs/service accounts, not tied to a specific logged-in user. Obtained via the token exchange endpoint.

**Token Exchange** — The process of swapping `code` (from OAuth redirect) for a `sessionId`. Happens server-side in `/api/auth/token`.

**RBAC** — Role-Based Access Control. Users have a role within each workspace. Roles are developer-defined strings (commonly `owner`, `admin`, `member`) configured in the dashboard — not a fixed built-in set. Gates: `WhenWorkspaceRoles`.

**Event Emitter** — The SDK's internal system for dispatching events (workspace:changed, user:created, etc.) that can be listened to via `handleEvent` callback.

**Workspace Settings Provider** — Internal SDK provider that powers the built-in workspace settings dialog (users, billing, features, permissions).

**Push Service Worker** — A JavaScript file at `public/push-sw.js` required for browser push notifications. Provided verbatim in the SDK documentation.

**Ad-hoc Notification** — A push notification sent with any event slug without pre-registering the event in the dashboard.
