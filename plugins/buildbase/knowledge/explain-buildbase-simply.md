# Buildbase Explained Simply

Plain-language explanations for someone brand new. No jargon. Use these analogies when a beginner asks "what is this?" or "why do I need it?"

---

## What is Buildbase?

Imagine you want to open a shop. Before you can sell anything, you'd normally have to build:
- a **lock and a membership desk** (so only the right people get in) → that's **authentication**
- a **cash register that handles cards, subscriptions, and receipts** → that's **billing**
- a **rule book** of who's allowed to do what → that's **permissions and feature flags**
- a **meter** that tracks how much each customer uses → that's **quotas and usage**

Building all of that yourself takes months and is easy to get wrong (especially the security and payments parts).

**Buildbase is a company you hire to run all of that for you.** You connect your app to Buildbase, and it handles the locks, the register, the rule book, and the meter. You just build the actual thing your customers came for.

---

## The words you'll keep seeing (in plain English)

| Word | What it really means |
|------|----------------------|
| **SDK** | The toolbox (`@buildbase/sdk`) you install to talk to Buildbase. "SDK" = "Software Development Kit" = a bundle of ready-made code. |
| **Org (organization)** | Your company/product as Buildbase knows it. You get one when you sign up. |
| **Workspace** | A single customer account or team. If you build a team tool, each team is one workspace. Billing and limits attach to a workspace. |
| **User** | A person who logs in. A user can belong to one or more workspaces. |
| **Session** | Proof that a user is logged in right now. Stored as a `sessionId`. |
| **Cookie** | A small note the browser keeps. We store the login proof in a special **httpOnly** cookie — one that page scripts can't read, so it can't be stolen. |
| **Provider** | One React component (`SaaSOSProvider`) you wrap your whole app in. It makes Buildbase available everywhere. You write one; the SDK does the rest. |
| **Factory** | A function (`BuildBase(...)`) you call once on your server that hands back a set of tools. |
| **Gate** | A component whose name starts with `When…` (like `WhenAuthenticated`). It shows its contents only when a condition is true. |
| **Slug** | A short lowercase id for something you set up in the dashboard, like `pro` for a plan or `analytics` for a feature. Your code refers to things by their slug. |
| **Dashboard** | The Buildbase website ([console.buildbase.app](https://console.buildbase.app)) where you (the developer) configure plans, features, and login methods. Not the same as your app. Official docs: [docs.buildbase.app](https://docs.buildbase.app). |
| **Plan** | A pricing tier (Free, Pro, Enterprise). You define these in the dashboard; Buildbase charges cards via Stripe. |
| **Quota** | A usage limit that resets each billing period (e.g. "5,000 API calls/month"). |
| **Credits** | Prepaid units a customer buys up front (e.g. "100 AI generations"). They don't reset. |

---

## The one rule that prevents most confusion

**Dashboard first, then code.**

Many Buildbase features depend on something you set up in the dashboard *before* your code can use it. If you write `<WhenWorkspaceFeatureEnabled slug="analytics">` but never created an "analytics" feature in the dashboard, nothing shows up — and there's no error, just silence. That silence confuses everyone.

So whenever a feature involves a **slug** (a plan, a feature, a quota), the order is always:
1. Create it in the dashboard (give it a slug).
2. Reference that exact slug in your code.

---

## The smallest possible explanation of how login works

1. Your user clicks **Sign In**.
2. Buildbase shows them a login page and, when they succeed, sends them back to your app with a temporary **code**.
3. Your app's server quietly trades that code (using a secret key) for a **session**, and remembers it in a cookie.
4. The user is now logged in, and stays logged in across refreshes.

You don't have to build the login page or handle passwords — Buildbase does. You just wire up the hand-off. The step-by-step is in [sdk/quick-start.md](./sdk/quick-start.md).

---

## What Buildbase does NOT do

So you don't go looking for features that aren't there:
- It's **not your database.** Your app's own data (todos, posts, whatever) lives in your own database. Buildbase handles accounts, billing, and limits — not your business data.
- It's **not a UI framework.** It gives you some ready-made screens (login, pricing, settings), but you build your actual app's interface.
- It **doesn't replace your backend.** You still have your own API routes; Buildbase plugs into them.
