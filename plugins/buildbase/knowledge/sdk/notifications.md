# Notifications

This is how your app tells users something happened - "your export is ready," "payment failed," "Alice commented." BuildBase delivers those messages two ways: **email** (lands in their inbox) and **push** (a pop-up from the browser, even when your tab is closed), and keeps every one in an **in-app inbox** the user can come back to. You'll reach for this whenever code needs to nudge a user. New to the SDK? Start with [quick-start.md](./quick-start.md) - this guide assumes you already have the `notification` tool wired up. Verified against `@buildbase/sdk` 1.9.0.

## Contents

- [System Overview](#system-overview) - channels, the inbox and notification types
- [Push Notifications Setup](#push-notifications-setup) - serve the SDK's service worker
- [Sending Notifications (Server-Side)](#sending-notifications-server-side) - `notification.send` usage and limits
- [Notification Data Options](#notification-data-options) - full payload interface
- [Scheduling and cancelling](#scheduling-and-cancelling) - `scheduledAt`, `notification.cancelScheduled`
- [Channel Control](#channel-control) - forcing email vs push, the 4 gates
- [Merge Tags](#merge-tags) - `{{placeholder}}` personalization
- [Creating Custom Notification Events](#creating-custom-notification-events) - dashboard setup, or the first send
- [Notification Response](#notification-response) - shape returned by send
- [Notification Inbox](#notification-inbox) - `NotificationBell`, `NotificationInbox`, `useNotifications`
- [Push State Hook](#push-state-hook) - `usePushNotifications` subscribe UI
- [Member preferences](#member-preferences) - the Notifications settings screen

## System Overview

BuildBase provides a layered notification system:
1. **Email** - sent through the email sender connected in the console (SMTP, Google, Mailgun or Amazon SES)
2. **Push notifications** - short pop-up messages delivered via the browser's **Web Push API** (the standard browsers use to show alerts when your site isn't even open)
3. **Inbox** - every notification is also kept as one item per recipient, whichever channels reached them, for `<NotificationBell />` and `<NotificationInbox />`
4. **Channel control** - choosing *which* of email and push fires, per-event and per-member (a **channel** = one delivery path)

Three types of notifications:
- **System notifications** - Auto-triggered by BuildBase itself (invite, payment failed, trial ending). You manage these in the admin dashboard; no code needed.
- **Custom notifications** - Events *you* define in the dashboard, then trigger from your code.
- **Ad-hoc notifications** - A send with an event slug you never set up. It delivers push and the inbox item; email starts only once an email template is attached to the event. On a server from release 22 the first send registers the event, so it shows in the console and counts toward the plan's custom events.

---

## Push Notifications Setup

The browser runs a small script, a **service worker**, to show a push when it arrives, even when your app's tab is closed. The SDK ships it as the `PUSH_SERVICE_WORKER_SCRIPT` string (exported from both `@buildbase/sdk` and `@buildbase/sdk/react`). Write it into your public directory at build time, so it updates with the SDK:

```js
// scripts/write-push-sw.mjs
import fs from 'node:fs';
import { PUSH_SERVICE_WORKER_SCRIPT } from '@buildbase/sdk';

fs.writeFileSync('public/push-sw.js', PUSH_SERVICE_WORKER_SCRIPT);
```

```json
{
  "scripts": {
    "predev": "node scripts/write-push-sw.mjs",
    "prebuild": "node scripts/write-push-sw.mjs"
  }
}
```

- It must be served at `/push-sw.js` itself. `SaaSOSProvider` mounts its push provider on that path and has no prop to change it; to keep the file elsewhere, answer `/push-sw.js` through a rewrite, never a redirect (browsers refuse a worker script that redirects).
- **Do not hand-write a copy of the worker.** A copy does not pick up fixes when you upgrade. Since 0.0.83 the shipped worker shows everything the server sends (image, badge, action buttons, `requireInteraction`, `silent`, `renotify`, `timestamp`, `dir`), a `tag` replaces an earlier notification instead of stacking, and a click opens the tracked link so clicks are counted.
- Turn **Push notifications** on in the console (Messaging, Notification events, Global). Off, no event sends a push.

Everything else is automatic - subscription management, settings UI, billing event triggers.

---

## Sending Notifications (Server-Side)

The `notification` tool comes from your server-side BuildBase setup in `src/lib/buildbase.ts` (see [server-side.md](./server-side.md)). The second argument is the **event slug** - the short code identifier for a notification event (e.g. `comment_added`), which you either define in the dashboard or send ad-hoc.

```ts
import { notification } from '@/lib/buildbase';

// Notify a specific user
await notification.send(workspaceId, 'comment_added', userId, {
  title: 'New Comment',
  message: 'Alice commented on your project',
  icon: 'https://cdn.example.com/comment-icon.png',
  image: 'https://cdn.example.com/screenshot.jpg',
  url: 'https://app.example.com/projects/123#comments',
});

// Notify all workspace members (omit userId)
await notification.send(workspaceId, 'new_release', undefined, {
  title: 'Version 2.0 Released',
  message: 'Dark mode, API v2, and more!',
  url: '/changelog',
});

// Ad-hoc push (no event pre-registration required)
await notification.send(workspaceId, 'deployment_done', userId, {
  title: 'Deployment Complete',
  message: 'v2.1.0 deployed to production',
  channels: { push: true },  // Push only, skip email
});
```

Signature: `send(workspaceId, event, userId?, data?) => Promise<NotificationResult>`. Limits:
- An event name is at most 128 characters, and `data` as JSON at most 64 KB; past either the send answers 400.
- One workspace's sends register at most **20 new event names a UTC day**; the 21st answers 403 `NOTIFICATION_EVENT_NOT_SET_UP` (also the answer at the plan's custom-event limit). Send a fixed set of event names and put what varies in `data`, never in the name.
- More than 300 sends in an hour from one workspace answers 429.
- A `userId` that is not a member of the workspace answers 404.

---

## Notification Data Options

```ts
interface NotificationData {
  title?: string;                               // Push title (falls back to the event name)
  message?: string;                             // Push body + email {{message}}
  icon?: string;                                // Push icon URL (falls back to the org icon)
  image?: string;                               // Large push image
  badge?: string;                               // Status bar icon (monochrome)
  url?: string;                                 // Opens on push click + {{url}} in email
  tag?: string;                                 // Replace existing notification
  actions?: Array<{ action: string; title: string; icon?: string }>;  // Max 2
  silent?: boolean;                             // No sound/vibration
  requireInteraction?: boolean;                 // No auto-dismiss
  renotify?: boolean;                           // Re-alert on tag replace (needs tag)
  timestamp?: number;                           // Custom timestamp (ms)
  dir?: 'ltr' | 'rtl' | 'auto';
  ttl?: number;                                 // Time-to-live (seconds, default 86400)
  urgency?: 'very-low' | 'low' | 'normal' | 'high';
  scheduledAt?: string;                         // ISO 8601: holds the whole delivery, at most 365 days ahead
  channels?: { email?: boolean; push?: boolean };  // Override default channels
  [key: string]: unknown;                       // Custom merge tags for email
}
```

`NotificationData`, `NotificationResult` and `NotificationEvent` are exported types from `@buildbase/sdk`.

---

## Scheduling and cancelling

A future `scheduledAt` holds the whole delivery (inbox item, email and push), not only the push, and the send answers with an id you can cancel by:

```ts
const held = await notification.send(workspaceId, 'daily_digest', undefined, {
  message: '12 new updates in your workspace',
  scheduledAt: '2026-12-01T09:00:00Z',
});
// held: { sent, channels, scheduled: true, scheduledAt, scheduledId }

if (held.scheduledId) await notification.cancelScheduled(workspaceId, held.scheduledId);
// { cancelled: true, scheduledId }
```

`cancelScheduled` (since 1.6.0; `WorkspaceApi.cancelScheduledNotification` in the browser) is refused 404 for an unknown id and 409 `SCHEDULED_SEND_NOT_PENDING` once the send is sending, sent, failed or cancelled. A time more than 365 days ahead, or not a date-time, is a 400.

---

## Channel Control

```ts
// Push only
await notification.send(workspaceId, 'typing', userId, {
  message: 'Alice is typing...',
  channels: { push: true },
});

// Email only
await notification.send(workspaceId, 'weekly_report', undefined, {
  message: 'Your weekly summary is ready',
  channels: { email: true },
});
```

Even when you force a channel in code, the notification still has to clear **4 gates** - every one must be "on" for that channel to send:
1. Org global on/off for email or push (admin dashboard)
2. Event config: the event's master switch and its email/push defaults (admin dashboard)
3. Preferences, only for events marked `userManaged`: each member's own choice in the workspace, then the workspace default (a default an admin marked required is what every member gets)
4. User unsubscribe (the end-user opted out of email), checked at delivery

Preferences decide how a member is interrupted, not whether the notification is recorded: with both channels off it still appears in their inbox. The gate fails open: a slug with no event config sends (a send through the SDK registers it first).

---

## Merge Tags

A **merge tag** is a `{{placeholder}}` in your title or message that BuildBase swaps for a real value at send time (so one template personalizes for every recipient). Both email templates and push use this syntax:

```ts
await notification.send(workspaceId, 'export_ready', userId, {
  title: '{{workspaceName}}: Export Ready',
  message: 'Hi {{name}}, your export is complete',
  downloadUrl: 'https://example.com/exports/abc',
  url: '/downloads',
});
```

Built-in tags: `{{name}}`, `{{email}}`, `{{workspaceName}}`, `{{message}}`, `{{url}}`

Custom tags: any key in the data object (`{{downloadUrl}}`, `{{planName}}`, etc.)

---

## Creating Custom Notification Events

In the BuildBase dashboard (Messaging, Notification events, the **Custom** tab, **Create custom event**):
1. **Name** - Display name (e.g., "Comment Added")
2. **Slug** - Code identifier (e.g., `comment_added`)
3. **Description** and **Category** - Category groups events in user settings
4. **User can toggle this in workspace settings** - If on, members can turn this notification off for themselves (`userManaged`; "User control" when you edit the event)

The event is made with email and push on (change either later) and its own email template, `custom-notification-<slug>`; customize it in Email Templates. Your plan caps how many custom events you have.

An event registered by its first send instead starts with push and the inbox only, has no email template, and counts toward the plan's custom notification events like one made in the console. The slug is stored lowercase; letters, digits, `.`, `_`, `:` and `-` are kept, so `comment_added` stays `comment_added`.

---

## Notification Response

```ts
const result = await notification.send(...);
// {
//   sent: true,                         // at least one recipient was resolved; check channels
//   channels: { email: true, push: true },
//   notifiedCount: 5                    // 1 for single user, N for workspace-wide, 0 when nothing was sent
// }
// A switched-off event: { sent: false, reason: 'event_disabled', channels: { email: false, push: false }, notifiedCount: 0 }
// A held send adds: scheduled: true, scheduledAt, scheduledId
```

An older self-hosted server leaves `channels` and `notifiedCount` out of the `event_disabled` answer, so read them with `?.` if your app may talk to one. A broadcast to a workspace with no members is not an error: `sent: false` with `notifiedCount: 0`.

---

## Notification Inbox

Everything your app sends a user, by email, push or both, is kept for them as an inbox. One notification is one item however it was delivered, and the item says what each channel did (email opened or clicked, push clicked). Opening an email does not mark the item read; opening it in the inbox or clicking its email or push link does. Sign-in codes, magic links and password resets are never in it.

```tsx
import { NotificationBell, NotificationInbox } from '@buildbase/sdk/react';

function Header() {
  // Unread count on a bell, the inbox in a panel. Opening it marks the items
  // seen, which clears the highlight without reading anything.
  return <NotificationBell />;
}

function NotificationsPage() {
  // The current workspace only. Omit workspaceId for every workspace,
  // or pass 'none' for account notices that belong to none.
  return <NotificationInbox workspaceId="current" />;
}
```

- `<NotificationInbox />` props: `workspaceId`, `pageSize` (default 20, at most 100), `pollIntervalMs`, `live`, `title` and `description` (`null` hides), `showFilter`, `onSelect(item)` (by default opens the item's `link`; pass your router's navigation for an app path), `emptyLabel`, `markSeenOnView`, `compact`, `className`.
- `<NotificationBell />` takes the same scope options plus `align`, `maxCount` (default 99, then "99+") and `inboxProps`.
- `useNotifications(options)` is the hook behind both: `{ notifications, unread, counts: { unread, unseen }, loading, loadingMore, hasMore, error, refresh, loadMore, markRead, markUnread, archive, markAllRead, markSeen }`. Every consumer of the same scope shares one list, so a bell and an inbox page make one request and a read in either updates both. New items arrive over one live connection per tab (`live`, default true), with polling every minute while the tab is visible as the fallback (`pollIntervalMs`, 0 to turn it off).
- `useNotificationsApi()` is the memoized `NotificationsApi` (`list`, `counts`, `markRead`, `markUnread`, `archive`, `unarchive`, `markAllRead`, `markSeen`).

A user only ever sees their own notifications; the whole workspace's history is in the console.

---

## Push State Hook

```tsx
import { usePushNotifications } from '@buildbase/sdk/react';

function NotificationToggle() {
  const { isSupported, isSubscribed, permission, loading, error, subscribe, unsubscribe } =
    usePushNotifications();

  if (!isSupported) return null; // no push support, or not on HTTPS or localhost

  return (
    <div>
      <button disabled={loading} onClick={isSubscribed ? unsubscribe : subscribe}>
        {isSubscribed ? 'Disable Push Notifications' : 'Enable Push Notifications'}
      </button>
      {permission === 'denied' && <p>Allow notifications in your browser's site settings.</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
```

It works anywhere inside `SaaSOSProvider`, which mounts the push provider. `subscribe()` asks the browser for permission itself (`requestPermission()` asks without subscribing), then registers this browser with BuildBase; for a signed-out visitor it does nothing, because a subscription belongs to a user. A browser that blocked notifications cannot be asked again by your app. At the plan's push subscriber limit a new browser is turned away; browsers already subscribed keep receiving.

---

## Member preferences

The `notifications` settings screen (`openWorkspaceSettings('notifications')`) includes the push toggle and per-event email/push toggles, **only for events where you enabled "User Control"**; system notifications are never shown to end users. Since SDK 0.0.71 on a server from release 22 it is each member's own ("Your notifications") over the workspace defaults, which admins set on the same screen. Hide parts with `ui.settings.notifications` (`push`, `emailToggles`, `pushToggles`).
