# Notifications

This is how your app tells users something happened — "your export is ready," "payment failed," "Alice commented." Buildbase sends those messages two ways: **email** (lands in their inbox) and **push** (a pop-up from the browser, even when your tab is closed). You'll reach for this whenever code needs to nudge a user outside the app itself. New to the SDK? Start with [quick-start.md](./quick-start.md) — this guide assumes you already have the `notification` tool wired up.

## Contents

- [System Overview](#system-overview) — the 3-layer model and notification types
- [Push Notifications Setup](#push-notifications-setup) — required service worker file
- [Sending Notifications (Server-Side)](#sending-notifications-server-side) — `notification.send` usage
- [Notification Data Options](#notification-data-options) — full payload interface
- [Channel Control](#channel-control) — forcing email vs push, the 4 gates
- [Merge Tags](#merge-tags) — `{{placeholder}}` personalization
- [Creating Custom Notification Events](#creating-custom-notification-events) — dashboard setup
- [Notification Response](#notification-response) — shape returned by send
- [Push State Hook](#push-state-hook) — `usePushNotifications` subscribe UI

## System Overview

Buildbase provides a 3-layer notification system:
1. **Email** — sent through whichever email provider you've configured (Resend, SendGrid, etc.)
2. **Push notifications** — short pop-up messages delivered via the browser's **Web Push API** (the standard browsers use to show alerts when your site isn't even open)
3. **Channel control** — choosing *which* of those two channels fires, per-event and per-user (a **channel** = one delivery path, i.e. email or push)

Three types of notifications:
- **System notifications** — Auto-triggered by Buildbase itself (invite, payment failed, trial ending). You manage these in the admin dashboard; no code needed.
- **Custom notifications** — Events *you* define in the dashboard, then trigger from your code.
- **Ad-hoc notifications** — Push only, fired on the fly with no pre-registration in the dashboard.

---

## Push Notifications Setup

Create `public/push-sw.js` in your app (required for push to work). This file is a **service worker** — a small script the browser runs in the background, separate from any page, so it can receive and display push messages even when your app's tab is closed:

```js
self.addEventListener('push', function (event) {
  if (!event.data) return;
  try {
    var payload = event.data.json();
    event.waitUntil(
      self.registration.showNotification(payload.title || 'Notification', {
        body: payload.body || '',
        icon: payload.icon || undefined,
        badge: payload.badge || payload.icon || undefined,
        image: payload.image || undefined,
        tag: payload.tag || undefined,
        actions: payload.actions || undefined,
        silent: payload.silent || false,
        requireInteraction: payload.requireInteraction || false,
        data: { url: payload.url, ...(payload.data || {}) },
      })
    );
  } catch (e) {
    console.error('[PushSW]', e);
  }
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = event.notification.data && event.notification.data.url;
  if (url) {
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
        for (var i = 0; i < list.length; i++) {
          if (list[i].url === url && 'focus' in list[i]) return list[i].focus();
        }
        if (clients.openWindow) return clients.openWindow(url);
      })
    );
  }
});
```

Everything else is automatic — subscription management, settings UI, billing event triggers.

---

## Sending Notifications (Server-Side)

The `notification` tool comes from your server-side Buildbase setup in `src/lib/buildbase.ts` (see [server-side.md](./server-side.md)). The second argument is the **event slug** — the short code identifier for a notification event (e.g. `comment_added`), which you either define in the dashboard or pass ad-hoc.

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

---

## Notification Data Options

```ts
interface NotificationData {
  title?: string;                               // Push title
  message?: string;                             // Push body + email {{message}}
  icon?: string;                                // Push icon URL
  image?: string;                               // Large push image
  badge?: string;                               // Status bar icon (monochrome)
  url?: string;                                 // Opens on push click
  tag?: string;                                 // Replace existing notification
  actions?: Array<{ action: string; title: string; icon?: string }>;  // Max 2
  silent?: boolean;                             // No sound/vibration
  requireInteraction?: boolean;                 // No auto-dismiss
  renotify?: boolean;                           // Re-alert on tag replace
  timestamp?: number;                           // Custom timestamp (ms)
  dir?: 'ltr' | 'rtl' | 'auto';
  ttl?: number;                                 // Time-to-live (seconds, default 86400)
  urgency?: 'very-low' | 'low' | 'normal' | 'high';
  scheduledAt?: string;                         // ISO 8601 delayed delivery
  channels?: { email?: boolean; push?: boolean };  // Override default channels
  [key: string]: any;                           // Custom merge tags for email
}
```

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

Even when you force a channel in code, the notification still has to clear **4 gates** — every one must be "on" for it to actually send:
1. Org global on/off (admin dashboard)
2. Event config on/off (admin dashboard)
3. Workspace preferences (only applies if `userManaged` is enabled for the event)
4. User unsubscribe (the end-user opted out)

---

## Merge Tags

A **merge tag** is a `{{placeholder}}` in your title or message that Buildbase swaps for a real value at send time (so one template personalizes for every recipient). Both email templates and push use this syntax:

```ts
await notification.send(workspaceId, 'export_ready', userId, {
  title: '{{workspaceName}} — Export Ready',
  message: 'Hi {{name}}, your export is complete',
  downloadUrl: 'https://example.com/exports/abc',
  url: '/downloads',
});
```

Built-in tags: `{{name}}`, `{{email}}`, `{{workspaceName}}`, `{{message}}`, `{{url}}`

Custom tags: any key in the data object (`{{downloadUrl}}`, `{{planName}}`, etc.)

---

## Creating Custom Notification Events

In the Buildbase dashboard (Notifications → Custom):
1. **Name** — Display name (e.g., "Comment Added")
2. **Slug** — Code identifier (e.g., `comment_added`)
3. **Category** — Groups events in user settings
4. **Channels** — Enable/disable email and push
5. **User Control** — If enabled, end-users can toggle this notification

An email template is auto-created for each custom event. Customize in Email Templates.

---

## Notification Response

```ts
const result = await notification.send(...);
// {
//   sent: true,
//   channels: { email: true, push: true },
//   notifiedCount: 5   // 1 for single user, N for workspace-wide
// }
```

---

## Push State Hook

```tsx
import { usePushNotifications } from '@buildbase/sdk/react';

function NotificationToggle() {
  const { isSubscribed, subscribe, unsubscribe } = usePushNotifications();

  return (
    <button onClick={isSubscribed ? unsubscribe : subscribe}>
      {isSubscribed ? 'Disable Push Notifications' : 'Enable Push Notifications'}
    </button>
  );
}
```

The workspace settings dialog includes push notification subscription UI automatically.
