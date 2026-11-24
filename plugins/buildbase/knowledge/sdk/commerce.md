# Commerce: Your Users Sell Through Your App

Commerce is for apps whose **users sell**: the people or workspaces in your app become sellers on Stripe Connect, list items, and buyers pay through your app while you take a fee on each sale. Your app can also sell its own items beside them (its own store). Stripe verifies each seller and pays them out; your app never handles identity documents, bank details or cards.

This is not how you charge for your own app. Plans, add-ons and credit packs do that: [billing.md](./billing.md), [credits.md](./credits.md). Commerce is the other direction, people selling to people inside your app.

Verified against `@buildbase/sdk` 1.9.0. The seller screens need 1.2.0 or later; co-sellers 1.4.0; account debit terms 1.5.0; booking requests, gifts, seats, the review hooks and `useSellerStats` 1.8.0; the review screens, `SellerStats`, the booking-request list, the licence-key states and `BuyButton gift`/`seats` 1.9.0. This page names the main parts and the traps. The full list of every component, hook, type and code is in the installed package: `node_modules/@buildbase/sdk/agents/react-commerce.md` (components and hooks), `agents/core-commerce.md` (types, pure helpers, API classes), `agents/server.md` (the server back office) and `docs/ERROR_CODES.md`. The docs site covers it under Billing: selling, items, item types, orders, bookings, shipping, coupons, affiliates.

## Contents

- [When to use it](#when-to-use-it) - commerce or billing
- [Two shapes: storefront or marketplace](#two-shapes-storefront-or-marketplace) - who the buyer pays
- [Console first](#console-first) - Stripe keys, Connect, the selling checklist, item types
- [Selling: onboarding a seller](#selling-onboarding-a-seller) - `SellerHome`
- [Items](#items) - what sellers list
- [Buying: checkout and BuyButton](#buying-checkout-and-buybutton) - one item, carts, guests
- [Orders and what the buyer holds](#orders-and-what-the-buyer-holds) - orders, grants, access
- [Sales, refunds and payouts](#sales-refunds-and-payouts) - the seller's side
- [Bookings](#bookings) - selling a time on a calendar
- [Files and licence keys](#files-and-licence-keys) - digital delivery
- [Subscriptions bought](#subscriptions-bought) - recurring prices sellers sell
- [Affiliates](#affiliates) - referral programs
- [Co-sellers](#co-sellers) - sharing one item's sales
- [Reviews, gifts and seats](#reviews-gifts-and-seats) - hooks (1.8.0) and screens (1.9.0)
- [Your server: the back office](#your-server-the-back-office) - `createServerClient(...).commerce`
- [Webhooks](#webhooks) - what your server is told
- [Traps](#traps) - what the SDK docs call out

## When to use it

| The user wants | Use |
|---|---|
| Their users to sell to each other (a marketplace, a storefront per seller, a booking app, downloads, courses) | Commerce, this page |
| The app itself to sell items (a one-off product, a download) beside or without sellers | Commerce, the app's own store |
| To charge for the app: tiers, seats, add-ons, usage, credits | [billing.md](./billing.md), [quota-usage.md](./quota-usage.md), [credits.md](./credits.md) |

## Two shapes: storefront or marketplace

You choose one in the console. It locks once the first seller joins, because each seller's Stripe account is created for it.

|  | Storefront | Marketplace |
|---|---|---|
| Who the buyer pays | The seller, on their own Stripe account (a direct charge) | Your app, which pays the seller out |
| Refunds and disputes | The seller's | Yours |
| Stripe's fees | The seller's, or yours if you choose | Yours |
| Carts across sellers | Paid in steps, one Stripe page per seller | One Stripe page for every seller |

**Your own store** (off until you turn it on): the app sells its own items as the seller `{ type: 'org', id: 'store' }` (`OWN_STORE_SUBJECT`), charged on your own Stripe account with no fee and no seller payout.

## Console first

1. Stripe keys under **Billing > Credentials**: test keys in a Staging environment first (Staging takes only `sk_test_` / `pk_test_`), live keys in Production when you go live.
2. Connect turned on in your Stripe account, with the platform profile complete, in the mode of your keys.
3. **Billing > Selling**: a seven-step checklist (Stripe readiness, the shape, your fee, who can sell, the Connect webhook, terms, turn on). If it says **Selling is not open for this app yet**, contact BuildBase support.
4. **Item types**: what sellers may list, their fields, benefits, checkout mode and review. Items are written against a published type.

Live keys work once live selling is open for your app; before that a buyer's checkout is refused `403 LIVE_SELLING_NOT_ALLOWED`. Turning selling off answers every new checkout `503 SELLING_UNAVAILABLE`, and what was sold keeps working.

## Selling: onboarding a seller

`SellerHome` is the whole seller flow: Start selling, Stripe's onboarding inside your app, status, documents, and payouts and balance.

```tsx
'use client';

import { SellerHome, useSaaSAuth } from '@buildbase/sdk/react';
import { loadConnectAndInitialize } from '@stripe/connect-js/pure';

export default function SellingPage() {
  const { user } = useSaaSAuth();
  return (
    <SellerHome
      subject={{ user: true }} // or a workspace id
      defaultDisplayName={user?.name}
      defaultEmail={user?.email}
      loadConnectAndInitialize={loadConnectAndInitialize}
    />
  );
}
```

- The SDK adds no Stripe dependency. Install `@stripe/connect-js` and, in Next.js, import from `@stripe/connect-js/pure` (it loads nothing during server rendering). Your CSP must allow `https://connect-js.stripe.com` and `https://js.stripe.com`.
- A seller is the signed-in person (`{ user: true }`, `/me/selling`) or a workspace (`workspace:selling:view` to read, `workspace:selling:manage` to start and change).
- `sellingAvailableFor(settings, 'user' | 'workspace')` says whether to show selling at all; the settings dialog then shows "Selling" and "Personal selling" on its own.
- Headless: `useSelling(subject)`, and `useSellerConnectComponent` to mount one of Stripe's screens in your own layout. Also `SellerTaxChoice` (when the app lets each seller choose Stripe Tax), `DebitTermsConsent` (account debit terms), `SellerStatusBadge`.
- Refusals carry a `code`: `SELLING_UNAVAILABLE`, `SELLER_COUNTRY_NOT_ALLOWED`, `SELLER_EMAIL_REQUIRED`, `SELLER_TERMINAL` (a closed seller cannot start again), `CONNECT_NOT_READY`, `SELLER_NOT_FOUND`. `sellingErrorMessage` words them.

## Items

- `<SellerItems subject={{ user: true }} />` is a seller's item list and form, drawn from the app's published item types. `ItemEditor`, `ItemStatusBadge`; headless `useItemTypes`, `useSellerItems`, `useSaveItem`, `usePublishItem`, `useSellerItem`.
- A save the type refuses throws `ITEM_INVALID` with `problems` (`{ path, code, message }`); others: `ITEM_SLUG_TAKEN`, `ITEM_LISTING_LIMIT` (402), `ITEM_STATE_CONFLICT`, `ITEM_NOT_FOUND`, `SELLER_NOT_FOUND` (start selling first).
- A type with `review: 'manual'` sends a published item to your review (`pending_review`). A sold price is retired and replaced, never edited.
- Option axes (Size, Colour): `OptionPicker` with `useOptionSelection(item)`; every variant is one combination.
- Buyers browse with `usePublishedItems({ typeKey })` and `usePublishedItem`, signed in or not.

## Buying: checkout and BuyButton

```tsx
import { BuyButton, usePublishedItems } from '@buildbase/sdk/react';

export function Shop() {
  const { items } = usePublishedItems({ typeKey: 'class' });
  return items.map((item) => {
    const variant = item.variants[0];
    const price = variant.prices[0];
    return (
      <div key={item._id}>
        {item.title}
        <BuyButton itemId={item._id} variantId={variant.id} priceId={price.id} />
      </div>
    );
  });
}
```

- `<BuyButton>` starts checkout (stock held for 30 minutes) and sends the buyer to Stripe's hosted page, back to the same page with `?checkout=success` unless `successUrl` says otherwise. A `free` price completes at once. Props cover `quantity`, `amount` (pay what you want, minor units), `slotStart` (a booking), `coupons` / `couponCode`, `buyerCountries`, `addressFirst` (carrier shipping rates), `guest`.
- `useCheckout().checkout(itemId, input)` is the same without the button: it resolves Stripe's `url` (null for a free claim) and the order, or null with `error` and `problems`.
- **Carts across sellers**: `useCart()` and `<CartSummary />`. A marketplace cart is one Stripe page; a storefront cart is paid in steps, one page per seller (`next()`).
- **Guests**, only when the app allows them (else `GUESTS_NOT_ALLOWED`): `<BuyButton guest={{ name, email }} />`, `useGuestCheckout`, then `useOrderByToken(orderLinkFromUrl())` on the order page.
- Refusals: `CHECKOUT_REFUSED` with `problems`, `OUT_OF_STOCK`, `BUY_OWN_ITEM`, `SELLER_CANNOT_SELL`, `TOO_MANY_OPEN_CHECKOUTS` (429), `LIVE_SELLING_NOT_ALLOWED` (403). `orderErrorMessage` words them.

## Orders and what the buyer holds

- `useMyOrders()`, and `useMyOrder(id, { waitForPayment: true })`, which reads an open order again until Stripe's payment lands. Amounts are minor units: format with `fmtCents`.
- What the buyer got is a **grant** per benefit of each paid line: `useHoldings({ orderId })`, with `content` only while `state` is `available` (`not_yet`, `expired`, `revoked` otherwise).
- `useHasAccess('course', courseId)` answers whether the person may use an object of your app named by an `access` benefit. **It is for the page only**: gate the object itself on your server (`commerce.grants.access` below).
- Buyer screens: `OrderTracking` (shipments), `OrderReturns`, `OrderParts` (a price paid in parts: deposit, milestones, installments), `BookingDetails`, `HoldingFiles`, `HoldingKeys`, `HoldingSubscription`.

## Sales, refunds and payouts

- `<SellerSales subject={{ user: true }} />`: each order of what they sell, what the seller receives (`sellerAmount`) and the app's fee, refunds per line, Mark as sent, shipments, returns, Export CSV. Headless `useSales`, `useRefundSale`, `useFulfilSale`, `useSalesExport`.
- A seller refunds only in the storefront shape (`sellerMayRefund`); in the marketplace the platform answers `REFUND_NOT_ALLOWED` and the app owner refunds. `REFUND_FAILED` means Stripe made no refund.
- `useSellerStats(subject, { from?, to?, bucket?, currency? })` (1.8.0) reads the seller's own figures: totals, a series, top items, currencies; minor units of one currency, never converted. Since 1.9.0 `<SellerStats subject={{ user: true }} />` draws them: sales, net, orders, average order, refunds, running subscriptions and MRR over the last 30 days or 12 months (`initialRange`), the best sellers, and a currency switch when there is more than one. ⚠️ `<SellerHome>` shows it once the seller's account is set up; `showStats={false}` keeps the 1.8.0 page.
- Shipping (`ShippingRatesEditor`, `ShipOrder`), coupons (`SellerCoupons`) and tax at checkout are seller settings too; see react-commerce.md.

## Bookings

An item type with `checkoutMode: 'booking'` sells a time on the seller's calendar.

- Buyer: `<SlotPicker itemId={item._id} value={slot} onChange={setSlot} />`, then `<BuyButton ... slotStart={slot} />`. `BookingDetails` and `useMyBookings` for cancel and move, as the item's rules allow.
- Seller: `BookingAvailabilityEditor` (inside `ItemEditor`), `SellerBookings`, `SellerCalendars` (shared calendars), `useSellerBookingActions` (with `accept` and `decline` for a booking request, 1.8.0).
- Booking requests (1.9.0): ⚠️ `<SellerBookings>` lists the requests waiting for the seller's answer above its tabs, each with its answer-by time, Accept (charges the authorised card) and Decline (asked once, with an optional reason the buyer reads). On a platform without booking requests the list is empty. `BookingStatusBadge` and `BOOKING_STATUS_DISPLAY` read `requested` and `declined`, and `BookingListQuery.status` takes them.
- Refusals: `409 SLOT_UNAVAILABLE` when the last seat went first, `422 BOOKING_CHANGE_REFUSED` with `problems[].code`, `404 BOOKING_NOT_FOUND`.

## Files and licence keys

- Files: `<SellerFiles subject={{ user: true }} seriesId="..." />` uploads and publishes releases (each file checked and scanned for malware); the buyer's `<HoldingFiles holding={h} />` asks for a link per file with `useDownloadFile`. A link works for a few minutes and counts a download: never store one.
- Licence keys: `<HoldingKeys holding={h} />` shows one key per seat; since 1.9.0 it says how many seats a seat-counted key covers (`seats`) and when the seller turned a key off (`disabled`), and a signed-in holder gives an activation back (`canRemove={false}` for a guest). The seller's own software checks a key with `new LicensesApi({ serverUrl, version: ApiVersion.V1, orgId })`: `validate`, `activate`, `deactivate`, with no session or secret, so it can ship inside a desktop app. `reason` is `not_found`, `revoked`, `expired`, `not_yet`, `limit_reached` or `not_activated`.

## Subscriptions bought

A recurring price buys the same way (Stripe's page in subscription mode). These are subscriptions a buyer holds from what sellers sell, apart from the app's own plan (`useSubscription`): `useItemSubscriptions()`, `useItemSubscriptionActions()` (cancel at period end, resume, change tier), `<HoldingSubscription subscription={s} />`; the seller's `<SellerSubscriptions />`. A holder cannot end one sooner; the seller, the app owner and your server can.

## Affiliates

`<AffiliateJoin programId={id} />`, `<AffiliateDashboard />` (links, earnings, payouts), `<SellerAffiliatePrograms subject={{ user: true }} />` for a seller's own programs. Call `captureReferral()` from `@buildbase/sdk/tracking` on landing pages: checkout, carts, `BuyButton` and `CartSummary` then send the kept referral by themselves. A program is the app owner's (every seller's items, made in the console) or a seller's (their own items, at most 3).

## Co-sellers

A seller invites another seller to share one item's sales at `shareBps` (1.4.0). Only the invitee's accept, with `consent: true`, changes the item's payees. `<CoSellerInvitations subject={{ user: true }} sellerId={seller._id} />` (received), `<ItemCoSellers subject item />` (sent, per item), `useCoSellerInvitations(subject, direction)`. An invitation answers within 14 days. `CO_SELLERS_OWNER_ONLY` (403) when the app owner keeps co-sellers to themselves.

## Reviews, gifts and seats

1.8.0 added these as hooks (headless); 1.9.0 adds the screens.

- Reviews, off until the app owner turns them on for an item type: `useItemReviews(itemId)` (published reviews and the rating, signed in only), `useOrderReviews(orderId)` (the buyer writes per line), `useSaleReviews(subject, orderId)` (the seller replies once). Show `authorName ?? t('reviews.verifiedBuyer')`.
- Review screens (1.9.0): `<ReviewList itemId={item._id} />` shows an item's published reviews with its rating on top, sorted newest, highest or lowest, a page at a time, with the seller's reply and Report (`canReport={false}` hides it); signed out it says to sign in. `<RatingSummary rating={data.rating} />` is the average, five stars and the count on its own (`variant="compact"` for a card); in `/react` the name is both the component and the `{ count, average }` type. `<ReviewForm orderId={order._id} />` is the buyer's order line by line: stars and text while a line's window is open, Edit until it closes, and why a line is closed (`REVIEW_CLOSED_KEYS`); with `seller={{ user: true }}` it shows each buyer's review with Reply (once).
- Gifts and team seats: check out with `gift: { recipientEmail, ... }` or `seats: true` on `useCheckout().checkout(itemId, input)`, or since 1.9.0 straight from the button: `<BuyButton ... gift={{ recipientEmail, recipientName?, message?, deliverAt?, hidePrice?, claimUrl? }} />` (with the button's usual `itemId`, `variantId` and `priceId`) says "Buy as a gift" and, under the button, where and when it goes; `<BuyButton ... seats quantity={5} />` says "Buy 5 seats". Neither with a booking, and not together. The recipient claims with `useGift(giftLinkFromUrl())`; a pool's lead assigns and frees seats with `useSeats`.
- Refusals: `REVIEW_NOT_FOUND`, `REVIEW_REFUSED`, `GIFT_NOT_FOUND`, `GIFT_ALREADY_CLAIMED`, `GIFT_REVOKED`, `SEAT_REFUSED`.

## Your server: the back office

`createServerClient(...).commerce` from `@buildbase/sdk/server` is your app's own server, for every seller and buyer, with an org API token whose role grants the `marketplace_*` resources it calls (`marketplace_orders`, `marketplace_refunds` for refunds, `marketplace_grants`, ...). It runs on a server only.

```ts
import { createServerClient, BuildBaseTimeoutError } from '@buildbase/sdk/server';

const bb = createServerClient({
  serverUrl: process.env.BUILDBASE_URL!,
  apiToken: process.env.BUILDBASE_API_TOKEN!, // <orgId>:<secret>, server only
});

// Gate your own object on the server, never on useHasAccess alone.
export async function canOpenCourse(userId: string, courseId: string) {
  const { hasAccess } = await bb.commerce.grants.access({ userId, resourceType: 'course', resourceId: courseId });
  return hasAccess;
}

// One key per action, kept for its retries: a refund is made once.
export async function refundOrder(orderId: string, key: string) {
  const input = { amount: 4500, reason: 'Requested by the buyer' };
  try {
    return await bb.commerce.orders.refund(orderId, input, { idempotencyKey: key });
  } catch (err) {
    // Timed out: the outcome is unknown. Retry under the SAME key, never a new one.
    if (err instanceof BuildBaseTimeoutError) return bb.commerce.orders.refund(orderId, input, { idempotencyKey: key });
    throw err;
  }
}
```

- Namespaces: `items`, `orders` (with `stats` and `export`), `subscriptions`, `bookings`, `calendars`, `affiliates`, `commissions`, `shipments`, `shippingRates`, `returns`, `shippingSettings`, `grants` (with `access`, and in 1.8.0 key rotation and seats), `licenses`, `files`, `releases`, and `buyers.state` (everything one buyer holds in one read).
- Every write sends an `Idempotency-Key` (yours, or a new one per call) and every error carries it as `err.idempotencyKey`. The SDK never retries. The same key with another body is `IdempotencyKeyReusedError` (`IDEMPOTENCY_KEY_REUSED`, **422** here, where billing writes answer 409); one still running is `IdempotencyInProgressError` (409, retry shortly with the same key). The platform remembers a key for 24 hours.
- Writes that move money (refunds, part charges, subscription cancel and change, booking cancel, shipments, return approve and refund) wait `moneyTimeoutMs` (60 s); a `BuildBaseTimeoutError` means unknown, so retry with the same key or read the order.
- As the signed-in person instead (a buyer, or a seller's own sales): `BuildBase().commerce` (`items`, `checkout`, `orders`, `holdings`, `access`, `subscriptions`, `slots`, `bookings`, `sales`, `refundSale`, ...).

## Webhooks

Your server hears commerce through the same signed webhooks as everything else ([webhooks.md](../http-api/webhooks.md)): `order.created`, `order.paid`, `order.refunded`, `order.fulfilled`, `order.disputed`, `order.part_paid`, `order.shipped`, `grant.created`, `grant.revoked`, `item_subscription.created` and the rest of `item_subscription.*`, `booking.confirmed`, `booking.requested`, `booking.cancelled`, `commission.created`, `seller.status_changed`, `license.rotated`, `grant.gifted`, `review.created` and `buyer.state_changed`. Statuses and reasons in these payloads are open unions: keep a default branch. Never invent an event name; check the catalog.

## Traps

- **`useHasAccess` is for the page only.** Gate the object on your server with `commerce.grants.access` (or `GET /api/v1/server/commerce/grants/access` with your API key).
- **Never refund under a new key after a timeout.** Retry with the key on the error, or read the order's `refunds` first.
- **Commerce and billing answer a reused key differently**: 422 here, 409 on plan and add-on writes.
- **A marketplace seller cannot refund**: `REFUND_NOT_ALLOWED`; the app owner does.
- **The shape locks** once the first seller joins. Test in Staging with test keys; sellers onboard again in live mode, because Stripe keeps test and live apart.
- **Only some benefits are delivered so far**: `message`, `link`, `access`, `manual` and `webhook_only`. Checkout refuses the others (`benefit_not_delivered`).
- **Booking times**: read slot maths from `effectiveBookingConfig(item.booking, calendar)`, never `item.booking.timeZone` (an item may sit on a shared calendar). `BookingStatus` itself does not list `requested` or `declined` (they are `BookingRequestStatus`); test a booking with `isBookingRequest(booking)`.
- **Bank debits** (ACH, SEPA) leave an order `checkout: 'open'` and unpaid for up to 14 days: wait for `order.paid`, not the return from Stripe.
- **Carrier shipping rates** must be quoted for the address before checkout (`addressFirst`, a `shippingQuote` valid 30 minutes), because Stripe's hosted page offers fixed amounts only.
- **Download links expire** in minutes and count a download: never store one.
- **Amounts are minor units** everywhere (prices, `sellerAmount`, refunds, stats): `fmtCents`, never `/ 100`.
- **Seller screens need Stripe's script**: without `loadConnectAndInitialize` a seller can start selling but is told onboarding cannot open.
