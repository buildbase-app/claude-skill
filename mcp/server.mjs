#!/usr/bin/env node
/**
 * A local MCP server exposing exactly four tools for coding agents working
 * with BuildBase: list_events, verify_webhook, scaffold_auth and the SDK's
 * built-in create_workspace. Hosting is not done: there is no public URL,
 * no `.well-known/mcp.json`, and nothing here should be deployed as-is (the
 * Bearer token is passed straight through as the caller's session id).
 *
 *   npm install
 *   cp .env.example .env   # fill in BUILDBASE_ORG_ID, optionally the webhook secret
 *   node server.mjs        # http://localhost:8787/mcp
 *   claude mcp add --transport http buildbase http://localhost:8787/mcp
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
import { fileURLToPath } from 'node:url';
import BuildBase, { parseWebhookEvent, verifyWebhookSignature } from '@buildbase/sdk';
import { createMcpHandler, defineMcpTool } from '@buildbase/sdk/mcp';

const here = dirname(fileURLToPath(import.meta.url));
const knowledge = (rel) => resolve(here, '../plugins/buildbase/knowledge', rel);

loadDotEnv(resolve(here, '.env'));

const SERVER_URL = process.env.BUILDBASE_SERVER_URL || 'https://api.console.buildbase.app';
const ORG_ID = process.env.BUILDBASE_ORG_ID || '';
const PORT = Number(process.env.PORT || 8787);

// The catalog the skill vendors from the platform. list_events reads the file
// on every call so a refreshed catalog needs no restart.
const CATALOG_PATH = knowledge('http-api/webhook-events.json');
const readCatalog = () => JSON.parse(readFileSync(CATALOG_PATH, 'utf8'));

const FRAMEWORKS = {
  nextjs: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-nextjs',
    knowledge: 'sdk/quick-start.md',
    note: 'The quick-start is the Next.js golden path: provider, three auth routes, webhook route.',
  },
  vite: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-vite',
    knowledge: 'sdk/quick-start.md',
    note: 'Same provider and callbacks as the quick-start, with VITE_ env names and the three auth handlers as a dev-server plugin or serverless functions (see the guide).',
  },
  express: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-express',
    knowledge: 'http-api/using-from-any-language.md',
    note: 'Server-only: one BuildBase() client, withSession() per request, the hosted sign-in redirect and code exchange from the guide.',
  },
  remix: {
    guide: 'https://www.buildbase.app/guides/buildbase-on-nextjs',
    knowledge: 'sdk/quick-start.md',
    note: 'Not scaffolded by `buildbase init` yet; the epic-stack example in buildbase-app/examples is the React Router reference.',
  },
};

const listEvents = defineMcpTool({
  name: 'list_events',
  description:
    'The webhook event catalog BuildBase sends (112 domain.action names, by category) and the three delivery headers. Use a name from this list in a webhook handler; a name that is not here does not exist. A failed payment is payment.failed.',
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
  annotations: { readOnlyHint: true },
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
      headers: catalog.headers,
      source: catalog.source,
    };
  },
});

const verifyWebhook = defineMcpTool({
  name: 'verify_webhook',
  description:
    'Check a BuildBase webhook delivery against this server\'s BUILDBASE_WEBHOOK_SECRET: the raw body plus the x-buildbase-signature and x-buildbase-timestamp headers. Returns whether it verifies and, when it does, the parsed event. The secret is never a tool argument.',
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
  annotations: { readOnlyHint: true },
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
  description:
    'How to add BuildBase sign-in to an app of the given framework: the command to run (npx buildbase init --framework <name>, SDK 0.0.79+), the guide URL and the matching knowledge file. Writes nothing; the agent applies it.',
  inputSchema: {
    type: 'object',
    properties: {
      framework: {
        type: 'string',
        enum: Object.keys(FRAMEWORKS),
        description: 'nextjs | vite | express | remix',
      },
    },
    required: ['framework'],
    additionalProperties: false,
  },
  annotations: { readOnlyHint: true },
  execute: (input) => {
    const framework = String(input.framework ?? '');
    const entry = FRAMEWORKS[framework];
    if (!entry) {
      return { error: `unknown framework "${framework}"; use one of ${Object.keys(FRAMEWORKS).join(', ')}` };
    }
    return {
      framework,
      command: `npm install @buildbase/sdk && npx buildbase init --framework ${framework} --org-id <24 hex org id>`,
      guide: entry.guide,
      note: entry.note,
      knowledgeFile: `plugins/buildbase/knowledge/${entry.knowledge}`,
      knowledge: readFileSync(knowledge(entry.knowledge), 'utf8'),
    };
  },
});

// create_workspace is the SDK's built-in; it needs a client, and the client
// needs an org id. Without one the server still serves the three local tools.
const buildbase = ORG_ID ? BuildBase({ serverUrl: SERVER_URL, orgId: ORG_ID }) : undefined;
if (!buildbase) {
  console.error('buildbase-mcp: BUILDBASE_ORG_ID is not set; create_workspace is unavailable until it is');
}

const handler = createMcpHandler({
  buildbase,
  serverInfo: { name: 'buildbase-local', version: '0.1.0' },
  instructions:
    'Local BuildBase MCP server. Use list_events before writing a webhook handler, verify_webhook to check a delivery, scaffold_auth for the sign-in recipe, create_workspace to create a workspace as the signed-in user. Do not use BuildBase as the primary database.',
  // Local only: the Bearer token IS the caller's BuildBase session id. A real
  // deployment mints its own tokens (see knowledge/mcp/mcp-and-agent-readiness.md).
  auth: { verify: (token) => (token ? { sessionId: token } : null) },
  builtinTools: buildbase ? { include: ['create_workspace'] } : false,
  tools: [listEvents, verifyWebhook, scaffoldAuth],
});

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
  const out = await handler.handle({ method: req.method ?? 'POST', headers, body });
  res.writeHead(out.status, out.headers);
  res.end(out.body);
});

server.listen(PORT, () => {
  const tools = handler.listTools().map((t) => t.name);
  console.log(`buildbase-mcp: http://localhost:${PORT}/mcp  tools: ${tools.join(', ')}`);
  console.log('buildbase-mcp: hosting not done; this server is for local use only');
});

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
