# Pre-built UI - what ships, so you do not rebuild it

**Read this before writing any settings, billing, members or profile screen.** BuildBase ships 13 settings screens, a workspace switcher, a pricing page, a credit store and an agent-connection guide. They are translated into 8 languages, permission-gated, responsive, and handle their own loading and error states.

The most expensive mistake an AI agent makes with BuildBase is hand-building UI that already exists. A "simple" members screen is invites, role changes, seat counting, seat-overage warnings, permission checks and eight translations. `openWorkspaceSettings('users')` is one line.

## Contents

- [The settings dialog](#the-settings-dialog) - 13 screens, one function
- [Opening billing and credits from anywhere](#opening-billing-and-credits-from-anywhere)
- [Headless page components](#headless-page-components) - pricing, credit store, beta form
- [Workspace switcher](#workspace-switcher)
- [Agents and devices](#agents-and-devices)
- [Hiding parts of it: the `ui` prop](#hiding-parts-of-it-the-ui-prop)
- [Theming](#theming) - CSS variables, no forks
- [Languages](#languages) - 8 locales, RTL
- [What is NOT pre-built](#what-is-not-pre-built)

---

## The settings dialog

One call opens it. Pass a section to land directly on that screen.

```tsx
import { useSaaSAuth } from '@buildbase/sdk/react';

function SettingsButton() {
  const { openWorkspaceSettings } = useSaaSAuth();
  return <button onClick={() => openWorkspaceSettings('subscription')}>Billing</button>;
}
```

| Section | What the user gets |
|---|---|
| `profile` | Name, email, language, country, currency, timezone |
| `security` | Passkeys and active sessions |
| `devices` | Signed-in devices: rename, sign out, forget |
| `connected-agents` | Connected OAuth2 agents such as MCP clients, with revoke |
| `general` | Workspace name, icon, billing currency |
| `users` | Invite members, assign roles, seat usage, remove members |
| `subscription` | Current plan, change plan, cancel or resume, invoices |
| `usage` | Per-quota progress bars with consumption and overage |
| `credits` | Balance, purchase, transaction history, expiring credits |
| `features` | Toggle workspace feature flags |
| `notifications` | Push toggle and per-event email/push preferences |
| `permissions` | Role-permission matrix with toggles |
| `danger` | Delete workspace, with confirmation |

Call it with no argument for the default (`profile`) screen. Every screen already checks permissions, so a member without `workspace:billing:view` sees a no-permission pane rather than a blank one.

---

## Opening billing and credits from anywhere

Use these in upgrade banners, feature gates and empty states rather than routing the user to a page you built.

| Method | Opens |
|---|---|
| `openWorkspaceSettings(section?)` | The settings dialog |
| `openPlanPicker()` | Plan selection |
| `openCreditStore()` | Credit purchase |

```tsx
const { openPlanPicker, openCreditStore } = useSaaSAuth();
```

---

## Headless page components

These fetch the data and own the checkout logic; **you render the markup** through a required render prop. That is the point: the pricing logic is hard, the markup is yours.

```tsx
import { PricingPage, CreditStorePage } from '@buildbase/sdk/react';

<PricingPage slug="main-pricing" redirectBaseUrl="https://app.example.com/dashboard">
  {({ loading, error, plans, selectPlan, notes, refetch }) => /* your markup */}
</PricingPage>

<CreditStorePage>
  {({ loading, error, packages, selectPackage }) => /* your markup */}
</CreditStorePage>
```

`slug` is the **plan-group** slug and must exist in the console, or the page renders empty. `redirectBaseUrl` is what makes `selectPlan` resume after sign-in for a signed-out visitor; without it the visitor is simply sent to sign-in and the choice is lost.

`<BetaForm onSuccess={...} />` is a drop-in beta signup form.

---

## Workspace switcher

```tsx
import { WorkspaceSwitcher } from '@buildbase/sdk/react';

<WorkspaceSwitcher trigger={(isLoading, currentWorkspace) => /* your trigger */} />
```

Note the argument order: `(isLoading, currentWorkspace)`.

---

## Agents and devices

`<ConnectedAgents />`, `<Devices />` and `<Sessions />` are the same screens the settings dialog opens, exported so you can embed them in your own pages. All props are optional.

Set `mcp` on the provider and the connected-agents screen gains a **Connect an agent** guide: a copyable server URL, a paste-into-your-AI prompt, and setup steps for ChatGPT, Claude, Cursor, VS Code, Windsurf and Cline.

```tsx
<SaaSOSProvider mcp={{ url: 'https://app.example.com/api/mcp', name: 'Acme' }}>
```

The guide is also standalone as `<ConnectMcpGuide />`, and renders `null` when no `mcp.url` is set. For fully custom UI, `useConnectedAgents()`, `useDevices()` and `useSessions()` return headless data and actions.

---

## Hiding parts of it: the `ui` prop

Before deciding a screen does not fit and rebuilding it, check whether you can just turn parts off. `ui` is additive: every option defaults to current behavior.

```tsx
<SaaSOSProvider
  ui={{
    settings: {
      sections: { credits: false, 'connected-agents': false },   // whole screens
      subscription: { cancel: false, invoicesTab: false },       // parts of a screen
      users: { invite: false, seatPricing: false },
    },
    workspaceSwitcher: { createButton: false, planBadge: false },
    behavior: { autoOpenPlanDialog: false, trialEndingDays: 7 },
    messages: { settings: { sidebar: { credits: 'Tokens' } } },  // rename anything
    formats: { date: { dateStyle: 'short' } },
  }}
>
```

Hidden sections disappear from the sidebar and are unreachable by deep link. **Visibility is not security**: `ui` only hides UI, and the platform still enforces permissions underneath. `useUIVisibility()` applies the same combined config-plus-permission decision to your own components, and `useUIConfig()` reads the raw config.

---

## Theming

Every SDK component is styled through CSS custom properties, so overriding variables re-skins all of it. No forks, no `!important`.

Values are **HSL triplets with no `hsl()` wrapper**, which is what lets the SDK derive tints such as `hsl(var(--success) / 0.1)`. Load your overrides after `@buildbase/sdk/css`.

```css
:root {
  --primary: 262 83% 58%;
  --primary-foreground: 0 0% 100%;
  --radius: 0.75rem;
  --destructive: 0 84% 60%;
  --success: 142 72% 29%;
  --warning: 26 90% 37%;
  --info: 224 76% 48%;
}
```

The full set covers `--background`, `--card`, `--popover`, `--primary`, `--secondary`, `--muted`, `--accent`, `--destructive`, `--success`, `--warning`, `--info`, each with a `-foreground` pair, plus `--border`, `--input`, `--ring` and `--radius`. Dark theme is the same variables under `.dark`.

---

## Languages

```tsx
<SaaSOSProvider locale="es">
```

Eight locales: `en`, `es`, `fr`, `de`, `ja`, `zh`, `hi`, `ar`. Arabic sets `dir="rtl"` throughout. `useTranslation()` gives you `t`, `locale`, `dir`, `fmtCents(cents, currency)` and `fmtNum(n)` for your own components, so your markup formats money and numbers the same way the SDK's does.

---

## What is NOT pre-built

There is no pre-built UI for email campaigns, workflows, collections, content, forms, short links or assets. Those are driven from the console and the org API - see [../http-api/org-api.md](../http-api/org-api.md). Do not go looking for a `useCollections` hook; it does not exist.

Your product's own screens are also yours. BuildBase covers the account, billing and membership surface that every SaaS needs and no one wants to write twice.
