# Decision Trees: Which Feature to Use?

Four decision trees for the most common "what should I use?" questions. Read them like a conversation - they're meant to guide you through the reasoning, not just give you an answer.

## Contents

- [Tree 1: What Do I Use to Restrict Content?](#tree-1-what-do-i-use-to-restrict-content) - pick the right gate
- [Tree 2: Do I Record a User Action on the Client or the Server?](#tree-2-do-i-record-a-user-action-on-the-client-or-the-server) - where to record usage
- [Tree 3: Credits or Quotas?](#tree-3-credits-or-quotas) - choose the billing model
- [Tree 4: Personal Mode or Platform Mode?](#tree-4-personal-mode-or-platform-mode) - choose the workspace mode

---

## Tree 1: What Do I Use to Restrict Content?

You want to show or hide something based on the user's state. Start here and follow the branches.

**Ask yourself: Is the user signed in?**

- If the question is "is this user authenticated at all?" → use auth gates
  - Show only to signed-in users: `<WhenAuthenticated>`
  - Show only to signed-out users: `<WhenUnauthenticated>`
  - Check programmatically: `useSaaSAuth().isAuthenticated`
  - Stop here. You don't need billing or feature gates for a basic auth check.

- If the user is signed in, continue.

**Ask yourself: Does access depend on what they've paid for?**

- If yes, continue to billing.
- If no, skip to feature flags.

**Billing: Is it a capability the plan (or an add-on) includes?**

- This is the usual case, and the entitlement gates are the right tool: they answer by slug from the server's composed entitlement (plan, add-ons and overrides), so moving a feature between plans or selling it as an add-on needs no code change.
  - A feature: `<WhenEntitled slug="advanced-analytics" fallbackComponent={<UpgradeCard />}>`, or `useEntitlement('advanced-analytics').allowed`
  - The upsell side: `<WhenNotEntitled slug="advanced-analytics">`
  - A ceiling such as "max projects": `<WhenWithinLimit slug="max-projects" current={projects.length}>` / `<WhenLimitReached ...>`, or `useLimit('max-projects', { current })`
  - The person's own plan rather than the workspace's: `<WhenUserEntitled slug="api-keys">`, or `useEntitlement(slug, { subject: { user: true } })`
  - Remember: these fail open. Nothing locks while loading, and a slug the plan does not mention is `unknown` and renders as entitled unless `whileUnknown="deny"` or `strictAbsent`. Enforce on the server too.

**Billing: Does it depend on whether they have any active subscription?**

- Yes, show only to subscribers: `<WhenSubscription>`
- Yes, show only to non-subscribers (free users): `<WhenNoSubscription>`
- These count a **live** subscription by default (`active`, `trialing` until the trial ends, `past_due` while Stripe retries). For a screen a lapsed customer still needs, such as fixing the card, pass `status="any"`.
- No, you want a specific plan. Continue.

**Billing: Does it depend on which specific plan they're on?**

- Yes, one or more plans: `<WhenSubscriptionToPlans plans={['pro', 'enterprise']}>` (plan slugs, matched case-insensitively). Use it for "which plan is this" display; gate capabilities with the entitlement gates above.
- Yes, you want to exclude a specific plan: use `useSubscriptionContext()` and check `response?.plan?.slug !== 'free'` directly
- No, continue.

**Billing: Does it depend on trial state?**

- User is in a trial: `<WhenTrialing>`
- Trial is ending soon: `<WhenTrialEnding daysThreshold={7}>` (default 3 days, or `ui.behavior.trialEndingDays`)
- Trial has ended (no longer trialing and no active plan): combine `<WhenNotTrialing>` with `<WhenNoSubscription>`, or check `useTrialStatus()`. (There is no `WhenTrialEnded` component.)
- Continue if not trial-related.

**Ask yourself: Does access depend on a specific feature being enabled for the workspace?**

- This is about workspace-level feature flags (set per workspace or per plan):
  - Gate content: `<WhenWorkspaceFeatureEnabled slug="your-feature">`
  - Check programmatically: read the workspace's feature map, `useSaaSWorkspaces().currentWorkspace?.features?.['your-feature']` (`features` is a `Record<string, boolean>`, so index it; it has no `.includes()`). `useUserFeatures()` is the per-user map, not this one.
  - Remember: the feature must exist in the dashboard AND be on the workspace's plan first. For a feature sold on a plan, `WhenEntitled` reads the same answer with the plan's provenance.

**Ask yourself: Does access depend on individual user-level features?**

- This is for features toggled per-user (beta access, personal experiments):
  - `<WhenUserFeatureEnabled slug="beta-access">`
  - `useUserFeatures().isFeatureEnabled('beta-access')`

**Ask yourself: Does access depend on how much the user has used?**

- This is quota-based: they have a monthly limit and might have used it up.
  - They have remaining quota: `<WhenQuotaAvailable slug="api_calls">`
  - They're approaching the limit: `<WhenQuotaThreshold slug="api_calls" threshold={80}>` (80% consumed)
  - They're at the limit: `<WhenQuotaExhausted slug="api_calls">`

**Ask yourself: Does access require prepaid credits?**

- This is for consumable units users purchase (AI tokens, generation credits):
  - They have enough credits: `<WhenCreditsAvailable min={5}>`
  - They're running low: `<WhenCreditsLow threshold={20}>`
  - They've run out: `<WhenCreditsExhausted>`

**Ask yourself: Does access depend on their role within the workspace?**

- This is role-based access control (RBAC):
  - Global user roles (admin/user across the platform): `<WhenRoles roles={['admin']}>`
  - Workspace-specific roles (`admin`, `editor`, `viewer` built in, plus any the org adds): `<WhenWorkspaceRoles roles={['admin', 'editor']}>`. No member's role is ever `owner`; for "is this the workspace's creator?" use `usePermissions().isOwner`.
  - Prefer workspace roles for most access control - they're more granular.

**Ask yourself: Does access depend on a custom permission?**

- You've defined custom permissions in `defaultPermissions` on `SaaSOSProvider` (or in the console, as the org's own permissions):
  - Use `<WhenPermission permission="reports:export">` or `usePermissions().can('reports:export')` (the hook returns `{ can, permissions, isOwner, role, appPermissionDefinitions }` - the method is `can`)

---

## Tree 2: Do I Record a User Action on the Client or the Server?

You're recording usage, tracking an event, or consuming credits. Should that happen in the browser or in your API?

**Ask yourself: Where does the action actually complete?**

- If the action is purely a client-side event (page view, UI interaction, a toggle the user clicks):
  - Consider `useRecordUsage` from the React SDK
  - But continue reading - there are important caveats.

- If the action requires a server round-trip (API call, file processing, database write):
  - Record server-side. Don't record client-side. Continue.

**Ask yourself: Could a malicious user trigger the action without triggering the recording?**

- If yes (the recording is in a React `onClick` but the API accepts calls directly):
  - Must be server-side. Move recording to the API route.
- If no (the only way to trigger the action is through your API):
  - Server-side is still preferred, but client-side is acceptable for low-stakes tracking.

**Ask yourself: Could this be called twice for the same action? (Network retry, user double-click, job retry)**

- If yes:
  - Must use `idempotencyKey` to prevent double-counting (on `usage.record`, `usage.recordBatch`, `credits.consume` and `credits.reserve`).
  - Derive the key from the unit of work (the request ID, the job ID, the message ID), and send the same key on every retry of that work. A fresh UUID per attempt protects nothing: the SDK does not retry these POSTs for you, so your retry is the second attempt and must carry the first one's key.
  - This applies whether recording client-side or server-side.
  - `usage.record(workspaceId, { quotaSlug, quantity, idempotencyKey: 'gen-' + requestId })`

**Ask yourself: Is this inside a background job or cron task?**

- Always server-side. Never client-side.
- Use the `BuildBase()` factory directly.
- Use `withSession(serviceSessionId)` if you need a user-scoped session for a job.
- Use `recordBatch(workspaceId, { items: [...] })` for bulk operations (max 100 items per call).

**The short answer:**
- Client `useRecordUsage` → page views, analytics events, low-stakes UI interactions
- Server `usage.record(...)` → anything that affects billing, anything the user could manipulate, anything in a background job

---

## Tree 3: Credits or Quotas?

Both involve "counting" how much of something a workspace uses. The billing model is different.

**Ask yourself: Does usage reset automatically at the end of the billing period?**

- Yes, it resets → **Quota**
  - Example: 1000 API calls per month. When the billing period ends, the count resets.
  - Plan includes 1000 calls → workspace uses 750 → next month starts at 0 again.
  - Configure as a quota on the plan in the dashboard.

- No, it doesn't reset automatically → **Credits**
  - Example: 1000 AI tokens purchased. The user buys them, spends them down.
  - They don't get more at the end of the month unless they buy more.
  - Configure as credit packages in the dashboard.

**Ask yourself: Do users purchase this upfront, in advance?**

- Yes, they buy a pack of N units → **Credits**
  - Users go to a credits purchase flow to buy more.
  - Use `CreditActionsProvider` for the buy-and-consume UI.
  - Use `WhenCreditsAvailable min={N}` to gate actions that cost credits.
  - When the cost is known only after the work, hold an estimate first (`credits.reserve`, or `credits.withHold` on the server) and settle at the real cost.

- No, it's included in their subscription plan → **Quota**
  - The plan says "includes 1000 API calls/month."
  - Overage can be configured per-unit if you want pay-as-you-go above the limit.

**Ask yourself: Does it have overage billing?**

- Yes, users can go over the limit and pay per additional unit → **Quota with overage**
  - Configure overage pricing on the plan's quota definition in the dashboard.
  - SDK handles the `available` vs `overage` state automatically.

- No, when they run out they're blocked → **Quota without overage** or **Credits**
  - For time-reset blocking limits: Quota without overage.
  - For prepaid spending: Credits.

**Common mapping:**
- Monthly API call limit → Quota
- Monthly email sends → Quota
- Monthly storage GBs → Quota
- AI generation tokens → Credits
- One-time compute units → Credits
- "Token packages" users buy → Credits
- Per-generation cost → Credits (consume N credits per generation)

**The rule of thumb:**
Credits are like a prepaid card - spend until empty, buy more. Quotas are like a data plan - use what's included, potentially pay for more, resets monthly.

Both can belong to the person instead of the workspace: the credit hooks take `{ user: true }` for the signed-in person's own wallet, and the server records a person's own usage with `me.usage.record`.

---

## Tree 4: Personal Mode or Platform Mode?

Workspace mode is set in the Buildbase dashboard (Workspaces, then Settings, Mode) and determines how users and workspaces relate. A new org starts in Personal; Platform needs a BuildBase plan that includes it.

**Ask yourself: Is each user their own independent customer?**

- Yes, each user signs up for themselves, has their own subscription, and doesn't share anything with other users:
  - **Personal mode**
  - Example: a solo tool, a personal productivity app, a developer API service
  - Each user signs up → one workspace is automatically created for them → they subscribe → done
  - Users never create workspaces manually or invite members

- No, users belong to teams or organizations that share resources:
  - **Platform mode**
  - Example: Slack, Notion, GitHub, Vercel - any B2B SaaS
  - Organizations subscribe, not individuals
  - One org can have multiple workspaces, multiple members per workspace

**Ask yourself: Is this a B2C product (selling to individuals)?**

- Yes → **Personal mode**
  - Users don't think of themselves as "workspace owners"
  - The workspace concept is invisible to them
  - Their account IS their workspace
  - The plan is usually sold to the person (a pricing group whose payer is a person, read with `{ user: true }`), though a Personal workspace can hold a plan too

- No, it's B2B (selling to companies) → **Platform mode**
  - Users join a company account
  - Companies have multiple team members
  - Billing is per-workspace, not per-user

**Ask yourself: Do users need to invite other people to their account?**

- Yes → **Platform mode**
  - Platform mode enables workspace membership, invitations, and per-workspace roles
  - Personal mode doesn't support multi-user workspaces

- No, it's a single-user product → **Personal mode**

**Ask yourself: Can one user have multiple "projects" or "accounts" within your product?**

- Yes, users can have multiple separate contexts (like multiple GitHub organizations) → **Platform mode**
  - Platform mode supports multiple workspaces per user
  - Users can switch between workspaces

- No, one account per user → **Personal mode**

**The quick test:**
> "If two employees at the same company both use my product, should they be on the same account or different accounts?"

- Same account, shared subscription → **Platform mode**
- Different accounts, separate subscriptions → **Personal mode**

**What changes between the modes in the SDK:**
- Personal mode: each person gets exactly one workspace of their own on first sign-in, with no invitations and no switcher. Users never see workspace management UI.
- Platform mode: Users see workspace creation, invitations, and the workspace switcher. A new user still lands in a workspace of their own on first sign-in unless the org turns off "Auto-create first workspace" (`settings.workspace.autoCreateFirst`) for an invite-only app.
- Both modes: same SDK hooks, same gate components, same auth flow. The mode changes the user experience, not the technical integration.
