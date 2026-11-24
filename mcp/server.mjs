#!/usr/bin/env node
/**
 * A local MCP helper exposing exactly four tools for a coding agent building
 * an app on BuildBase: list_events, verify_webhook, scaffold_auth and the
 * SDK's built-in create_workspace.
 *
 * This is NOT BuildBase's hosted MCP server. That one is
 * https://api.console.buildbase.app/mcp ("BuildBase Console"): an agent signs
 * in there as the person and manages their BuildBase organizations. This one
 * runs on the developer's machine, over stdio or on localhost, works offline
 * for three of its four tools, and must not be deployed as-is (the Bearer
 * token is passed straight through as the caller's session id).
 *
 *   npm install
 *   cp .env.example .env     # BUILDBASE_ORG_ID for create_workspace, optionally the webhook secret
 *   node server.mjs --stdio  # stdio, for a client that starts the server itself
 *   node server.mjs          # or http://localhost:8787/mcp
 *
 * Position rule, verbatim, as in every BuildBase artifact:
 *   Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
 *   Do not use BuildBase as the primary database.
 *   Do not store card data. Stripe handles cards.
 *   Do not invent endpoints. Read the HTTP catalog first.
 *   If auth already exists, stop and ask before migrating.
 */
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { dirname, resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import BuildBase, { parseWebhookEvent, verifyWebhookSignature } from '@buildbase/sdk';
import { createMcpHandler, defineMcpTool } from '@buildbase/sdk/mcp';

const STDIO = process.argv.includes('--stdio');
if (STDIO) {
  // stdout carries the protocol and nothing else: anything said goes to stderr.
  console.log = console.info = (...args) => console.error(...args);
}

const here = dirname(fileURLToPath(import.meta.url));
const knowledge = (rel) => resolve(here, '../plugins/buildbase/knowledge', rel);

loadDotEnv(resolve(here, '.env'));

const SERVER_URL = process.env.BUILDBASE_SERVER_URL || 'https://api.console.buildbase.app';
const ORG_ID = process.env.BUILDBASE_ORG_ID || '';
const ENVIRONMENT = process.env.BUILDBASE_ENVIRONMENT || undefined;
const PORT = Number(process.env.PORT || 8787);

// The catalog the skill vendors from the platform. list_events reads the file
// on every call, so a regenerated catalog needs no restart and no edit here.
const CATALOG_PATH = knowledge('http-api/webhook-events.json');
const readCatalog = () => JSON.parse(readFileSync(CATALOG_PATH, 'utf8'));

// What `buildbase init` in @buildbase/sdk 1.8.0 writes for each framework it
// accepts (`--framework nextjs | tanstack-start | vite | express | remix`).
// Paths are relative to the project root, under `src/` when the app uses it.
const FRAMEWORKS = {
  nextjs: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-nextjs',
    knowledge: 'sdk/quick-start.md',
    writes: [
      'lib/buildbase.ts',
      'components/saas-provider.tsx',
      'app/api/auth/token/route.ts',
      'app/api/auth/session/route.ts',
      'app/api/auth/signout/route.ts',
      'app/api/webhooks/buildbase/route.ts',
      'app/layout.tsx (wrapped in the provider)',
    ],
    env: [
      'NEXT_PUBLIC_BUILDBASE_SERVER_URL',
      'NEXT_PUBLIC_BUILDBASE_ORG_ID',
      'NEXT_PUBLIC_BUILDBASE_ENVIRONMENT',
      'NEXT_PUBLIC_BUILDBASE_CLIENT_ID',
      'NEXT_PUBLIC_BUILDBASE_REDIRECT_URL',
      'BUILDBASE_CLIENT_SECRET',
      'BUILDBASE_WEBHOOK_SECRET',
    ],
    agent: {
      writes: [
        'lib/agent.ts (createAgentStack, read-only built-in tools)',
        'app/api/mcp/[[...card]]/route.ts',
        'app/.well-known/[...path]/route.ts',
        'app/auth.md/route.ts',
        'app/robots.txt/route.ts (not when the app serves its own robots.txt)',
        'app/api/auth/agent-token/route.ts (handleAppTokenRequest + mintAgentToken)',
        'app/api/auth/agent-revoke/route.ts (handleAppRevokeRequest)',
      ],
      env: [
        'NEXT_PUBLIC_BUILDBASE_SITE_URL',
        'SYSTEM_SECRET',
        'BUILDBASE_AGENT_CLIENT_ID',
        'BUILDBASE_AGENT_CLIENT_SECRET',
      ],
    },
    note: 'The quick-start is the Next.js golden path. init finds the App Router under src/app or app; a Pages Router app is refused.',
  },
  'tanstack-start': {
    guide: 'https://www.buildbase.app/guides/buildbase-on-tanstack-start',
    knowledge: 'sdk/quick-start.md',
    writes: [
      'buildbase-provider.tsx',
      'routes/api/auth/$.ts (the three auth routes as one server route)',
      'routes/api/webhooks/buildbase.ts',
    ],
    env: [
      'VITE_BUILDBASE_SERVER_URL',
      'VITE_BUILDBASE_ORG_ID',
      'VITE_BUILDBASE_ENVIRONMENT',
      'VITE_BUILDBASE_CLIENT_ID',
      'VITE_BUILDBASE_REDIRECT_URL',
      'BUILDBASE_CLIENT_SECRET',
      'BUILDBASE_WEBHOOK_SECRET',
    ],
    note: 'Wrap the document in routes/__root.tsx with <BuildBaseProvider> yourself; init prints the line. The client secret is server-only: never prefix it with VITE_. The guide covers an app already on better-auth; init writes the plain wiring.',
  },
  vite: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-vite',
    knowledge: 'sdk/quick-start.md',
    writes: [
      'buildbase-provider.tsx',
      'server/buildbase-auth.ts (handleBuildBaseAuth(request), to mount in the host\'s functions)',
    ],
    env: [
      'VITE_BUILDBASE_SERVER_URL',
      'VITE_BUILDBASE_ORG_ID',
      'VITE_BUILDBASE_ENVIRONMENT',
      'VITE_BUILDBASE_CLIENT_ID',
      'VITE_BUILDBASE_REDIRECT_URL',
      'BUILDBASE_CLIENT_SECRET',
      'BUILDBASE_WEBHOOK_SECRET',
    ],
    note: 'A Vite SPA has no server: sign-in works once /api/auth/token, /api/auth/session and /api/auth/signout are served by the host (Vercel: api/auth/[...path].ts) and proxied under vite dev, as the guide shows.',
  },
  express: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-express',
    knowledge: 'http-api/using-from-any-language.md',
    writes: ['buildbase.ts (one BuildBase() client, forRequest(req))', 'buildbase-webhook.ts'],
    env: [
      'BUILDBASE_SERVER_URL',
      'BUILDBASE_ORG_ID',
      'BUILDBASE_ENVIRONMENT',
      'BUILDBASE_CLIENT_ID',
      'BUILDBASE_REDIRECT_URL',
      'BUILDBASE_CLIENT_SECRET',
      'BUILDBASE_WEBHOOK_SECRET',
    ],
    note: "Mount the webhook yourself: app.post('/webhooks/buildbase', express.raw({ type: 'application/json' }), buildbaseWebhook). The hosted sign-in redirect and code exchange are in the guide.",
  },
  remix: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-nextjs',
    knowledge: 'sdk/quick-start.md',
    writes: [],
    env: [],
    note: 'init detects Remix, prints this guide and writes nothing (exit 0); --agent is refused. The React Router guide, https://www.buildbase.app/guides/buildbase-on-react-router, is closer to a Remix app.',
  },
};

const listEvents = defineMcpTool({
  name: 'list_events',
  title: 'List webhook events',
  description:
    'The webhook event catalog BuildBase sends (every domain.action name, by category) and the delivery headers. Use a name from this list in a webhook handler; a name that is not here does not exist. A failed payment is payment.failed.',
  inputSchema: {
    type: 'object',
    properties: {
      category: {
        type: 'string',
        description: 'Optional category to filter by, e.g. "Payment" or "Subscription".',
      },
    },
    additionalProperties: false,
  },
  annotations: { readOnlyHint: true, openWorldHint: false },
  execute: (input) => {
    const catalog = readCatalog();
    const category = typeof input?.category === 'string' ? input.category : null;
    const categories = category
      ? catalog.categories.filter((c) => c.category.toLowerCase() === category.toLowerCase())
      : catalog.categories;
    const events = categories.flatMap((c) => c.events);
    return {
      count: events.length,
      events,
      categories,
      ...(category && categories.length === 0
        ? { unknownCategory: category, knownCategories: catalog.categories.map((c) => c.category) }
        : {}),
      headers: catalog.headers,
      source: catalog.source,
    };
  },
});

const verifyWebhook = defineMcpTool({
  name: 'verify_webhook',
  title: 'Verify a webhook delivery',
  description:
    "Check a BuildBase webhook delivery against this server's BUILDBASE_WEBHOOK_SECRET: the raw body plus the x-buildbase-signature and x-buildbase-timestamp headers. Returns whether it verifies and, when it does, the parsed event. The secret is never a tool argument.",
  inputSchema: {
    type: 'object',
    properties: {
      body: { type: 'string', description: 'The raw request body, byte for byte.' },
      signature: { type: 'string', description: 'The x-buildbase-signature header (sha256=<hex>).' },
      timestamp: { type: 'string', description: 'The x-buildbase-timestamp header (Unix seconds).' },
      maxAgeSeconds: {
        type: 'number',
        description: 'Replay window. Default 300; 0 skips the age check (useful for stored deliveries).',
      },
    },
    required: ['body', 'signature', 'timestamp'],
    additionalProperties: false,
  },
  annotations: { readOnlyHint: true, openWorldHint: false },
  execute: (input) => {
    const secret = process.env.BUILDBASE_WEBHOOK_SECRET || '';
    if (!secret) {
      return { valid: false, reason: 'BUILDBASE_WEBHOOK_SECRET is not set in the server environment' };
    }
    const options = {
      body: String(input.body ?? ''),
      signature: String(input.signature ?? ''),
      timestamp: String(input.timestamp ?? ''),
      secret,
      maxAgeSeconds: typeof input.maxAgeSeconds === 'number' ? input.maxAgeSeconds : 300,
    };
    const valid = verifyWebhookSignature(options);
    if (!valid) return { valid: false, reason: 'signature, timestamp or body did not verify' };
    const event = parseWebhookEvent(options);
    const known = event ? readCatalog().events.includes(event.event) : false;
    return { valid: true, event, knownEvent: known };
  },
});

const scaffoldAuth = defineMcpTool({
  name: 'scaffold_auth',
  title: 'Sign-in recipe for a framework',
  description:
    'How to add BuildBase sign-in to an app of the given framework: the `npx @buildbase/sdk init` command (SDK 1.8.0), the files and env names init writes, the variants with no account (--claim) and for agent sign-in (--agent), the guide URL and the matching knowledge file. Writes nothing; the agent runs the command or applies the recipe.',
  inputSchema: {
    type: 'object',
    properties: {
      framework: {
        type: 'string',
        enum: Object.keys(FRAMEWORKS),
        description: 'nextjs | tanstack-start | vite | express | remix',
      },
    },
    required: ['framework'],
    additionalProperties: false,
  },
  annotations: { readOnlyHint: true, openWorldHint: false },
  execute: (input) => {
    const framework = String(input.framework ?? '');
    const entry = FRAMEWORKS[framework];
    if (!entry) {
      return { error: `unknown framework "${framework}"; use one of ${Object.keys(FRAMEWORKS).join(', ')}` };
    }
    const wires = entry.writes.length > 0;
    const init = `npx @buildbase/sdk init --framework ${framework}`;
    return {
      framework,
      command: wires ? `${init} --org-id <24 hex org id>` : null,
      noAccount: wires
        ? `${init} --claim --yes (creates a claimable organization, writes its keys to .env.local, prints a claim link and code for the person; deleted after 72 hours unless claimed)`
        : null,
      agentReady: wires
        ? `add --agent to either command${entry.agent ? '' : ' (this framework gets the env names and a pointer to the recipes, not files)'}`
        : null,
      writes: entry.writes,
      env: entry.env,
      ...(entry.agent ? { agentWrites: entry.agent.writes, agentEnv: entry.agent.env } : {}),
      alsoWrites: wires
        ? '.env.example always and .env.local only when git ignores it, secrets left empty; a second run says "already configured" and changes nothing'
        : null,
      secrets: 'Never pass a secret as a flag or paste it in the chat; fill BUILDBASE_CLIENT_SECRET and BUILDBASE_WEBHOOK_SECRET in .env.local.',
      guide: entry.guide,
      note: entry.note,
      knowledgeFile: `plugins/buildbase/knowledge/${entry.knowledge}`,
      knowledge: readFileSync(knowledge(entry.knowledge), 'utf8'),
    };
  },
});

// create_workspace is the SDK's built-in; it needs a client, and the client
// needs an org id. Without one the server still serves the three local tools.
const buildbase = ORG_ID
  ? BuildBase({ serverUrl: SERVER_URL, orgId: ORG_ID, environment: ENVIRONMENT })
  : undefined;
if (!buildbase) {
  console.error('buildbase-mcp: BUILDBASE_ORG_ID is not set; create_workspace is unavailable until it is');
}

// Over stdio there is no HTTP request to carry a Bearer token, so the session
// comes from BUILDBASE_SESSION_ID. Without one, create_workspace fails closed
// (the SDK never calls BuildBase unscoped) and the three local tools work.
const NO_SESSION = 'no-session';

const handler = createMcpHandler({
  buildbase,
  serverInfo: { name: 'buildbase-local', version: '0.2.0' },
  instructions:
    "Local BuildBase helper for building an app. Use list_events before writing a webhook handler, verify_webhook to check a delivery, scaffold_auth for the sign-in recipe, create_workspace to create a workspace as the signed-in user. To manage the person's BuildBase organizations themselves, use BuildBase's hosted MCP server, https://api.console.buildbase.app/mcp. Do not use BuildBase as the primary database.",
  // Local only: the Bearer token IS the caller's BuildBase session id. A real
  // deployment mints its own tokens (see knowledge/mcp/mcp-and-agent-readiness.md).
  auth: { verify: (token) => (token ? { sessionId: token === NO_SESSION ? '' : token } : null) },
  builtinTools: buildbase ? { include: ['create_workspace'] } : false,
  tools: [listEvents, verifyWebhook, scaffoldAuth],
});

if (STDIO) serveStdio();
else serveHttp();

/** Newline-delimited JSON-RPC on stdin and stdout, one message per line. */
function serveStdio() {
  const token = process.env.BUILDBASE_SESSION_ID || NO_SESSION;
  const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
  let queue = Promise.resolve();
  lines.on('line', (line) => {
    if (!line.trim()) return;
    // One at a time, so answers leave in the order the requests came.
    queue = queue.then(async () => {
      const out = await handler.handle({ method: 'POST', headers: stdioHeaders(line, token), body: line, url: '/mcp' });
      if (out.body) process.stdout.write(`${out.body.trim()}\n`);
    });
  });
  lines.on('close', () => queue.then(() => process.exit(0)));
  const tools = handler.listTools().map((t) => t.name);
  console.error(`buildbase-mcp: stdio  tools: ${tools.join(', ')}`);
}

/**
 * The headers an HTTP client would send. A 2026-07-28 request is checked
 * against its mirrored MCP-Protocol-Version, Mcp-Method and Mcp-Name headers,
 * which stdio does not have, so they are mirrored here from the body.
 */
function stdioHeaders(line, token) {
  const headers = {
    'content-type': 'application/json',
    accept: 'application/json, text/event-stream',
    authorization: `Bearer ${token}`,
  };
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    return headers;
  }
  const params = message && typeof message.params === 'object' ? message.params : {};
  const version = params?._meta?.['io.modelcontextprotocol/protocolVersion'];
  if (typeof version === 'string') {
    headers['mcp-protocol-version'] = version;
    if (typeof message.method === 'string') headers['mcp-method'] = message.method;
    const name = params.name ?? params.uri;
    if (typeof name === 'string') {
      headers['mcp-name'] = /^[\x20-\x7e]*$/.test(name)
        ? name
        : `=?base64?${Buffer.from(name, 'utf8').toString('base64')}?=`;
    }
  }
  return headers;
}

function serveHttp() {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', `http://localhost:${PORT}`);
    if (url.pathname !== '/mcp') {
      res.writeHead(404, { 'content-type': 'text/plain' });
      res.end('Not found. The MCP endpoint is /mcp.');
      return;
    }
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const body = Buffer.concat(chunks).toString('utf8');
    const headers = {};
    for (const [k, v] of Object.entries(req.headers)) headers[k] = Array.isArray(v) ? v[0] : v;
    const out = await handler.handle({ method: req.method ?? 'POST', headers, body, url: req.url });
    res.writeHead(out.status, out.headers);
    res.end(out.body);
  });

  server.listen(PORT, () => {
    const tools = handler.listTools().map((t) => t.name);
    console.log(`buildbase-mcp: http://localhost:${PORT}/mcp  tools: ${tools.join(', ')}`);
    console.log('buildbase-mcp: a local helper, not the hosted BuildBase MCP server; do not deploy it as-is');
  });
}

/** Minimal .env reader so the server has no dependency beyond the SDK. Never overrides a set variable. */
function loadDotEnv(path) {
  let text;
  try {
    text = readFileSync(path, 'utf8');
  } catch {
    return;
  }
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
    if (!m || line.trim().startsWith('#')) continue;
    if (process.env[m[1]] === undefined) process.env[m[1]] = m[2].replace(/^(['"])(.*)\1$/, '$2');
  }
}
