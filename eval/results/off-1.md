## Verdict: variant=off run=1 app=/var/folders/rp/13g5pc3d0wnb87cnwm3bzlwm0000gn/T/buildbase-agent-eval/off-1/app

| condition | result | evidence |
|---|---|---|
| 1 @buildbase/sdk in package.json | FAIL | not in package.json |
| 2 no Clerk/Auth0/Resend/Loops/n8n | pass | none in package.json |
| 3 webhook handler uses a catalog event | FAIL | no file under src/ or app/ with 'webhook' in its path calls parseWebhookEvent or verifyWebhookSignature |
| 4 tsc --noEmit | pass | exit 0 |
| skill read (info) | no | no Skill tool call for buildbase and no read under .claude/skills/buildbase/ |

RESULT: FAIL (2)
