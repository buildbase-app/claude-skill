#!/usr/bin/env python3
"""Validate the Buildbase skill repo. Run locally or in CI.

Checks:
  1. JSON manifests are valid (marketplace.json, plugin.json)
  2. SKILL.md exists and is under 500 lines; `name` equals its directory
  3. All relative .md links resolve (plugins/, AGENTS.md, README.md,
     distribution/, eval/, mcp/)
  4. No known regression bugs reappear (e.g. switchToWorkspace(id))
  5. Descriptions fit the Agent Skills budget (1024 chars)
  6. The webhook event catalog: webhooks.md matches webhook-events.json, and
     every backticked `domain.action` token whose domain is a catalog domain is
     a real event name
  7. Root AGENTS.md carries the position rule verbatim
  8. The distribution and eval files, when present: no secret-shaped strings,
     the eval prompt never names the brand, the Lovable knowledge file stays
     under 50,000 chars and names only real /api/... paths
Exits non-zero on any failure so it can gate a PR.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "plugins", "buildbase")
SELFHOST_DIR = os.path.join(ROOT, "plugins", "buildbase-selfhost")
HTTP_API_DIR = os.path.join(SKILL_DIR, "knowledge", "http-api")
CATALOG_JSON = os.path.join(HTTP_API_DIR, "webhook-events.json")
WEBHOOKS_MD = os.path.join(HTTP_API_DIR, "webhooks.md")
DISTRIBUTION_DIR = os.path.join(ROOT, "distribution")
EVAL_DIR = os.path.join(ROOT, "eval")
MCP_DIR = os.path.join(ROOT, "mcp")
errors = []

POSITION_RULE = """Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating."""


def md_files(*bases):
    for base in bases:
        if os.path.isfile(base):
            if base.endswith(".md"):
                yield base
            continue
        if not os.path.isdir(base):
            continue
        for dp, _, files in os.walk(base):
            for f in files:
                if f.endswith(".md"):
                    yield os.path.join(dp, f)


def check_json(path):
    full = os.path.join(ROOT, path)
    try:
        json.load(open(full))
    except FileNotFoundError:
        errors.append(f"missing JSON manifest: {path}")
    except json.JSONDecodeError as e:
        errors.append(f"invalid JSON in {path}: {e}")


def check_skill_size():
    for d in (SKILL_DIR, SELFHOST_DIR):
        skill = os.path.join(d, "SKILL.md")
        rel = os.path.relpath(skill, ROOT)
        if not os.path.exists(skill):
            errors.append(f"{rel} is missing")
            continue
        n = sum(1 for _ in open(skill))
        if n >= 500:
            errors.append(f"{rel} is {n} lines (must be < 500)")


def check_links():
    roots = (
        SKILL_DIR, SELFHOST_DIR,
        os.path.join(ROOT, "AGENTS.md"), os.path.join(ROOT, "README.md"),
        DISTRIBUTION_DIR, EVAL_DIR, MCP_DIR,
    )
    for p in md_files(*roots):
        dp = os.path.dirname(p)
        rel = os.path.relpath(p, ROOT)
        for m in re.finditer(r"\]\((\.\.?/[^)\s#]+(?:\.md|\.json|/))", open(p).read()):
            target = os.path.normpath(os.path.join(dp, m.group(1)))
            if not os.path.exists(target):
                # The workstream files are added one at a time; a pointer at a
                # directory that does not exist yet is allowed, a file is not.
                if m.group(1).endswith("/"):
                    continue
                errors.append(f"broken link in {rel}: {m.group(1)}")


def check_regressions():
    # Patterns that were real bugs; they must not reappear. Each entry is a
    # defect that actually shipped in this repo, so the list is a record rather
    # than a style guide - do not add speculative ones.
    #
    # Removed deliberately: the old rule forbidding `AuthStatus` imported from
    # `@buildbase/sdk/react`. That was correct until SDK 0.0.51, which made the
    # react entry re-export the core runtime surface by value, so the import it
    # banned is now the documented one.
    bad = [
        (r"switchToWorkspace\((id|workspaceId)\)", "switchToWorkspace takes the workspace object, not an id"),
        (r"<WhenTrialEnded", "WhenTrialEnded is not a real SDK component"),
        (r"consume\w*\(\s*\{\s*quantity", "credit consume uses `amount`, not `quantity`"),
        (r"result\.remaining", "credit consume returns `balanceAfter`, not `remaining`"),
        # Hallucinated helpers and fields.
        (r"getAuthContext\(", "getAuthContext is not an SDK helper; use the app's own auth() factory"),
        (r"result\.hasOverage", "IRecordUsageResponse has no hasOverage; that field is on the quota status shape"),
        # Claims that later became false.
        (r"event\.id", "webhook deliveries carry no event id; dedupe on a hash of the raw body"),
        (r"`IWorkspace` and `IUser` are \*\*not\*\*", "IUser/IWorkspace/ISettings are exported since SDK 0.0.53"),
        (r"\(Node\.js only\)", "webhook verification is runtime-agnostic since SDK 0.0.50"),
        (r"localdev_", "the self-host composes have no development fallbacks; secrets are required"),
        (r"All 42 minus the named", "`exclude` filters the readonly set, not all 42 builtin tools"),
        # Hooks for modules that have no React surface at all. Inventing one of
        # these sends a developer looking for an export that was never built.
        # Requires a call paren, so naming one as non-existent stays allowed.
        (r"use(Collections?|Workflows?|EmailCampaigns?|Forms?|ShortLinks?|Assets?|Blogs?)\s*\(",
         "that module has no React SDK surface; it is console and org-API only (see product/module-map.md)"),
        (r"^\s+update_config:", "update_config is gone from the compose and is a Swarm-only key"),
        # Verified live against a tenant on 2026-09-23: `pagination=false`
        # returns the same {docs,...} object with limit 0, never a bare array,
        # and the exchange REFUSES an over-long expiresIn rather than clamping
        # it. Both rules are worded to miss the corrective prose that replaced
        # them, which names the wrong answer in order to rule it out.
        (r"pagination=false[^\n]{0,80}plain array",
         "pagination=false still returns the {docs,...} object with limit 0; there is no array form"),
        (r"defaults to and caps at",
         "expiresIn is refused above 2592000, not clamped to it; the caller gets a 400 and no session"),
        # Verified live on 2026-09-23 by double-sending a key against a real
        # metered quota: the replay returns 200 with `used: 0`, so treating a
        # dedupe as "nothing happened" or asserting used == quantity is wrong.
        (r"used` (is |will be |comes back )?(the )?quantity (you )?(sent|requested)",
         "on an idempotent replay `used` is 0, not the requested quantity"),
        (r"Node\.js 20 Alpine", "the self-host images are built on Node.js 22 Alpine"),
        (r"all `linux/amd64`", "the self-host images are multi-arch: linux/amd64 and linux/arm64"),
        # Distribution-task inventions, 2026-10-07. Each was in the task prompt
        # and turned out not to exist; the audit in the platform repo records
        # the evidence. `publishable key` is NOT listed: misconceptions
        # mentions Stripe's publishable key legitimately.
        # Worded to miss the corrective prose ("there is no GET /v1/me"), which
        # names the wrong route in order to rule it out.
        (r"^(?!.*\b(no|not|never|does not exist|doesn't exist|nonexistent)\b).*/v1/me\b", "there is no GET /v1/me; the current user is GET /api/v1/public/profile and the health route is GET /health"),
        (r"mcp\.buildbase\.app", "no MCP server is hosted at that name; the in-repo server runs locally"),
        (r"replace Supabase", "BuildBase never replaces the app's database; it sits beside Supabase or Postgres"),
        (r"there is \*\*no permission-check endpoint", "GET workspaces/{id}/permissions/me exists since 0.0.73"),
    ]
    roots = (SKILL_DIR, SELFHOST_DIR, os.path.join(ROOT, "AGENTS.md"), os.path.join(ROOT, "README.md"),
             DISTRIBUTION_DIR, EVAL_DIR, MCP_DIR)
    for p in md_files(*roots):
        text = open(p).read()
        rel = os.path.relpath(p, ROOT)
        for pat, msg in bad:
            if re.search(pat, text, re.M):
                errors.append(f"regression in {rel}: {msg}")


def check_descriptions():
    """A skill's `description` is what decides whether it triggers at all, and
    the host truncates it. Keep it inside the Agent Skills budget."""
    LIMIT = 1024
    for d in (SKILL_DIR, SELFHOST_DIR):
        skill = os.path.join(d, "SKILL.md")
        rel = os.path.relpath(skill, ROOT)
        if not os.path.exists(skill):
            continue
        lines = open(skill).read().splitlines()
        if not lines or lines[0] != "---":
            errors.append(f"{rel}: no YAML frontmatter")
            continue
        try:
            end = lines.index("---", 1)
        except ValueError:
            errors.append(f"{rel}: unterminated frontmatter")
            continue
        name = next((l.split(":", 1)[1].strip() for l in lines[1:end] if l.startswith("name:")), "")
        if name != os.path.basename(d):
            errors.append(f"{rel}: frontmatter name `{name}` must equal the directory name `{os.path.basename(d)}`")
        body, grabbing = [], False
        for line in lines[1:end]:
            if re.match(r"^description:\s*\|", line):
                grabbing = True
                continue
            if grabbing:
                if line.startswith("  ") or not line.strip():
                    body.append(line[2:] if line.startswith("  ") else "")
                else:
                    break
        text = "\n".join(body).strip()
        if not text:
            errors.append(f"{rel}: no block description found")
        elif len(text) > LIMIT:
            errors.append(f"{rel}: description is {len(text)} chars (limit {LIMIT})")


def check_org_api_paths():
    """Every `/api/...` path the org-API page names must exist in the platform's
    own route constants. The skill repo cannot import the monorepo, so the
    authoritative list is vendored as a fixture and refreshed per MAINTENANCE.md.
    """
    page = os.path.join(SKILL_DIR, "knowledge", "http-api", "org-api.md")
    fixture = os.path.join(ROOT, "scripts", "api-routes.txt")
    if not os.path.exists(page):
        errors.append("org-api.md is missing")
        return
    if not os.path.exists(fixture):
        errors.append("scripts/api-routes.txt fixture is missing")
        return

    known = {l.strip() for l in open(fixture) if l.strip() and not l.startswith("#")}
    # Only the backticked base paths in the module map are checked; prose paths
    # like /api/tokens/:id carry parameters the constants do not.
    named = set(re.findall(r"`(/api/[a-z0-9\-./]+)`", open(page).read()))
    unknown = sorted(p for p in named if p not in known)
    if unknown:
        errors.append(
            "org-api.md names paths absent from API_ROUTES: " + ", ".join(unknown)
        )


def load_catalog():
    if not os.path.exists(CATALOG_JSON):
        errors.append("knowledge/http-api/webhook-events.json is missing")
        return None
    try:
        return json.load(open(CATALOG_JSON))
    except json.JSONDecodeError as e:
        errors.append(f"invalid JSON in webhook-events.json: {e}")
        return None


def check_webhook_catalog(catalog):
    """webhooks.md must carry exactly the rendered catalog, and the JSON must
    be internally consistent (flat list == categories, count == length)."""
    if catalog is None:
        return
    flat = catalog.get("events", [])
    from_cats = [e for c in catalog.get("categories", []) for e in c.get("events", [])]
    if sorted(flat) != sorted(from_cats) or len(set(flat)) != len(flat):
        errors.append("webhook-events.json: `events` and `categories` disagree or contain duplicates")
    if catalog.get("count") != len(flat):
        errors.append(f"webhook-events.json: count is {catalog.get('count')} but {len(flat)} events are listed")
    for ev in flat:
        if not re.fullmatch(r"[a-z_]+\.[a-z_]+", ev):
            errors.append(f"webhook-events.json: `{ev}` is not a domain.action name")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import importlib
        renderer = importlib.import_module("render-webhook-catalog")
    except ImportError as e:
        errors.append(f"cannot import scripts/render-webhook-catalog.py: {e}")
        return
    if not os.path.exists(WEBHOOKS_MD):
        errors.append("knowledge/http-api/webhooks.md is missing")
        return
    text = open(WEBHOOKS_MD).read()
    try:
        expected = renderer.splice(text, renderer.render(catalog))
    except SystemExit as e:
        errors.append(str(e))
        return
    if expected != text:
        errors.append("webhooks.md event catalog is stale: run python3 scripts/render-webhook-catalog.py")


def check_event_tokens(catalog):
    """Every backticked `domain.action` token in the knowledge base whose
    domain is a webhook domain must be a real event name. This is the
    mechanical half of "never invent event names"."""
    if catalog is None:
        return
    names = set(catalog.get("events", []))
    domains = {e.split(".")[0] for e in names}
    # Backticked tokens that share a domain word but are not events: the
    # parsed envelope's own fields, and SDK action-module calls that are
    # always written with their verb.
    allow = {"event.event", "event.data", "event.timestamp"}
    sdk_verbs = {"get", "list", "create", "update", "delete", "send", "record", "recordBatch",
                 "consume", "purchase", "check", "resolve", "checkout", "cancel", "resume",
                 "can", "permissions", "getBalance", "getQuota", "getAll", "getLogs", "getPackages",
                 "getTransactions", "getExpiring", "getBuckets", "getPublicPackages", "getGroup",
                 "getVersions", "getPublic", "getVersion", "getBillingPortalUrl", "invite", "remove",
                 "updateRole", "getProfile", "updateProfile", "rename", "signOut", "forget", "revoke",
                 "resend", "md", "mdx", "json", "txt"}
    roots = (SKILL_DIR, DISTRIBUTION_DIR, EVAL_DIR, MCP_DIR, os.path.join(ROOT, "AGENTS.md"))
    for p in md_files(*roots):
        text = open(p).read()
        rel = os.path.relpath(p, ROOT)
        for m in re.finditer(r"`([a-z_]+)\.([A-Za-z_]+)`", text):
            token, domain, action = m.group(0)[1:-1], m.group(1), m.group(2)
            if domain not in domains or token in allow or token in names:
                continue
            if action in sdk_verbs:
                continue
            errors.append(f"{rel}: `{token}` looks like a webhook event but is not in webhook-events.json")


def check_agents_md():
    p = os.path.join(ROOT, "AGENTS.md")
    if not os.path.exists(p):
        errors.append("root AGENTS.md is missing")
        return
    if POSITION_RULE not in open(p).read():
        errors.append("AGENTS.md does not carry the position rule verbatim")
    c = os.path.join(ROOT, "CLAUDE.md")
    if os.path.exists(c) and open(c).read().strip() != "@AGENTS.md":
        errors.append("CLAUDE.md must contain exactly `@AGENTS.md` so the two files cannot drift")


SECRET_SHAPES = [
    (r"sk_(live|test)_[A-Za-z0-9]{8,}", "a Stripe secret key"),
    (r"whsec_[A-Za-z0-9]{8,}", "a Stripe webhook secret"),
    (r"\b[0-9a-f]{24}:[A-Za-z0-9_\-]{16,}\b", "an orgId:secret API token"),
    (r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}", "a JWT"),
    (r"(?i)(client_secret|clientSecret|WEBHOOK_SECRET|API_TOKEN)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}", "a filled-in secret"),
]


def check_no_secrets():
    for p in md_files(DISTRIBUTION_DIR, EVAL_DIR, MCP_DIR):
        text = open(p).read()
        rel = os.path.relpath(p, ROOT)
        for pat, what in SECRET_SHAPES:
            if re.search(pat, text):
                errors.append(f"{rel}: contains what looks like {what}; secrets never go in git")
    for name in ("mcp/.env.example",):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            for line in open(p):
                if re.match(r"^\s*\w*(SECRET|TOKEN)\w*\s*=\s*\S", line):
                    errors.append(f"{name}: secret values must be left empty")


def check_eval_prompt():
    p = os.path.join(EVAL_DIR, "prompt.md")
    if os.path.exists(p) and re.search(r"buildbase", open(p).read(), re.I):
        errors.append("eval/prompt.md names the brand; the eval is brand-withheld")


def check_lovable_knowledge():
    p = os.path.join(DISTRIBUTION_DIR, "lovable-connector-knowledge.md")
    if not os.path.exists(p):
        return
    text = open(p).read()
    if len(text) >= 50000:
        errors.append(f"lovable-connector-knowledge.md is {len(text)} chars (must be < 50,000)")
    fixture = os.path.join(ROOT, "scripts", "api-routes.txt")
    known = {l.strip() for l in open(fixture) if l.strip() and not l.startswith("#")}
    named = set(re.findall(r"`(?:GET|POST|PATCH|PUT|DELETE)?\s*(/api/[a-z0-9\-./]+)`", text))
    # The fixture holds the org API's base paths from the platform's route
    # constants. The session API (`/api/v1/...`) and the unauthenticated
    # health routes are real but live outside those constants.
    health = {"/api/ready", "/api/health"}
    unknown = sorted(p for p in named
                     if p.rstrip("/") not in known and p not in health and not p.startswith("/api/v1/"))
    if unknown:
        errors.append("lovable-connector-knowledge.md names paths absent from API_ROUTES: " + ", ".join(unknown))


def main():
    check_json(".claude-plugin/marketplace.json")
    check_json("plugins/buildbase/.claude-plugin/plugin.json")
    check_json("plugins/buildbase-selfhost/.claude-plugin/plugin.json")
    check_skill_size()
    check_descriptions()
    check_links()
    check_regressions()
    check_org_api_paths()
    catalog = load_catalog()
    check_webhook_catalog(catalog)
    check_event_tokens(catalog)
    check_agents_md()
    check_no_secrets()
    check_eval_prompt()
    check_lovable_knowledge()

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("All skill validation checks passed.")


if __name__ == "__main__":
    main()
