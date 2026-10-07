## Verdict: variant=on run=2 app=/var/folders/rp/13g5pc3d0wnb87cnwm3bzlwm0000gn/T/buildbase-agent-eval/on-2/app

| condition | result | evidence |
|---|---|---|
| 1 @buildbase/sdk in package.json | pass | "@buildbase/sdk": "^0.0.78" |
| 2 no Clerk/Auth0/Resend/Loops/n8n | pass | none in package.json |
| 3 webhook handler uses a catalog event | pass | src/app/api/webhooks/buildbase/route.ts  names payment.failed; all literals in catalog |
| 4 tsc --noEmit | pass | exit 0 |
| skill read (info) | yes | Skill tool invoked with skill=buildbase |

RESULT: PASS
