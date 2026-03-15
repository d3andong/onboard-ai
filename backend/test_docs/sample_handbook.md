# Acme Corp Employee Handbook

## Welcome to Acme Corp

Welcome to the team! This handbook contains everything you need to get started at Acme Corp. We're glad to have you on board.

## Working Hours & PTO

Our standard working hours are 9:00 AM to 5:00 PM, Monday through Friday. We offer flexible scheduling — talk to your manager about adjusting your hours if needed.

**PTO Policy:**
- Full-time employees receive 20 days of PTO per year
- PTO accrues at 1.67 days per month
- Unused PTO carries over up to a maximum of 10 days
- Please submit PTO requests at least 2 weeks in advance through BambooHR

## Engineering Team Standards

### Code Review Process
All code changes require at least one approved review before merging. For changes affecting more than 3 files, request two reviewers. Use the PR template in the repository — it includes sections for description, testing steps, and screenshots.

### Deployment Process
We deploy to production every Tuesday and Thursday at 2:00 PM MT. Feature branches should be merged to `main` by 12:00 PM on deployment days. Hotfixes can be deployed at any time with approval from the on-call engineer.

### On-Call Rotation
Engineering team members rotate on-call weekly, starting Monday at 9:00 AM. The on-call schedule is managed in PagerDuty. If you receive an alert:
1. Acknowledge within 5 minutes
2. Begin investigation within 15 minutes
3. Post status updates in #incidents every 30 minutes
4. Write a postmortem within 48 hours of resolution

## Tools & Access

### Day One Setup
Your manager will ensure you have access to the following on your first day:
- **Slack** — our primary communication tool. Join #general, #engineering, and your team channel
- **GitHub** — all code repositories. Your team lead will add you to the right orgs
- **Jira** — project management. Ask your PM for a walkthrough of current sprints
- **AWS Console** — request access through IT if your role requires it
- **BambooHR** — HR platform for PTO, benefits, and payroll

### VPN Setup
To access internal tools remotely, you'll need to set up the company VPN:
1. Download WireGuard from your app store
2. Request a VPN config file from IT (Slack #it-help)
3. Import the config into WireGuard
4. Connect before accessing any internal services

## Benefits

### Health Insurance
We offer three health plan options through Blue Cross Blue Shield:
- **Basic:** $150/month employee contribution, $2,000 deductible
- **Standard:** $250/month, $1,000 deductible
- **Premium:** $400/month, $500 deductible

Open enrollment is in November. New hires can enroll within 30 days of start date.

### 401(k)
Acme Corp matches 4% of your salary in 401(k) contributions. You're eligible after 90 days of employment. Vesting schedule is 25% per year over 4 years.

## Communication Norms

- **Slack** is for day-to-day communication. Expect responses within a few hours during work hours.
- **Email** is for external communication and formal internal announcements.
- **Meetings** should have an agenda shared at least 24 hours in advance. No-agenda, no-meeting.
- **Friday Demos** — every Friday at 3:00 PM, teams share what they shipped that week. Attendance is encouraged but optional.

## Questions?

If anything in this handbook is unclear, reach out to your manager or HR at hr@acmecorp.com. We also have a #new-hires Slack channel where you can ask anything — no question is too small!
