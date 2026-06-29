# Webhooks — Verify in Any Language

Buildbase POSTs webhook events to an endpoint you host. Before trusting one, verify its signature. The SDK's `verifyWebhookSignature` / `parseWebhookEvent` do this in Node, but the algorithm is plain **HMAC-SHA256** — reproducible in any language. This recipe is extracted verbatim from `sdk/src/lib/webhook-verification.ts`.

## The algorithm

- **Headers on the incoming request:**
  - `x-buildbase-signature` — format `sha256=<hex>`
  - `x-buildbase-timestamp` — Unix epoch **in seconds** (integer)
- **Signed message:** the literal string `` `${timestamp}.${rawBody}` `` — the timestamp header value, a `.`, then the **raw request body exactly as received** (do not re-serialize parsed JSON; byte-for-byte matters).
- **MAC:** `HMAC_SHA256(key = your_webhook_secret, message = "{timestamp}.{rawBody}")`, hex-encoded (lowercase).
- **Compare:** constant-time equality between the hex from the header (after stripping `sha256=`) and your computed hex.
- **Replay window:** reject if `abs(now_seconds - timestamp) > 300` (5 minutes). Configurable; `0` disables the check.
- **Fail closed:** reject if any of signature / timestamp / secret / body is missing, the prefix is wrong, the timestamp isn't a number, it's expired, or any error occurs.

## Steps

1. Read the **raw** body (before JSON parsing) and the two headers.
2. Require `x-buildbase-signature` to start with `sha256=`; take the rest as `sig_hex`.
3. Parse the timestamp as an integer; reject if `|now - ts| > 300`.
4. Compute `expected = hmac_sha256_hex(secret, f"{ts}.{rawBody}")`.
5. Constant-time compare `sig_hex` vs `expected`. Accept only if equal.
6. Only then `JSON.parse` the body. The event shape is `{ event: string, timestamp: number, data: {...} }` — switch on `event` (e.g. `subscription.created`, `workspace.member_added`). Dedupe on the event's id if you process at-least-once.

## Python

```python
import hmac, hashlib, time

def verify_buildbase_webhook(raw_body: str, sig_header: str, ts_header: str,
                             secret: str, max_age_seconds: int = 300) -> bool:
    if not (raw_body and sig_header and ts_header and secret):
        return False
    if not sig_header.startswith("sha256="):
        return False
    sig_hex = sig_header[len("sha256="):]
    try:
        ts = int(ts_header)
    except ValueError:
        return False
    if max_age_seconds > 0 and abs(int(time.time()) - ts) > max_age_seconds:
        return False
    expected = hmac.new(secret.encode(), f"{ts_header}.{raw_body}".encode(),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig_hex, expected)
```

Use the raw `ts_header` string in the signed message (not a reformatted int).

## Go

```go
import ("crypto/hmac"; "crypto/sha256"; "encoding/hex"; "strconv"; "strings"; "time")

func VerifyBuildbaseWebhook(rawBody, sigHeader, tsHeader, secret string, maxAge int64) bool {
    if rawBody == "" || sigHeader == "" || tsHeader == "" || secret == "" {
        return false
    }
    if !strings.HasPrefix(sigHeader, "sha256=") {
        return false
    }
    sigHex := strings.TrimPrefix(sigHeader, "sha256=")
    ts, err := strconv.ParseInt(tsHeader, 10, 64)
    if err != nil {
        return false
    }
    if maxAge > 0 {
        if d := time.Now().Unix() - ts; d > maxAge || -d > maxAge {
            return false
        }
    }
    mac := hmac.New(sha256.New, []byte(secret))
    mac.Write([]byte(tsHeader + "." + rawBody))
    expected := hex.EncodeToString(mac.Sum(nil))
    return hmac.Equal([]byte(sigHex), []byte(expected))
}
```

## Node (the SDK already does this)

In Node you can just use the SDK: `parseWebhookEvent({ body, signature, timestamp, secret })` returns the parsed event or `null`. See `knowledge/sdk/server-side.md`.
