# MCP Server & Agent Readiness — `@buildbase/sdk/mcp`

Make a Buildbase-powered app connectable by AI agents (Claude Desktop/Code, Cursor, ChatGPT, MCP Inspector): a live MCP server on the app's own domain, OAuth discovery so agents authenticate with **zero manual config**, and the full agent-discovery document surface (`llms.txt`, `.well-known/*`, agent cards).

**Requires `@buildbase/sdk` ≥ 0.0.54** — the `@buildbase/sdk/mcp` entry point does not exist before that. Every API name, flow, and failure below was verified against 0.0.54 with a live end-to-end integration (Next.js 16 App Router + Claude Code as the MCP client), 2026-07-10.

---

## Mental model: who owns what

**The platform owns auth. The app owns everything else.**

- **Buildbase platform** (console.buildbase.app) runs the OAuth2 authorization server: login, consent screen, PKCE, dynamic client registration (RFC 7591), refresh rotation. It never mints and never sees the app's access tokens.
- **The app** mints its own tokens (HS256 with its own secret), serves all discovery documents locally, and runs the MCP server. The platform contributes exactly one thing to discovery: the pointer to its authorization server.
- **The agent can never exceed the user.** Every tool call runs under the granting user's Buildbase session (embedded encrypted in the token), so the platform enforces the user's real permissions.

The flow when an agent connects:

```
Agent → POST /mcp (no token) → 401 + WWW-Authenticate: resource_metadata=…
      → GET /.well-known/oauth-protected-resource/mcp   (app serves; points at platform AS)
      → GET platform /.well-known/oauth-authorization-server/org/<orgId>  (RFC 8414)
      → POST platform /register  (DCR — agent self-registers a PKCE-only public client)
      → browser: user logs in + approves scopes on consent screen
      → agent exchanges code at platform token endpoint
      → platform calls THE APP's applicationTokenUrl (signed) → app mints its own JWT
      → agent calls POST /mcp with Bearer <app JWT> → tools
```

---

## Setup — the order matters

### 0. Prereqs

- Working Buildbase auth integration (the app already signs users in — see `../sdk/quick-start.md`).
- `@buildbase/sdk@^0.0.54`.
- A **public HTTPS origin**. `localhost` cannot work for the token-mint step: the platform's servers call the app's endpoints and their SSRF guard blocks loopback/private addresses in production. For local dev, tunnel first (`ngrok http 3000`) and use the tunnel origin everywhere.

### 1. `src/lib/agent.ts` — one config for the whole surface

```ts
import { createAgentStack, defineMcpTool } from '@buildbase/sdk/mcp';
import { z } from 'zod';

export const agent = createAgentStack({
  serverUrl: process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!,
  orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!,
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL!,          // the PUBLIC origin
  site: { name: 'My App', description: 'What the app does.' },
  secret: process.env.SYSTEM_SECRET!,                  // app-owned; openssl rand -hex 32
  mcp: {
    // CRITICAL: serve at /mcp. The default is /api/mcp, but the canonical
    // RFC 9728 resource identifier is <host>/mcp — MCP clients (Claude Code
    // among them) REJECT the connection when endpoint ≠ declared resource:
    //   "Protected resource …/mcp does not match expected …/api/mcp"
    path: '/mcp',
    builtinTools: 'readonly',   // least privilege: 24 read tools. 'all' = 42.
    tools: [
      defineMcpTool({
        name: 'app_health',
        description: 'Liveness check.',
        inputSchema: z.object({}),               // zod schema (NOT `schema`)
        annotations: { readOnlyHint: true },
        execute: async () => ({ status: 'ok' }), // (NOT `handler`)
      }),
    ],
  },
  discovery: {
    llmsTxt: '# My App\n\n> …',                 // a STRING, not an object
    security: { contact: 'mailto:security@example.com', expires: '2027-01-01T00:00:00.000Z' },
    sitemap: { urls: ['/', '/dashboard'] },
  },
});
```

### 2. Route files (Next.js App Router) — all one-liners

| File | Content |
|---|---|
| `src/app/mcp/route.ts` | `export const { GET, POST, DELETE, OPTIONS } = agent.routes;` |
| `src/app/.well-known/[...path]/route.ts` | `export const GET = agent.serveAgentPath;` |
| `src/app/llms.txt/route.ts`, `llms-full.txt/`, `auth.md/`, `robots.txt/`, `security.txt/`, `sitemap.xml/` | `export const GET = agent.serveAgentPath;` (each) |

(Each file also needs `import { agent } from '@/lib/agent';`.)

### 3. The OAuth bridge routes — the platform calls these

```ts
// src/app/api/agent/token/route.ts  (applicationTokenUrl)
import { NextRequest, NextResponse } from 'next/server';
import { handleAppTokenRequest, mintAgentToken } from '@buildbase/sdk';

export async function POST(request: NextRequest) {
  const { status, body } = await handleAppTokenRequest({
    authorization: request.headers.get('authorization'),
    // MUST be the secret of the OAuth2 BASE client (see §Console + §Failures)
    clientSecret: process.env.BUILDBASE_AGENT_CLIENT_SECRET!,
    mintToken: (claims) =>
      mintAgentToken({ claims, secret: process.env.SYSTEM_SECRET! }),
  });
  return NextResponse.json(body, { status });
}
```

```ts
// src/app/api/agent/token/revoke/route.ts  (applicationRevokeUrl — optional but called for real)
import { NextRequest, NextResponse } from 'next/server';
import { handleAppRevokeRequest } from '@buildbase/sdk';

export async function POST(request: NextRequest) {
  const { status, body } = await handleAppRevokeRequest({
    authorization: request.headers.get('authorization'),
    clientSecret: process.env.BUILDBASE_AGENT_CLIENT_SECRET!,
    onRevoke: async (claims) => {
      // Tokens are short-lived stateless JWTs; purge any denylist/session store here.
      // claims: { userId, clientId, reason }
    },
  });
  return NextResponse.json(body, { status });
}
```

### 4. Console — OAuth2 client for agents

Dashboard → Auth clients → **Create Auth client**:

- **Type:** `oauth2`. **Client kind:** `Agent (third-party)` — this is what makes users see the consent screen. (`Application (first-party)` skips consent — wrong for agents.)
- **Application Token URL:** `https://<public-origin>/api/agent/token`
- **Application Revoke URL:** `https://<public-origin>/api/agent/token/revoke`
- **Application Profile URL:** required by the form but **never called in the agent flow** (it's a DCR metadata fallback). Point it at the token URL or any real route.
- **Require PKCE:** keep checked.
- **Redirect URLs: leave empty on this client** — agents register their own redirect URIs via DCR (`redirect_uris` is a required DCR field).

Copy **this client's secret** — the app verifies platform calls with it.

### 5. Console — enable Agent Readiness

Dashboard → Admin → Auth → **Agent access**:

- **Agent readiness** → ON. Publishes the org's authorization server; the app's `/auth.md` + OAuth pointers activate automatically (SDK caches the readiness bundle ~5 min; restart the app server to pick it up instantly).
- **Let agents register themselves** (DCR) → ON, and pick the OAuth2 client from step 4 as the **base client**. Self-registered agents inherit its endpoints and signing.
- **Allow agent self-signup** → only if bot accounts are wanted. Off by default.

Verify from outside: `GET <serverUrl>/api/v1/public/<orgId>/agent-readiness` must return `{"enabled":true,"authorizationServer":{…}}`.

### 6. Environment — note there are TWO client secrets

```env
NEXT_PUBLIC_SITE_URL=https://<public-origin>
SYSTEM_SECRET=<openssl rand -hex 32>              # app-owned token signing
BUILDBASE_CLIENT_SECRET=<login client secret>     # human sign-in (existing)
BUILDBASE_AGENT_CLIENT_SECRET=<base client secret> # agent bridge (step 4's client)
```

`NEXT_PUBLIC_*` values are inlined at **build time** — changing them requires `npm run build`, not just a restart. Server-only values need a restart. Code changes under `next start` always need a rebuild.

### 7. Verify (✅ after every step)

```bash
curl https://<origin>/.well-known/mcp/server-card.json     # transport.url must equal <origin>/mcp
curl https://<origin>/.well-known/oauth-protected-resource/mcp  # resource must equal <origin>/mcp
curl https://<origin>/auth.md                              # 200 once readiness is enabled
curl -X POST https://<origin>/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}' -i
# expect: 401 with WWW-Authenticate: Bearer resource_metadata="…/oauth-protected-resource/mcp"
```

Then connect a real client: `claude mcp add --transport http my-app https://<origin>/mcp` → `/mcp` → Authenticate. Login + consent should complete and tools appear.

---

## Exposing tools

### `builtinTools` — every accepted form

| Value | Result | When to use |
|---|---|---|
| `'readonly'` | 24 read tools (**default**) | First integration; reporting/analysis agents |
| `'all'` | All 42, incl. writes + destructive | Demos; full-capability starters. Surface is invisible in code — prefer an explicit list for production |
| `false` | No built-ins | Standalone server: only the app's custom tools |
| `{ include: [...] }` | Exactly the named tools | **Production.** Explicit, PR-reviewable; names are typed (`BuiltinMcpToolName`), so a typo fails `tsc` |
| `{ exclude: [...] }` | All 42 minus the named | "Everything but destructive" — but tools added by future SDK versions appear automatically; prefer `include` for a security boundary |

Recipes:

```ts
// Reporting agent — reads only
builtinTools: 'readonly',

// Support agent — reads + safe member management
builtinTools: { include: [
  'list_workspaces', 'get_workspace', 'list_workspace_users',
  'get_subscription', 'get_quota_usage',
  'invite_workspace_user', 'update_workspace_user_role',
] },

// Billing agent — subscription lifecycle without deletion
builtinTools: { include: [
  'get_subscription', 'get_plans', 'get_public_plans', 'list_invoices',
  'create_subscription_checkout', 'update_subscription',
  'resume_subscription', 'get_billing_portal_url',
] },

// Metering agent — records usage / consumes credits, nothing else
builtinTools: { include: [
  'get_quota_usage', 'get_credit_balance',
  'record_usage', 'record_usage_batch', 'consume_credits',
] },

// Product-only agent — zero Buildbase tools, only custom ones
builtinTools: false,
```

The complete catalog (42 names, from the `BuiltinMcpToolName` type):

- **Reads (24):** `list_workspaces` `get_workspace` `list_workspace_users` `get_user_profile` · `get_subscription` `get_plans` `get_plan_versions` `get_plan_version` `get_public_plans` `list_invoices` `get_invoice` · `get_quota_usage` `get_all_quota_usage` `get_usage_logs` · `get_credit_balance` `list_credit_transactions` `get_credit_packages` `get_credit_buckets` `get_expiring_credits` `get_public_credit_packages` · `check_feature_flag` `check_permission` `resolve_permissions` `get_settings`
- **Writes (14):** `create_workspace` `update_workspace` `invite_workspace_user` `update_workspace_user_role` `update_user_profile` · `record_usage` `record_usage_batch` `consume_credits` `purchase_credits` `send_notification` · `create_subscription_checkout` `update_subscription` `resume_subscription` `get_billing_portal_url`
- **Destructive (4):** `delete_workspace` `remove_workspace_user` `cancel_subscription` `update_feature_flag`

A template pattern worth recommending: write `{ include: [ …all 42, grouped by category with comments… ] }` so the whole menu is visible in code and narrowing is just deleting lines (the destructive group first).

Built-ins run under the user's session; the read/write boundary is this config, not scopes.

### Custom tools
- **Custom tools:** `defineMcpTool({ name, description, inputSchema, annotations?, requiredScopes?, execute })`. In `execute(input, ctx)`: `ctx.auth` (`sessionId`, `userId?`, `workspaceId?`, `scopes?`), `ctx.workspaceId`, `ctx.bb` (session-scoped Buildbase actions), `ctx.custom` (your `context` factory's result). Field names are `inputSchema`/`execute` — not `schema`/`handler`.
- Custom tools with the same name **override** built-ins.
- **Clients cache `tools/list` per connection.** After adding/changing tools (and rebuilding): in Claude Code run `/mcp` → the server → **Reconnect** (no re-auth needed). New sessions always fetch fresh.

Production hardening on `mcp.handler`: `rateLimit`, `allowedOrigins`, `maxRequestBytes` (default 1 MiB), `formatToolError`, `onError`.

---

## Failure library (every one observed for real)

| Symptom | Cause | Fix |
|---|---|---|
| Client error: *"Protected resource `…/mcp` does not match expected `…/api/mcp`"* | Default `mcp.path` is `/api/mcp` but the canonical resource is `<host>/mcp` | Set `mcp.path: '/mcp'` and serve the route there |
| Platform's call to `applicationTokenUrl` returns **401 `invalid_signature`**; agent auth dies after consent | App verified with the **login client's** secret; the platform signs with the **base (agent) client's** secret — self-registered agents inherit its signing | Use the base client's secret (`BUILDBASE_AGENT_CLIENT_SECRET`) in `handleAppTokenRequest`/`handleAppRevokeRequest` |
| `/auth.md` and OAuth pointers 404 while everything else works | Org's **Agent readiness** toggle is off — or it was just enabled and the SDK's ~5-min bundle cache hasn't expired | Enable in Admin → Auth → Agent access; restart the app server to skip the cache |
| Agent completes login/consent, then token exchange fails; app never receives the mint call | Token/Revoke URLs point at `localhost` — platform can't reach it and its SSRF guard blocks loopback in production | Public HTTPS origin (deploy or tunnel) in the console client's URLs |
| Changed env/code but behavior didn't change | `NEXT_PUBLIC_*` inlined at build; `next start` serves the last build | Rebuild after env or code changes; restart after server-only env changes |
| Added tools but the agent doesn't see them | MCP clients fetch `tools/list` once per connection | Reconnect the server in the client (`/mcp` → Reconnect) |
| `invite_workspace_user` → *"User with email … not found, ask them to sign up first"* | Platform rule: only existing platform users can be invited to workspaces | Invitee signs up once, then re-invite |
| Console form demands an Application Profile URL | Required field, but never called in the OAuth2 agent flow (DCR fallback only) | Point it at the token URL or a trivial authenticated route |
| Free-ngrok client mysteriously fails discovery | ngrok's browser-warning interstitial intercepts requests lacking `ngrok-skip-browser-warning` | Suspect the interstitial first; paid ngrok/deploy avoids it |

---

## Security invariants (what to tell a worried developer)

- The app's `SYSTEM_SECRET` and minted tokens never reach the platform; the platform relays tokens opaquely and can neither forge nor decode them.
- The user's Buildbase session rides inside the token as an AES-256-GCM-encrypted `sid` claim; only the app (holder of `SYSTEM_SECRET`) can decrypt it.
- Tokens are audience-bound (RFC 8707): a token minted for one resource is rejected at another.
- Agent clients are PKCE-only public clients (`token_endpoint_auth_method: "none"`); self-registered ones are marked unverified and always require user consent.
- Whatever tools are exposed, the platform enforces the acting user's real permissions — an agent cannot do what its user cannot.
