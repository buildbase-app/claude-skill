# BuildBase sessions and Supabase RLS

Short answer: **not supported today**, and the gap is on the BuildBase side. This file records exactly why, and the smallest change an app can make now.

Position rule:

```text
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

## What Supabase needs

Supabase third-party auth (https://supabase.com/docs/guides/auth/third-party/overview) accepts another provider's tokens when that provider is an OIDC-style issuer: the token is a JWT, and Supabase can fetch the issuer's public keys from a JWKS URL to verify it. Row Level Security then reads `auth.uid()` and `auth.jwt()` from that verified token.

## What BuildBase has

- A BuildBase **session is an opaque id**, not a JWT: a 35-character random string stored in Redis, sent as the `x-session-id` header (`os/server/src/routes/v1/auth/constants.ts`, `SESSION_ID_LENGTH = 35`). There are no claims in it to read.
- The platform's own JWTs (used internally and for org tokens) are **HS256**, signed with a server secret (`packages/server-core/src/utils/jwt.ts`). There is no asymmetric key pair and **no JWKS endpoint**: `server/src/routes/wellKnown/index.ts` serves OAuth metadata, but no `jwks_uri`.

So there is no BuildBase token Supabase could verify on its own. Do not claim otherwise, and do not invent a claim.

## The smallest change today (app-side)

Mint the Supabase token yourself, in your own server route, after BuildBase has vouched for the user.

1. The browser calls your route with its BuildBase session (`x-session-id` header, or the `bb-session-id` cookie your app set).
2. Your route validates the session by calling BuildBase: `GET {serverUrl}/api/v1/public/profile` with headers `x-session-id: <session>` and `x-org-id` as the SDK sends them, or through the server SDK: `BuildBase({ serverUrl, orgId }).withSession(sessionId).users.getProfile()`. A `401` means the session is invalid; stop there.
3. Your route signs a **Supabase-shaped JWT** with your Supabase project's JWT secret (HS256, the legacy shared secret Supabase documents at https://supabase.com/docs/guides/auth/jwts). Claims are Supabase's own, not BuildBase's:
   - `sub`: the BuildBase user id from the profile
   - `role`: `"authenticated"`
   - `aud`: `"authenticated"`
   - `exp`: no later than the BuildBase session's remaining lifetime; keep it short (minutes) and let the client refresh by calling the route again
   - optionally `email` from the profile, and app-specific values under a namespaced claim your policies read with `auth.jwt()`
4. The client creates its Supabase client with that JWT as the bearer (`global.headers.Authorization = 'Bearer <jwt>'`, or `accessToken: async () => fetchFromYourRoute()` in `createClient`). RLS policies use `auth.uid()`, which is the `sub` above, and you store that same BuildBase user id in your tables' owner columns.

What this gives you: Supabase stays the database, BuildBase stays the identity, and no BuildBase secret or session ever reaches the Supabase client. What it costs: one route of yours, one secret of yours (the Supabase JWT secret) kept server-side, and tokens that must be refreshed on your schedule.

What it does not give you: Supabase's own session management, refresh tokens or `supabase.auth.getUser()`. Those read Supabase Auth's user table, which your users are not in.

## The platform change that would close the gap (not built)

BuildBase would need to issue **RS256 (or ES256) user JWTs** alongside the opaque session, publish the public keys at `/.well-known/jwks.json`, and advertise `jwks_uri` in its OAuth metadata. Supabase third-party auth could then be configured with BuildBase as the issuer and no app-side minting would be needed. This is recorded as a gap in `notes/AGENT_DISTRIBUTION_PLAN.md` in the platform repo. Until it ships, the recipe above is the supported path.
