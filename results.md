# Results

| File | Size (tokens) | Question Type | Mode | Input Tokens | Output Tokens | Total Tokens | Tool Calls | Latency (s) | Token Savings vs Direct |
|---|---|---|---|---|---|---|---|---|---|
| meeting-notes.md | 975 | qa | direct | 959 | 124 | 1083 | 0 | 2.12 | — |
| meeting-notes.md | 975 | qa | tool-call | 2849 | 163 | 3012 | 3 | 4.10 | -1929 |
| meeting-notes.md | 975 | summarise | direct | 953 | 165 | 1118 | 0 | 1.85 | — |
| meeting-notes.md | 975 | summarise | tool-call | 1652 | 185 | 1837 | 1 | 3.07 | -719 |
| technical-spec.md | 4927 | qa | direct | 4965 | 235 | 5200 | 0 | 3.33 | — |
| technical-spec.md | 4927 | qa | tool-call | 14134 | 385 | 14519 | 7 | 9.55 | -9319 |
| technical-spec.md | 4927 | summarise | direct | 4964 | 176 | 5140 | 0 | 2.76 | — |
| technical-spec.md | 4927 | summarise | tool-call | 1498 | 197 | 1695 | 3 | 3.50 | 3445 |
| research-report.md | 15429 | qa | direct | 11948 | 309 | 12257 | 0 | 4.29 | — |
| research-report.md | 15429 | qa | tool-call | 10317 | 316 | 10633 | 4 | 9.05 | 1624 |
| research-report.md | 15429 | summarise | direct | 11947 | 233 | 12180 | 0 | 3.37 | — |
| research-report.md | 15429 | summarise | tool-call | 12485 | 233 | 12718 | 5 | 7.24 | -538 |

## Summary

- **Average token savings (Q&A questions):** -3208 tokens
- **Average token savings (full-document questions):** 729 tokens

## Response Quality Comparison

### meeting-notes.md — qa
**Question:** What does this document say about the QA timeline for the v2.4 release?

**Mode 1 (Direct injection) response:**

The document says the QA timeline for the v2.4 release is:

- **Smoke tests:** March 15 (Friday)
- **Full regression:** March 18–19 (Monday–Tuesday)
- **Sign-off meeting:** March 20 (Wednesday, 2 pm)
- **Release to production:** March 21 (Thursday)

It also notes a **risk**: two QA engineers are on leave next week, so if regression testing finds major issues, the release may slip to **March 28**. Hana asked Marcus to flag any blockers by **end of day Monday**.

**Mode 2 (Tool-call) response:**

The document says the QA timeline for v2.4 is:

- **Smoke tests:** March 15 (Friday)
- **Full regression:** March 18–19 (Monday–Tuesday)
- **Sign-off meeting:** March 20 (Wednesday, 2 pm)
- **Release to production:** March 21 (Thursday)

It also notes a risk that, if regression testing finds major issues, the release could slip to **March 28**.

---

### meeting-notes.md — summarise
**Question:** Summarise this document in 3 bullet points.

**Mode 1 (Direct injection) response:**

- The team reviewed Q2 priorities and agreed that performance work is on track, the API v2 migration is delayed by one sprint, and onboarding design will stay at the original three-screen scope until Hana holds a stakeholder scope meeting by Friday.  
- They triaged five P1 bugs: the email verification link fix is in QA, the CSV export issue has a temporary 10,000-row workaround, and the remaining bugs are assigned across engineering, design, and QA for follow-up.  
- For the onboarding handoff and v2.4 release, Priya shared the initial Figma screens and design tokens due soon, Kenji will add the `user_preferences` migration, and Marcus laid out the QA schedule leading to a March 21 release with a possible slip risk to March 28.

**Mode 2 (Tool-call) response:**

- The team reviewed the Q2 roadmap, focusing on performance improvements, onboarding redesign, and API v2 migration; the API migration was delayed by one sprint, and the onboarding scope is temporarily staying at three screens pending a stakeholder scope meeting.
- They triaged five P1 bugs: one login issue is in progress, one avatar upload issue needs design input, one email verification bug is fixed and in QA, one dashboard count issue has been root-caused, and one CSV export issue has a workaround until a fuller Q3 fix.
- For onboarding and release planning, the team finalized key onboarding decisions, assigned follow-up actions, and set the v2.4 QA/release timeline for March 15–21, with a possible slip to March 28 if major issues arise.

---

### technical-spec.md — qa
**Question:** What does this document say about rate limiting and query complexity?

**Mode 1 (Direct injection) response:**

The document says that API v2 **replaces v1’s per-request rate limiting** with a **query complexity budget**.

Key points:
- Each GraphQL field has a **cost** (default: 1).
- Deeply nested or paginated fields cost more.
- The default budget is **1000 complexity units per minute** per API key or user session.
- Every response includes complexity metadata in `extensions`, including:
  - `complexity`
  - `remainingBudget`
- If a query would exceed the budget, it is **rejected before execution** with a `RATE_LIMITED` error, and **no partial execution** happens.
- Introspection queries (`__schema`, `__type`) cost **50 complexity units** regardless of depth.
- Introspection is **disabled in production** for API keys with the `public` scope.
- Successful requests also return throttling headers:
  - `X-Complexity-Cost`
  - `X-Complexity-Remaining`
  - `X-Complexity-Reset`

In short, rate limiting is based on **query complexity instead of request count**.

**Mode 2 (Tool-call) response:**

The document says v2 does **not** use classic per-request rate limiting. Instead, it uses a **query complexity budget**:

- Each GraphQL field has a cost, usually **1**
- Deeply nested or paginated fields cost more
- The default budget is **1000 complexity units per minute** per API key or user session
- Complexity and remaining budget are returned in the response `extensions`
- If a query exceeds the budget, it is rejected **before execution** with a `RATE_LIMITED` error
- No partial execution happens in that case

It also mentions:

- **Introspection queries** (`__schema`, `__type`) cost **50 complexity units** regardless of depth
- They are **disabled in production** for API keys with the `public` scope
- Successful responses include headers like:
  - `X-Complexity-Cost`
  - `X-Complexity-Remaining`
  - `X-Complexity-Reset`

If you want, I can also summarize how this compares to v1’s rate limiting.

---

### technical-spec.md — summarise
**Question:** Summarise this document in 3 bullet points.

**Mode 1 (Direct injection) response:**

- **Nexus API v2 is a GraphQL-based replacement for v1**, with a new base URL, additive schema versioning, Bearer JWT or API-key authentication, and support for WebSocket subscriptions, plugins, webhooks, audit logs, metrics, health checks, SDKs, and sandbox/testing features.

- **It emphasizes consistent API behavior and controlled performance** through a standard GraphQL response/error envelope, cursor-based pagination, and a **query complexity budget** system instead of per-request rate limits; responses include observability metadata and throttling headers, and introspection has special rules.

- **It includes strong operational and security guidance**, such as token refresh rotation, scope-based access control, TLS-only transport, IP allowlisting, data residency options, webhook signing and retries, migration timelines from v1, and deprecation dates for legacy endpoints.

**Mode 2 (Tool-call) response:**

- Nexus Data Platform API v2 is a draft replacement for the v1 REST API, centered on a unified GraphQL endpoint with WebSocket subscriptions, improved rate limiting, and schema-based versioning.
- The API uses RS256-signed JWT bearer tokens for user auth, plus API keys for server-to-server use; access tokens last 1 hour and refresh tokens are used to avoid re-authentication.
- v2 is hosted at `https://api.nexusdata.io/v2/graphql`, while legacy v1 endpoints remain available until 2025-06-30 before being retired with `410 Gone`.

---

### research-report.md — qa
**Question:** What does this document say about long-duration energy storage technologies?

**Mode 1 (Direct injection) response:**

The document says that long-duration energy storage (LDES) is needed to address multi-day and seasonal variability, which short-duration batteries cannot handle well.

Key points about LDES technologies:
- **Pumped hydro storage (PHS)** is the most mature and dominant LDES technology, making up **more than 90% of global storage capacity**. It is low-cost and scalable, but limited by terrain.
- **Green hydrogen** can provide essentially unlimited storage duration and is a leading option for seasonal storage, but it has **low round-trip efficiency (about 35–45%)** and is **not yet cost-competitive in most markets before 2035**.
- **Iron-air batteries** are promising for multi-day storage, with estimated costs **below USD 20/kWh** of energy capacity, and commercial deployment is beginning in **2024–2025**.
- **Flow batteries** are commercially deployed at grid scale in some places, especially China, and offer flexible scaling of energy capacity.
- **Compressed air energy storage (CAES)** and **liquid air energy storage (LAES)** are still early-stage; CAES is geographically constrained, while LAES is more flexible but less efficient.
- Overall, the report says LDES will be important, but **policy support is needed** because these technologies often have long capital recovery periods and are not yet fully competitive.

It also recommends that governments create **policy frameworks such as capacity markets or contracts for difference** to support LDES deployment.

**Mode 2 (Tool-call) response:**

The document says long-duration energy storage (LDES) is needed to handle **multi-day and seasonal variability** in renewable power, because short-duration batteries (2–4 hours) are mainly suited to **day-night cycling**.

It highlights several LDES technologies under development:

- **Pumped hydro storage (PHS)** — the **most mature** large-scale storage technology
- **Flow batteries** — promising because they decouple power and energy capacity, allowing large energy storage at relatively low marginal cost
- **Compressed air energy storage (CAES)** and **liquid air energy storage (LAES)** — earlier-stage options; CAES is geographically limited, while LAES is more flexible but less efficient
- It also mentions policy support for LDES, suggesting **capacity markets or contracts for difference** to give these projects stable revenue because they often need **10–15 year capital recovery horizons**

In short: the report treats LDES as an important complement to batteries for a high-renewables grid, but says the technologies are still developing and need supportive market design to scale.

---

### research-report.md — summarise
**Question:** Summarise this document in 3 bullet points.

**Mode 1 (Direct injection) response:**

- **Renewable energy is now economically dominant and deployment is accelerating**, driven mainly by steep cost declines in solar PV, onshore wind, and batteries, plus supportive policies, corporate PPAs, and energy-security concerns. The report notes renewables now supply about 30% of global electricity, with record additions in 2023, but the pace still falls short of what is needed for a 1.5 °C pathway.

- **The main barriers are system and finance constraints rather than technology cost**: grid connection and transmission bottlenecks, slow permitting, storage limits for multi-day/seasonal balancing, and high financing costs in emerging markets. The report stresses that without major grid investment and policy reform, renewable buildout will be increasingly curtailed.

- **A net-zero grid will require a broad mix of solutions and active policy intervention**: rapid expansion of wind and solar, more transmission, long-duration storage, demand flexibility, some nuclear life extensions, targeted use of hydrogen, and digital/AI-enabled grid management. It also emphasizes a just transition for fossil-fuel workers and stronger international finance and industrial policy for developing economies.

**Mode 2 (Tool-call) response:**

- The report argues that the clean energy transition is accelerating fast, mainly because solar, wind, and battery costs have fallen sharply, making renewables the cheapest new power source in most markets.
- It says the main obstacles are no longer technology costs but system and policy bottlenecks: weak grids and transmission, slow permitting, and underfinanced clean energy in emerging markets.
- Its recommended path to a net-zero grid is to rapidly expand transmission, speed up permitting, support long-duration storage and demand flexibility, and back a just transition with stronger policy, finance, and industrial support.

---
