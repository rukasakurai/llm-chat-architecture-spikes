# Meeting Notes — Product Sync
**Date:** 2024-03-12
**Attendees:** Hana Yamamoto (PM), Kenji Ito (Engineering Lead), Priya Nair (Design), Marcus Webb (QA)
**Location:** Conference Room B / Zoom hybrid

---

## Agenda

1. Q2 roadmap review
2. Bug triage from last sprint
3. Design handoff for onboarding flow
4. QA timeline for v2.4 release

---

## Discussion

### Q2 Roadmap Review

Hana opened the meeting by summarising the three key themes for Q2: performance improvements, onboarding redesign, and API v2 migration. She noted that the API v2 migration has been pushed back one sprint due to dependencies on the authentication team.

Kenji confirmed that performance work is on track. The database query optimisations from last week reduced p95 latency by 40 ms on the user-listing endpoint. He expects the remaining cache-warming work to be done by end of week.

Priya raised a concern that the onboarding redesign scope has grown. The original spec called for three screens; stakeholder feedback has expanded it to seven. She asked for a scope decision before design tokens are finalised.

**Decision:** Hana will schedule a separate 30-minute scope meeting with the product stakeholders by Friday. Until then, design will proceed with the original three-screen scope.

### Bug Triage

Marcus walked the team through the five P1 bugs from the previous sprint:

| Bug ID | Description | Owner | Status |
|--------|-------------|-------|--------|
| BUG-441 | Login redirect loop on Safari 17 | Kenji | In progress |
| BUG-443 | Avatar upload fails for files > 2 MB | Priya | Needs design |
| BUG-447 | Email verification link expires too fast | Kenji | Fixed, in QA |
| BUG-449 | Dashboard card counts incorrect for free tier | Kenji | Root-caused |
| BUG-452 | CSV export truncates rows > 10,000 | Marcus | Workaround in place |

BUG-447 was discussed in detail. The expiry was set to 15 minutes; the fix extends it to 72 hours, matching industry standard. Marcus confirmed he can include it in the current QA cycle.

BUG-452 is a streaming issue in the export service. A full fix requires refactoring the export pipeline, which is scoped for Q3. The current workaround limits exports to 10,000 rows with a warning banner.

### Design Handoff — Onboarding Flow

Priya shared the Figma link for the first three onboarding screens. Key decisions:

- **Welcome screen:** Single call-to-action button ("Get started"), no social login on this screen.
- **Profile setup:** Name and avatar are optional at onboarding; users can skip.
- **Goal selection:** Three goal categories (Personal, Team, Enterprise); multi-select allowed.

Kenji noted that the goal selection data needs to go into the `user_preferences` table. He will add the migration script this week.

Priya will export the design tokens as a JSON file and share via Slack by Thursday.

### QA Timeline for v2.4

Marcus outlined the QA schedule:

- **Smoke tests:** March 15 (Friday)
- **Full regression:** March 18–19 (Monday–Tuesday)
- **Sign-off meeting:** March 20 (Wednesday, 2 pm)
- **Release to production:** March 21 (Thursday)

He flagged a risk: two QA engineers are on leave next week. If regression testing uncovers significant issues, the release may need to slip to March 28.

Hana accepted the risk and asked Marcus to flag any blockers by end of day Monday.

---

## Action Items

| Owner | Action | Due Date |
|-------|--------|----------|
| Hana | Schedule scope meeting with product stakeholders | March 15 |
| Kenji | Finish cache-warming work | March 15 |
| Kenji | Add `user_preferences` migration script | March 15 |
| Priya | Export design tokens as JSON | March 14 |
| Marcus | Complete QA smoke tests | March 15 |
| All | Review Figma link before next sync | March 14 |

---

## Next Meeting

**Date:** March 19, 2024
**Time:** 10:00 am JST
**Agenda:** v2.4 regression status, scope decision on onboarding redesign
