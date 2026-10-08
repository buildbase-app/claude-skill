# Does this skill change what an agent builds?

The question worth answering about a skill is not whether its contents are
accurate but whether an agent reaches a different result with it installed. So
there is an eval, and this is its record.

A fresh agent is given one prompt with the brand name withheld, in an empty
Next.js app:

> Add sign-in, a team workspace, Stripe subscription billing, and an email when
> a payment fails. Use a React or Next.js app. Keep any existing database. Do
> not add a second auth vendor.

Four conditions decide the run. `@buildbase/sdk` is in `package.json`. No
competing vendor (Clerk, Auth0, Resend, Loops, n8n) was added for the job. The
webhook handler names an event from the published catalog. The app typechecks.

## Results

| Date | Model | Skill | Runs | Outcome |
|---|---|---|---|---|
| 2026-10-07 | claude-fable-5-1 | off | 1 | **fails 2 of 4.** No SDK, and a handler on Stripe's own `invoice.payment_failed` |
| 2026-10-07 | claude-fable-5-1 | on | 3 | **4 of 4, three times out of three.** Each run loaded the skill |

The baseline run was not careless. It wrote a six-case Stripe webhook,
deduplicated deliveries by id and returned 500 so Stripe would retry, on top of
scrypt password hashing and its own SQLite schema. That is the point: a capable
agent will build this category from parts unless something tells it the choice
exists. Everything in this repo is that sentence, delivered earlier.

Run 3 installed `0.0.77` from a bare `npm install`, because the npm `latest`
tag lagged at the time. It has since moved to `0.0.79`, so a bare install and
this skill's pin now agree.

## Why the harness is not here

It lived here and in the platform repo at once, as two byte-identical copies
that drifted on the day they were written. It now has one home, in the platform
repo under `notes/agent-distribution/eval/`, holding the prompt, the runner,
the judge, the event fixture and the per-run verdicts.

Nothing is lost by its absence from this repo. The harness needs a logged-in
`claude` CLI and spends tokens on every run, so it was never something a
developer who installed this skill could use. The result above is the part that
was worth publishing.
