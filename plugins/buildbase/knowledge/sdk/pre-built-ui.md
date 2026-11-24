# Pre-built UI - what ships, so you do not rebuild it

**Read this before writing any settings, billing, members, profile, sign-in security, notifications or SSO screen.** BuildBase ships 18 settings screens, a workspace switcher, a pricing page, a credit store, a notification bell and inbox, invitation, guest and consent components, the enterprise single sign-on screens and an agent-connection guide. They are translated into 8 languages, permission-gated, responsive, and handle their own loading and error states. Verified against `@buildbase/sdk` 1.9.0.

The most expensive mistake an AI agent makes with BuildBase is hand-building UI that already exists. A "simple" members screen is invites, pending invitations, role changes, seat counting, seat-overage warnings, permission checks and eight translations. `openWorkspaceSettings('users')` is one line.

## Contents

- [The settings dialog](#the-settings-dialog) - 18 screens, one function
- [Opening billing and credits from anywhere](#opening-billing-and-credits-from-anywhere)
- [Headless page components](#headless-page-components) - pricing, credit store, checkout return, beta form
- [Workspace switcher and invitations](#workspace-switcher-and-invitations)
- [Notifications](#notifications) - bell and inbox
- [Account, guests and consent](#account-guests-and-consent) - guest upgrade, impersonation, keyless, cookies, badge
- [Agents and devices](#agents-and-devices)
- [Enterprise single sign-on screens](#enterprise-single-sign-on-screens)
- [Commerce components](#commerce-components) - selling and buying, in commerce.md
- [UI primitives](#ui-primitives) - make your own screens match
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

The sections are the values of `SettingsScreen` (type `WorkspaceSettingsSection`; `SETTINGS_SCREENS` is the set). The first group is the person's own account, the rest the current workspace's.

| Section | What the user gets |
|---|---|
| `profile` | Name, email (and change of email), username, language, country, currency, timezone |
| `security` | Password, phone number, two-step sign-in, connected accounts and wallets, passkeys, delete account |
| `devices` | Signed-in devices (rename, sign out, forget) and active sessions |
| `billing` | The person's own plan (1.0.0); shown once the app sells plans to people |
| `account-credits` | The person's own credit wallet (1.0.0); shown beside `billing` when the app sells credit packs to people |
| `connected-agents` | Connected OAuth2 agents such as MCP clients, with revoke, and the connect guide |
| `my-selling` | The person as a seller (1.2.0); listed while the app's selling is on |
| `general` | Workspace name, icon, billing currency |
| `users` | Invite members, pending invitations, assign roles, seat usage, remove members |
| `subscription` | Current plan, change plan with the cost previewed, add-ons, pause, cancel or resume, invoices |
| `usage` | Per-quota progress bars with consumption and overage |
| `credits` | The workspace's balance, purchase, auto top-up, transaction history, expiring credits |
| `features` | Toggle the workspace's user-managed feature flags |
| `notifications` | Push toggle and per-event email/push preferences, each member's own |
| `permissions` | The app's own permissions per role for this workspace; shown once the org defines a permission of its own, changed only by the workspace's creator |
| `enterprise` | Single sign-on (1.0.0): the company's connection, setup links and company admin screens; shown while `enterpriseSsoAvailable(settings)` |
| `selling` | The workspace as a seller (1.2.0); listed while the app's selling is on |
| `danger` | Delete the workspace (its creator), or leave it (any other member); hidden when each person may have only one workspace |

Call it with no argument for the default (`profile`) screen. Every screen already checks permissions, so a member without `workspace:billing:view` sees a no-permission pane rather than a blank one. A person in no workspace still gets their own account sections (1.0.0). `workspaceSettingsManager.openWorkspaceSettings(section?, params?)` also takes deep-link parameters, such as `{ action: 'openConnectGuide' }` for `connected-agents` (or `?bb=action:openConnectGuide` in the URL).

---

## Opening billing and credits from anywhere

Use these in upgrade banners, feature gates and empty states rather than routing the user to a page you built.

| Method | Opens |
|---|---|
| `openWorkspaceSettings(section?)` | The settings dialog |
| `openPlanPicker()` | Plan selection for the current workspace |
| `openCreditStore()` | Credit purchase |
| `openAccountBilling(params?)` | The person's own Billing screen |

```tsx
const { openPlanPicker, openCreditStore, openAccountBilling } = useSaaSAuth();
```

`<AccountBilling />` (`className`, `title`, `description`) is the person's own Billing screen on a page of your app instead of in the dialog. Plans, add-ons, trials and entitlement checks are in [billing.md](./billing.md); credits in [credits.md](./credits.md).

---

## Headless page components

These fetch the data and own the checkout logic; **you render the markup** through a required render prop. That is the point: the pricing logic is hard, the markup is yours.

```tsx
import { CreditStorePage, PricingPage } from '@buildbase/sdk/react';

<PricingPage slug="main-pricing" redirectBaseUrl="https://app.example.com/dashboard">
  {({ loading, error, items, plans, notes, refetch, selectPlan, promotion, addOns, selectAddOn, purchaseGuard }) => (
    /* your markup */ null
  )}
</PricingPage>

<CreditStorePage redirectBaseUrl="https://app.example.com/dashboard">
  {({ loading, error, packages, notes, refetch, selectPackage, purchaseGuard }) => (
    /* your markup */ null
  )}
</CreditStorePage>
```

- `slug` is the **plan-group** slug and must exist in the console, or the page renders empty. `redirectBaseUrl` is what makes `selectPlan` / `selectPackage` resume after sign-in for a signed-out visitor; without it the visitor is simply sent to sign-in and the choice is lost. A press made while the session is still being read waits for it.
- `selectPlan(planVersionId, interval, currency)`. `PricingPage` also takes `promotionCode` (or reads `?promo=` / `?coupon=`), `for="user"` for a plan group sold to people, `loadingFallback` and `errorFallback`, and since 1.9.0 `initialData`: the plans fetched on the server (`plans.getPublic(slug)` from `BuildBase()`), rendered from the first render so the HTML carries real prices and nothing shifts on hydration ([billing.md](./billing.md#prices-in-the-server-html-initialdata-190)).
- `<PricingPlanTerms plan currency interval id />` (1.9.0) goes beside a plan card's paid button: every interval the plan sells with its price, the setup fee sentence, and the renewal terms of the interval the button buys. Put its `id` in the button's `aria-describedby`. `CreditStorePage` takes `subject={{ user: true }}` to buy for the person's own wallet.
- `purchaseGuard` is `'confirming'`, `'clearing'` or null: while set, show "A purchase is being confirmed" in place of the buy buttons, so a buyer back from Stripe is not offered the same thing twice.
- `<CheckoutStatus />` renders the return from Stripe inline on your own route (`ui.routes.checkoutReturn`); by default the provider confirms the return in a dialog.
- `<CreditBalance>{details => ...}</CreditBalance>` and `<CreditActionsProvider>` are render-prop components for the balance and purchases (see [credits.md](./credits.md)).
- `<BetaForm onSuccess={...} />` is a drop-in beta signup form (`onError`, `className`, `fieldClassName`, `autoFocus`, `showSuccessMessage`, `hideLogo`, `hideTitles`).

---

## Workspace switcher and invitations

```tsx
import { WorkspaceSwitcher } from '@buildbase/sdk/react';

<WorkspaceSwitcher trigger={(isLoading, currentWorkspace) => /* your trigger */ null} />
```

Note the argument order: `(isLoading, currentWorkspace)`. `trigger` is its only prop.

`<PendingInvitations />` (Accept and Decline; `onAccepted`, `switchOnAccept`, `hideWhenEmpty`, `title`, `description`, `emptyLabel`) and the gate `<WhenPendingInvitations>` put the signed-in user's invitations on your own no-workspace screen; the switcher already shows them in its empty state in an invite-only app. Details in [workspace.md](./workspace.md).

---

## Notifications

`<NotificationBell />` is a bell with the unread count that opens the inbox in a panel; `<NotificationInbox />` is the full inbox for a page (`workspaceId`: an id, `'current'`, `'none'`, or omitted for everything). Both share one list with `useNotifications()`. See [notifications.md](./notifications.md).

---

## Account, guests and consent

| Component | What it is |
|---|---|
| `<GuestUpgrade />` | "Create your account" for a guest (`useSaaSAuth().user.isAnonymous`), keeping their id, data and session; renders nothing for anyone else. Headless: `useGuestUpgrade()` |
| `<ImpersonationBanner />` | Says an app owner is viewing the app as the person. The provider already pins it; `ui.impersonationBanner: false` hides that one |
| `<KeylessPrompt config={process.env.NEXT_PUBLIC_BUILDBASE_KEYLESS} />` | In keyless development, says the app runs on a temporary organization and how to claim it; renders nothing without a config, so it can stay in the layout |
| `<CookieBanner />` | Asks a visitor about cookies once (Accept all, Reject all, Choose); opt-in, placed yourself or with `ui.cookieBanner: true`. `openCookieBanner()` shows it again for a "Cookie settings" link |
| `<WorkspaceAccessRefused />` | The company's refusal for one workspace, with **Confirm it's you** or **Sign in again** (see [auth.md](./auth.md)) |
| `<ConfirmItsYou stepUp={...} />` | The re-confirmation prompt for custom screens on `useStepUp` |
| `<FullScreenLoader />` | The overlay the provider uses (`message`, `children`, `backgroundColor`) |
| `<BuildBaseBadge />` | The "Built with BuildBase" badge; needs no provider |

---

## Agents and devices

`<ConnectedAgents />`, `<Devices />` and `<Sessions />` are the same screens the settings dialog opens, exported so you can embed them in your own pages. All props are optional.

Set `mcp` on the provider and the connected-agents screen gains a **Connect an agent** guide: a copyable server URL, a paste-into-your-AI prompt, and setup steps for ChatGPT, Claude, Cursor, VS Code, Devin Desktop (formerly Windsurf) and Cline.

```tsx
<SaaSOSProvider mcp={{ url: 'https://app.example.com/api/mcp', name: 'Acme' }}>
```

The guide is also standalone as `<ConnectMcpGuide />`, and renders `null` when no `mcp.url` is set. For fully custom UI, `useConnectedAgents()`, `useDevices()` and `useSessions()` return headless data and actions. This `mcp` prop is about your own app's MCP server (built with `@buildbase/sdk/mcp`), not BuildBase's hosted console MCP server.

---

## Enterprise single sign-on screens

Enterprise single sign-on and Directory Sync work through the app owner's own WorkOS account, set up in the BuildBase console. Since 1.0.0 the app side is pre-built: the `enterprise` settings section, or `<EnterpriseAccess />` on its own (`workspaceId`, `title`, `description`, `className`), shows the company's connection, **Set up SSO** for its IT admin, directory sync and certificate cards, and, for the company's own admins, its activity, access policy, admins, roles, groups, domains, joining, connected apps, API keys and more.

Each part is also exported for a page of its own: `EnterpriseActivity`, `EnterpriseSecurity`, `EnterpriseAdmins`, `EnterpriseRoles`, `EnterpriseGroups`, `EnterpriseManagedGroups`, `EnterpriseDomains`, `EnterpriseJoining`, `EnterpriseConnectedApps`, `EnterpriseAgentAccess`, `EnterpriseApiKeys`, `EnterpriseWorkloadIdentity`, `EnterpriseIdentityProviders`, `EnterpriseItContacts`, `EnterpriseInsights`, `EnterpriseLogStreams`, `EnterpriseWorkOSRoles` and `EnterpriseWorkspacePolicy`. Hide parts with `ui.settings.enterprise.*`. The headless hooks (`useEnterprise`, `useEnterprisePolicy`, ...) are listed in the SDK package's `agents/react.md`.

---

## Commerce components

Selling through Stripe Connect (`SellerHome`, `StartSelling`, `SellerItems`, `SellerSales`, `SellerStats`, ...), buying (`BuyButton`, `CartSummary`, ...), reviews (`ReviewList`, `ReviewForm`, `RatingSummary`, 1.9.0), bookings, affiliates, shipping and coupons have their own components and hooks. They are in [commerce.md](./commerce.md), and the settings dialog's `my-selling` and `selling` sections show the seller screens while the app's selling is on.

---

## UI primitives

`SectionHeader`, `EmptyState`, `StatusBanner`, `LoadingState`, `Progress`, `SidebarNavSection` and `SidebarNavItem` are the primitives the SDK's own screens use. Build a custom screen with them so it matches the rest of the dialog.

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
      danger: { leave: false },
    },
    workspaceSwitcher: { createButton: false, planBadge: false },
    behavior: { autoOpenPlanDialog: false, trialEndingDays: 7 },
    messages: { settings: { sidebar: { credits: 'Tokens' } } },  // rename anything
    formats: { date: { dateStyle: 'short' } },
  }}
>
```

Hidden sections disappear from the sidebar and are unreachable by deep link. **Visibility is not security**: `ui` only hides UI, and the platform still enforces permissions underneath. `useUIVisibility()` applies the same combined config-plus-permission decision to your own components, and `useUIConfig()` reads the raw config. The full option list is the SDK package's `docs/UI-CONFIG.md`.

---

## Theming

Every SDK component is styled through CSS custom properties, so overriding variables re-skins all of it. No forks, no `!important`.

The SDK declares its variables on `.saas-os-ui`, the class on its own container, not on `:root`, so it cannot restyle your app. Write your overrides against the same selector and load them after `@buildbase/sdk/css`: an override on `:root` alone is shadowed by the SDK's own rule. Values are **HSL triplets with no `hsl()` wrapper**, which is what lets the SDK derive tints such as `hsl(var(--success) / 0.1)`.

```css
.saas-os-ui {
  --primary: 262 83% 58%;
  --primary-foreground: 0 0% 100%;
  --radius: 0.75rem;
  /* Each status colour is a fill and a text tone */
  --destructive: 0 72% 45%;
  --destructive-text: 0 72% 36%;
  --success: 142 72% 26%;
  --success-text: 142 72% 19%;
  --warning: 26 90% 33%;
  --warning-text: 26 90% 24%;
  --info: 224 76% 48%;
  --info-text: 224 76% 38%;
}
```

The full set covers `--background`, `--card`, `--popover`, `--primary`, `--secondary`, `--muted`, `--accent`, `--destructive`, `--success`, `--warning`, `--info`, each with a `-foreground` pair, plus `--destructive-text`, `--success-text`, `--warning-text`, `--info-text`, `--border`, `--input`, `--ring` and `--radius`. When rebranding a status colour, set both its fill and its `-text` tone, in the light rule and the dark one.

Dark mode: the SDK ships dark values that apply under a `dark` class on any ancestor (the class next-themes and Tailwind's `darkMode: 'class'` put on `<html>`). Override the dark palette under `.dark .saas-os-ui`. The SDK package's `docs/THEMING.md` has the contrast rules.

---

## Languages

```tsx
<SaaSOSProvider locale="es">
```

Eight locales: `en`, `es`, `fr`, `de`, `ja`, `zh`, `hi`, `ar` (`SUPPORTED_LOCALES`; a regional tag such as `zh-TW` resolves to the nearest). English is bundled and the others lazy-load. Arabic sets `dir="rtl"` throughout, and Hindi and Arabic render native numerals. The hosted sign-in page opens in the same language, or in the `locale` you set in `auth`.

`useTranslation()` gives you `t`, `locale`, `formattingLocale`, `dir`, `fmtCents(cents, currency)`, `fmtNum(n)` and `messages` for your own components, so your markup formats money and numbers the same way the SDK's does. `t('users.memberCount', { count: 3 })` is ICU MessageFormat with compile-time-checked keys (`TranslationKey`). Override any SDK string with `ui.messages` (a `PartialSDKMessages`).

---

## What is NOT pre-built

There is no pre-built UI for email campaigns, workflows, collections, content, forms, short links or assets. Those are driven from the console and the org API - see [../http-api/org-api.md](../http-api/org-api.md). Do not go looking for a `useCollections` hook; it does not exist.

Your product's own screens are also yours. BuildBase covers the account, billing and membership surface that every SaaS needs and no one wants to write twice.
