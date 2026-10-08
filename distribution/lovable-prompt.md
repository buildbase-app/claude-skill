# Lovable paste prompt

Paste this into a Lovable project that already runs on Supabase. The first block is the prompt; the second is the position rule every BuildBase artifact repeats, so the agent reading it knows when BuildBase is the wrong tool.

```text
Keep Supabase as the database. Add BuildBase as the SaaS layer:
auth, workspaces, Stripe billing, and lifecycle email.
Package: @buildbase/sdk. Docs: https://www.buildbase.app/llms.txt
Hosted sign-in on our domain. Do not add Clerk, Auth0, Resend, or n8n.
Ask me for the BuildBase publishable key before writing env files.
```

```text
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

## What the agent will actually ask you for

BuildBase has no publishable key. The prompt keeps the author's wording; what the app needs is:

| Value | Where it comes from | Env name (Vite) |
|---|---|---|
| Server URL | `https://api.console.buildbase.app` for cloud, your tenant server for self-hosted | `VITE_BUILDBASE_SERVER_URL` |
| Organization id | Console, 24 hex characters | `VITE_BUILDBASE_ORG_ID` |
| OAuth client id | Console, Authentication, your app's client | `VITE_BUILDBASE_CLIENT_ID` |
| Redirect URL | Your app's callback route | `VITE_BUILDBASE_REDIRECT_URL` |
| OAuth client secret | Console, shown once | `BUILDBASE_CLIENT_SECRET`, server-side only, never `VITE_` |
| Webhook signing secret | Console, Webhooks | `BUILDBASE_WEBHOOK_SECRET`, server-side only |

None of these are safe to paste into chat except the server URL and the organization id. The two secrets go into Lovable's secret store, not into a file the agent writes.

The Vite guide the agent should follow: https://www.buildbase.app/guides/buildbase-on-vite
