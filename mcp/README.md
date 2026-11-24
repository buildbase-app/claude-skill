# BuildBase MCP helper (local, in-repo)

There are two different MCP servers around BuildBase. Pick the one for the job:

| | BuildBase's hosted MCP server | This folder |
|---|---|---|
| What it is for | Managing the person's BuildBase organizations: console reads and writes, blueprints, docs search, `get_api_operation`, env templates, claim links | Building an app on BuildBase: the webhook catalog, checking a delivery, the sign-in recipe, creating a workspace |
| Where it runs | `https://api.console.buildbase.app/mcp` ("BuildBase Console"), Streamable HTTP | On your machine: stdio, or `http://localhost:8787/mcp` |
| Sign-in | OAuth, as the person, with their role in each organization | None of its own (see [Auth](#auth)) |
| Tools | 20 | 4 |
| Set up | `npx @buildbase/sdk agent setup --console`, or the per-client guides in [buildbase-app/mcp](https://github.com/buildbase-app/mcp) | `npm install` here, then `node server.mjs --stdio` |

Use the hosted server whenever the agent can reach the internet and the person can sign in. This folder is a separate local helper with four distribution tools, kept for clients that want offline help while writing code: three of the four tools need no network at all. It is not deployed and must not be presented as a hosted service. Neither of them is an app's own MCP server; making the person's app agent-ready is `@buildbase/sdk/mcp` (`createAgentStack`), in [`../plugins/buildbase/knowledge/mcp/mcp-and-agent-readiness.md`](../plugins/buildbase/knowledge/mcp/mcp-and-agent-readiness.md).

Position rule, as in every BuildBase artifact:

```text
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

## What about `nextjs-agent-mcp-starter`?

[buildbase-app/nextjs-agent-mcp-starter](https://github.com/buildbase-app/nextjs-agent-mcp-starter) is a **template app you deploy yourself**: its README ends with `claude mcp add --transport http my-app https://<your-public-origin>/mcp`, where the origin is yours. It is an example of an app's own MCP server, serving the SDK's built-in tools to that product's users. The server here is the opposite: four tools for a developer wiring BuildBase into an app.

## The four tools

| Tool | What it does | Source of truth |
|---|---|---|
| `list_events` | Every webhook event name by category, plus the delivery headers. Optional `category` filter. | `../plugins/buildbase/knowledge/http-api/webhook-events.json`, read on every call, so it returns whatever that file holds |
| `verify_webhook` | Verifies a delivery (`body`, `signature`, `timestamp`) against `BUILDBASE_WEBHOOK_SECRET` from the server's environment and returns the parsed event, with its `id`. The secret is never a tool argument. | `verifyWebhookSignature` and `parseWebhookEvent` from `@buildbase/sdk` |
| `scaffold_auth` | For `nextjs`, `tanstack-start`, `vite`, `express` or `remix`: the `npx @buildbase/sdk init` command, the files and env names init writes in SDK 1.8.0, the `--claim` and `--agent` variants, the guide URL and the matching knowledge file. Writes nothing. | `buildbase init` in `@buildbase/sdk` 1.8.0, and the knowledge files in this repo |
| `create_workspace` | The SDK's built-in, run as the signed-in user. Needs `BUILDBASE_ORG_ID` and a session. | `@buildbase/sdk/mcp` built-ins |

Nothing else is exposed: `builtinTools` is an explicit `{ include: ['create_workspace'] }`. Without `BUILDBASE_ORG_ID` the server starts with three tools and says so on stderr.

## Run it

Pinned to `@buildbase/sdk` `^1.8.0`.

```bash
cd mcp
npm install
cp .env.example .env     # BUILDBASE_ORG_ID for create_workspace; BUILDBASE_WEBHOOK_SECRET for verify_webhook
node server.mjs --stdio  # stdio: the client starts the server and talks on stdin and stdout
node server.mjs          # or HTTP: http://localhost:8787/mcp
```

Connect Claude Code over stdio (the client starts the server itself):

```bash
claude mcp add buildbase-local -- node /absolute/path/to/mcp/server.mjs --stdio
```

Or over HTTP, with the Bearer token the server expects:

```bash
claude mcp add --transport http buildbase-local http://localhost:8787/mcp --header "Authorization: Bearer <session id>"
```

## Auth

Auth is local-only. Over HTTP the Bearer token is passed through as the caller's BuildBase session id, so `create_workspace` runs as whoever's session you hand it, and a request with no Bearer token gets 401. Over stdio the session comes from `BUILDBASE_SESSION_ID`; without it `create_workspace` refuses ("This tool needs an authenticated BuildBase session") and the other three tools work. A real deployment mints its own tokens; `../plugins/buildbase/knowledge/mcp/mcp-and-agent-readiness.md` is that recipe.

## Protocol revision

The server speaks what `@buildbase/sdk` 1.8.0's handler speaks: MCP **2026-07-28** for a request that carries the per-request `_meta`, and **2025-11-25** for a client that starts with `initialize`, negotiating down to 2024-11-05. Over stdio the server mirrors the `MCP-Protocol-Version`, `Mcp-Method` and `Mcp-Name` headers a 2026-07-28 request is checked against from the message itself, since stdio has no headers.

## Check it by hand

Over stdio, one request per line:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | node server.mjs --stdio | tail -n 1 | node -e 'process.stdin.on("data",d=>console.log(JSON.parse(d).result.tools.map(t=>t.name)))'
```

Over HTTP:

```bash
curl -s localhost:8787/mcp -H 'content-type: application/json' -H 'authorization: Bearer test' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node -e 'process.stdin.on("data",d=>console.log(JSON.parse(d).result.tools.map(t=>t.name)))'
```

Both print `[ 'create_workspace', 'list_events', 'verify_webhook', 'scaffold_auth' ]` (or the last three without an org id).

## Why no `.well-known/mcp.json` here

That document announces a public MCP URL, and this server has none: it runs on the developer's machine. The hosted server publishes its own discovery documents, including its MCP Server Card at `https://api.console.buildbase.app/.well-known/mcp/server-card.json`.
