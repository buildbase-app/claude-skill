# BuildBase MCP server (local, in-repo)

**Hosting not done.** There is no public MCP hostname, no public MCP URL and no `/.well-known/mcp.json` anywhere on buildbase.app. This directory ships the server in the repo so an agent can run it locally; it is not deployed and must not be presented as a hosted service.

Position rule, as in every BuildBase artifact:

```text
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

## What about `nextjs-agent-mcp-starter`?

[buildbase-app/nextjs-agent-mcp-starter](https://github.com/buildbase-app/nextjs-agent-mcp-starter) is a **template app you deploy yourself**, not a hosted server: its README ends with `claude mcp add --transport http my-app https://<your-public-origin>/mcp`, where the origin is yours. It exposes the SDK's full built-in tool set for a product's own users. The server here is the opposite: four tools for a developer wiring BuildBase into an app.

## The four tools

| Tool | What it does | Source of truth |
|---|---|---|
| `list_events` | The 112 webhook event names by category, plus the three delivery headers. Optional `category` filter. | `../plugins/buildbase/knowledge/http-api/webhook-events.json`, read on every call |
| `verify_webhook` | Verifies a delivery (`body`, `signature`, `timestamp`) against `BUILDBASE_WEBHOOK_SECRET` from the server's environment and returns the parsed event. The secret is never a tool argument. | `verifyWebhookSignature` and `parseWebhookEvent` from `@buildbase/sdk` |
| `scaffold_auth` | For `nextjs`, `vite`, `express` or `remix`: the `npx buildbase init` command, the guide URL and the matching knowledge file. Writes nothing. | The knowledge files in this repo |
| `create_workspace` | The SDK's built-in, run as the signed-in user. Needs `BUILDBASE_ORG_ID`. | `@buildbase/sdk/mcp` built-ins |

Nothing else is exposed: `builtinTools` is an explicit `{ include: ['create_workspace'] }`.

## Run it

```bash
cd mcp
npm install
cp .env.example .env     # BUILDBASE_ORG_ID for create_workspace; BUILDBASE_WEBHOOK_SECRET for verify_webhook
node server.mjs          # http://localhost:8787/mcp
```

Connect Claude Code:

```bash
claude mcp add --transport http buildbase http://localhost:8787/mcp
```

Auth is local-only: the Bearer token is passed through as the caller's BuildBase session id, so `create_workspace` runs as whoever's session you hand it. A real deployment mints its own tokens; `../plugins/buildbase/knowledge/mcp/mcp-and-agent-readiness.md` is that recipe.

Without `BUILDBASE_ORG_ID` the server starts with three tools and says so.

## Check it by hand

```bash
curl -s localhost:8787/mcp -H 'content-type: application/json' -H 'authorization: Bearer test' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node -e 'process.stdin.on("data",d=>console.log(JSON.parse(d).result.tools.map(t=>t.name)))'
```

prints `[ 'create_workspace', 'list_events', 'verify_webhook', 'scaffold_auth' ]` (or three names without an org id).

## Why no `.well-known/mcp.json`

That document announces a public MCP URL. Publishing one for a server nobody hosts would send every agent that reads it to a dead endpoint. When a hosted server exists, the document is three lines; until then its absence is the honest state and `scripts/validate.py` rejects any mention of a hosted MCP hostname.
