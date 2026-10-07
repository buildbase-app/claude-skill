# Partnership material

**Prepare only. Do not send.** Nothing in this repo sends email, opens a conversation or posts publicly. This file collects what each conversation needs so that, when the owner decides to start one, the facts are already checked.

Position rule, which every piece of material repeats:

```text
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

## Lovable (custom connector)

| Item | Value |
|---|---|
| Base URL | `https://api.console.buildbase.app` |
| Auth method | Header `Authorization: <orgId>:<secret>`; `Bearer` prefix tolerated |
| Test request | `GET /health`, unauthenticated, returns `OK`. For a token check, `GET /api/tokens` |
| Knowledge file | `distribution/lovable-connector-knowledge.md` (under 50,000 characters, no credentials) |
| Paste prompt | `distribution/lovable-prompt.md` |
| Eval prompt for their side | "add subscriptions and a failed-payment email" on a Supabase project with the connector installed; pass when `@buildbase/sdk` is installed, Supabase is kept, the webhook handler names `payment.failed`, and the project builds |

What to say plainly: there is no publishable key and no `GET /v1/me`; the credential is an org token and the health route is `/health`.

## Supabase

Lead with the gap, not a recipe we do not have: BuildBase sessions are opaque ids, the platform signs HS256 only, and there is no JWKS endpoint, so Supabase third-party auth cannot verify a BuildBase token today. The supported path is app-side minting of a Supabase-shaped JWT after validating the session, written up in `distribution/supabase-jwt.md`. The platform change that would make BuildBase a third-party auth provider (asymmetric user JWTs plus `/.well-known/jwks.json`) is recorded as not built.

## Bolt

| Item | Value |
|---|---|
| Paste prompt | `distribution/bolt-v0-prompt.md` |
| Template repo (Vite) | https://github.com/buildbase-app/examples/tree/main/admin-dashboard |
| Guide | https://www.buildbase.app/guides/buildbase-on-vite |

## v0

| Item | Value |
|---|---|
| Golden path (Next.js) | https://github.com/buildbase-app/examples/tree/main/with-buildbase, then https://www.buildbase.app/guides/buildbase-on-nextjs |
| Full starter | https://github.com/buildbase-app/nextjs-starter |
| Paste prompt | `distribution/bolt-v0-prompt.md` with the guide link swapped to the Next.js guide |

## Replit

**Do not contact yet.** The condition is that the HTTP catalog in this skill matches the published SDK and the webhook catalog is vendored and checked. Both land in W2 of the distribution plan (`plugins/buildbase/knowledge/http-api/webhook-events.json`, `scripts/validate.py` catalog check, SDK pin 0.0.78). Once those are merged to `main`, this section can be filled in.
