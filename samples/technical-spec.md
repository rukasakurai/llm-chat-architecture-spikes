# Nexus Data Platform — API v2 Technical Specification

**Version:** 2.0.0-draft
**Status:** Draft for internal review
**Author:** Kenji Ito (Engineering Lead)
**Last Updated:** 2024-03-10

---

## 1. Introduction

This document specifies the design and behaviour of Nexus Data Platform API v2. The v2 API supersedes the v1 REST API with a unified GraphQL layer, revised authentication model, improved rate limiting, and support for real-time subscriptions over WebSocket.

The primary goals of v2 are:

1. **Consistency** — All resources follow a uniform envelope format with predictable pagination and error codes.
2. **Performance** — Query complexity budgeting replaces the blunt per-request rate limit of v1.
3. **Extensibility** — A plugin architecture allows first-party and third-party integrations without forking the core schema.

This specification is intended for backend engineers implementing the API, frontend engineers consuming it, and QA engineers designing test plans.

---

## 2. Base URL and Versioning

The v2 API is available at:

```
https://api.nexusdata.io/v2/graphql
```

Legacy v1 endpoints remain at `https://api.nexusdata.io/v1/` and will be supported until **2025-06-30**, after which they will return `410 Gone`.

API versioning in v2 is handled through schema evolution (additive changes only). Breaking changes require a new major version and a minimum 12-month deprecation period.

---

## 3. Authentication

### 3.1 Bearer Tokens

All requests must include an `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens are JWTs signed with RS256. They carry the following claims:

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | User ID (UUID v4) |
| `org` | string | Organisation ID |
| `roles` | string[] | Array of role identifiers |
| `scope` | string | Space-separated OAuth 2.0 scopes |
| `exp` | number | Unix timestamp: token expiry |
| `iat` | number | Unix timestamp: token issuance |

Tokens expire after **1 hour**. Clients must use the refresh token flow to obtain a new access token without requiring the user to re-authenticate.

### 3.2 API Keys

Server-to-server integrations may use API keys instead of bearer tokens. API keys are passed in the `X-Api-Key` header:

```
X-Api-Key: ndp_live_xxxxxxxxxxxxxxxxxxxx
```

API keys are associated with a service account and carry a fixed set of scopes defined at creation time. They do not expire but can be revoked at any time from the developer console.

### 3.3 Token Refresh

Refresh tokens are valid for **30 days** and can be used once. Each use issues a new refresh token (refresh token rotation). If a refresh token is reused, the entire token family is revoked immediately.

Refresh endpoint:

```
POST https://auth.nexusdata.io/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=<token>&client_id=<client_id>
```

---

## 4. Request and Response Format

### 4.1 GraphQL Requests

All queries and mutations are sent as HTTP POST to the `/v2/graphql` endpoint:

```json
{
  "query": "query GetUser($id: ID!) { user(id: $id) { id email displayName } }",
  "variables": { "id": "user_01HXK9M2NB" },
  "operationName": "GetUser"
}
```

The `operationName` field is optional but strongly recommended for observability.

### 4.2 Response Envelope

All responses follow the standard GraphQL envelope:

```json
{
  "data": { ... },
  "errors": [ ... ],
  "extensions": {
    "requestId": "req_01HXK9M2NB",
    "complexity": 14,
    "remainingBudget": 986,
    "latencyMs": 23
  }
}
```

The `extensions` object is always present and contains observability metadata.

### 4.3 Error Format

Errors conform to the GraphQL spec with additional fields:

```json
{
  "errors": [
    {
      "message": "Resource not found",
      "locations": [{ "line": 2, "column": 3 }],
      "path": ["user"],
      "extensions": {
        "code": "NOT_FOUND",
        "httpStatus": 404,
        "requestId": "req_01HXK9M2NB"
      }
    }
  ]
}
```

Standard error codes:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHENTICATED` | 401 | Missing or invalid credentials |
| `FORBIDDEN` | 403 | Authenticated but insufficient permissions |
| `NOT_FOUND` | 404 | Requested resource does not exist |
| `VALIDATION_ERROR` | 422 | Input failed schema or business validation |
| `RATE_LIMITED` | 429 | Query complexity budget exceeded |
| `INTERNAL_ERROR` | 500 | Unexpected server-side error |

---

## 5. Rate Limiting and Query Complexity

### 5.1 Complexity Budgeting

Unlike v1's per-request rate limiting, v2 uses a **query complexity budget** computed before execution. Each field in the schema has a cost (default: 1); deeply nested or paginated fields have higher costs.

The default budget is **1000 complexity units per minute** per API key or user session. The current complexity and remaining budget are returned in every response's `extensions` object.

If a query exceeds the budget, it is rejected with a `RATE_LIMITED` error before execution begins — no partial execution occurs.

### 5.2 Introspection Queries

Schema introspection (`__schema`, `__type`) costs 50 complexity units regardless of depth. Introspection is disabled in production for API keys with the `public` scope.

### 5.3 Throttling Headers

Even when requests succeed, the following headers are returned:

```
X-Complexity-Cost: 14
X-Complexity-Remaining: 986
X-Complexity-Reset: 1710201600
```

---

## 6. Pagination

All list fields use **cursor-based pagination** (not offset/limit). The pattern is consistent across all resources:

### 6.1 Query Pattern

```graphql
query ListProjects($first: Int, $after: String) {
  projects(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        name
        createdAt
      }
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    totalCount
  }
}
```

### 6.2 Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `first` | Int | 20 | Return first N results (max 100) |
| `after` | String | null | Return results after this cursor |
| `last` | Int | — | Return last N results (max 100) |
| `before` | String | null | Return results before this cursor |

`first`/`after` and `last`/`before` are mutually exclusive. Using both raises a `VALIDATION_ERROR`.

---

## 7. Subscriptions

v2 adds real-time event subscriptions over WebSocket using the `graphql-ws` protocol.

### 7.1 Connection

```
wss://api.nexusdata.io/v2/graphql/ws
```

Authentication is passed as a connection init payload:

```json
{ "type": "connection_init", "payload": { "Authorization": "Bearer <token>" } }
```

### 7.2 Subscription Example

```graphql
subscription WatchProjectEvents($projectId: ID!) {
  projectEvents(projectId: $projectId) {
    eventType
    actor { id displayName }
    timestamp
    payload
  }
}
```

### 7.3 Event Types

| Event Type | Trigger |
|------------|---------|
| `MEMBER_JOINED` | A user joins a project |
| `MEMBER_LEFT` | A user leaves a project |
| `RESOURCE_CREATED` | A resource is created in the project |
| `RESOURCE_UPDATED` | A resource is updated |
| `RESOURCE_DELETED` | A resource is deleted |
| `INTEGRATION_TRIGGERED` | A plugin/integration fires an event |

---

## 8. Core Schema Types

### 8.1 User

```graphql
type User {
  id: ID!
  email: String!
  displayName: String!
  avatarUrl: String
  roles: [Role!]!
  organisation: Organisation!
  createdAt: DateTime!
  updatedAt: DateTime!
  preferences: UserPreferences!
}
```

### 8.2 Organisation

```graphql
type Organisation {
  id: ID!
  name: String!
  slug: String!
  plan: Plan!
  members(first: Int, after: String): UserConnection!
  projects(first: Int, after: String): ProjectConnection!
  createdAt: DateTime!
}
```

### 8.3 Project

```graphql
type Project {
  id: ID!
  name: String!
  description: String
  organisation: Organisation!
  members(first: Int, after: String): UserConnection!
  resources(first: Int, after: String, filter: ResourceFilter): ResourceConnection!
  integrations: [Integration!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}
```

---

## 9. Mutations

### 9.1 Creating a Project

```graphql
mutation CreateProject($input: CreateProjectInput!) {
  createProject(input: $input) {
    project {
      id
      name
    }
    errors {
      field
      message
    }
  }
}
```

Input:

```graphql
input CreateProjectInput {
  name: String!          # 1–100 characters
  description: String    # Optional, max 500 characters
  organisationId: ID!
}
```

### 9.2 Updating a Project

```graphql
mutation UpdateProject($id: ID!, $input: UpdateProjectInput!) {
  updateProject(id: $id, input: $input) {
    project { id name description updatedAt }
    errors { field message }
  }
}
```

### 9.3 Deleting a Project

Deletion is soft — the project moves to a `DELETED` state and is purged after 30 days.

```graphql
mutation DeleteProject($id: ID!) {
  deleteProject(id: $id) {
    success
    scheduledPurgeAt
  }
}
```

---

## 10. Plugins and Integrations

### 10.1 Plugin Architecture

Plugins extend the schema via a dedicated namespace. Each plugin registers:

- **Schema extensions**: Additional types and fields namespaced under the plugin identifier.
- **Resolvers**: Server-side functions that satisfy the extended fields.
- **Webhooks**: Outbound HTTP callbacks for asynchronous events.

Plugins are sandboxed: they cannot access data outside their registered scope.

### 10.2 Registering a Plugin

```graphql
mutation RegisterPlugin($input: RegisterPluginInput!) {
  registerPlugin(input: $input) {
    plugin {
      id
      namespace
      status
    }
  }
}
```

Input fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | ✓ | Human-readable plugin name |
| `namespace` | String | ✓ | Unique identifier (lowercase, no spaces) |
| `schemaUrl` | String | ✓ | URL serving the plugin's SDL schema fragment |
| `resolverUrl` | String | ✓ | URL of the plugin resolver service |
| `webhookUrl` | String | — | Optional webhook endpoint |
| `scopes` | [String] | ✓ | OAuth scopes the plugin requires |

---

## 11. Deprecation and Migration Guide

### v1 → v2 Migration

| v1 Concept | v2 Equivalent |
|------------|---------------|
| REST endpoints | GraphQL queries/mutations |
| `X-Auth-Token` header | `Authorization: Bearer` header |
| Offset pagination (`?page=2&limit=20`) | Cursor pagination (`first`/`after`) |
| Per-request rate limit (100 req/min) | Complexity budget (1000 units/min) |
| Polling for events | WebSocket subscriptions |

### Timeline

- **2024-04-01**: v2 enters public beta
- **2024-07-01**: v2 generally available; v1 enters deprecation
- **2025-06-30**: v1 end of life (`410 Gone`)

---

## 11b. Webhooks

### 11b.1 Overview

Webhooks provide asynchronous, outbound HTTP notifications for events that occur within the Nexus Data Platform. They are used by integrations, CI/CD pipelines, and third-party services to react to changes without polling.

Webhooks are configured per project and scoped to a set of event types. When an event fires, the platform sends an HTTP POST to the registered endpoint with a signed JSON payload.

### 11b.2 Registering a Webhook

```graphql
mutation RegisterWebhook($input: RegisterWebhookInput!) {
  registerWebhook(input: $input) {
    webhook {
      id
      url
      events
      active
      createdAt
    }
    errors { field message }
  }
}
```

Input:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `projectId` | ID | ✓ | Project the webhook is scoped to |
| `url` | String | ✓ | HTTPS endpoint to receive events |
| `events` | [String] | ✓ | List of event types to subscribe to |
| `secret` | String | — | Optional signing secret (recommended) |

All webhook URLs must use HTTPS. HTTP endpoints are rejected with a `VALIDATION_ERROR`.

### 11b.3 Payload Format

Every webhook delivery uses the following envelope:

```json
{
  "id": "evt_01HXK9M2NB",
  "type": "resource.created",
  "project_id": "proj_01HXK9M2NB",
  "timestamp": "2024-03-10T14:23:00Z",
  "data": { ... }
}
```

The `data` field contains the full resource object that was created, updated, or deleted.

### 11b.4 Signature Verification

When a signing secret is configured, the platform includes an `X-Nexus-Signature` header:

```
X-Nexus-Signature: sha256=<hex-encoded HMAC-SHA256 of raw request body>
```

Consumers should verify this signature before processing the payload to ensure authenticity.

Example (Python):

```python
import hmac, hashlib

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### 11b.5 Retry Policy

If the destination endpoint returns a non-2xx response or times out (timeout: 10 seconds), the platform retries the delivery with exponential back-off:

| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 30 seconds |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |

After five failed attempts, the event is marked as failed and the webhook is automatically deactivated. An email notification is sent to the project owner.

---

## 11c. Observability and Audit

### 11c.1 Audit Log

All mutations that modify resources are recorded in the audit log. The audit log is immutable, append-only, and retained for a minimum of 90 days (365 days on Enterprise plans).

```graphql
query AuditLog($projectId: ID!, $first: Int, $after: String) {
  auditLog(projectId: $projectId, first: $first, after: $after) {
    edges {
      node {
        id
        timestamp
        actor { id email }
        action
        resourceType
        resourceId
        changes { field before after }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

### 11c.2 Metrics and Tracing

The platform exposes operational metrics via a Prometheus-compatible `/metrics` endpoint available to service account tokens with the `metrics:read` scope.

Distributed traces use W3C Trace Context headers (`traceparent`, `tracestate`). Pass a `traceparent` header in requests to correlate platform traces with your own application telemetry.

### 11c.3 Health Checks

```
GET https://api.nexusdata.io/health
```

Returns HTTP 200 with:

```json
{ "status": "ok", "version": "2.0.0", "timestamp": "2024-03-10T14:23:00Z" }
```

A `/health/ready` endpoint additionally checks database and cache connectivity. Use `/health/live` for liveness probes and `/health/ready` for readiness probes in Kubernetes environments.

---

## 11d. SDK and Client Libraries

Official SDK libraries are maintained for the following languages:

| Language | Package | Minimum Version |
|----------|---------|-----------------|
| TypeScript / JavaScript | `@nexusdata/sdk` | Node 18+ |
| Python | `nexusdata-sdk` | Python 3.10+ |
| Go | `github.com/nexusdata/sdk-go` | Go 1.21+ |
| Java | `io.nexusdata:sdk` | Java 17+ |

All SDKs are generated from the GraphQL schema using a code-generation pipeline and are kept in sync with schema changes on a weekly cadence.

### TypeScript Example

```typescript
import { NexusClient } from "@nexusdata/sdk";

const client = new NexusClient({
  baseUrl: "https://api.nexusdata.io/v2/graphql",
  accessToken: process.env.NEXUS_ACCESS_TOKEN,
});

const { project } = await client.createProject({
  name: "My Project",
  organisationId: "org_01HXK9M2NB",
});

console.log(project.id);
```

### Python Example

```python
from nexusdata import NexusClient

client = NexusClient(
    base_url="https://api.nexusdata.io/v2/graphql",
    access_token=os.environ["NEXUS_ACCESS_TOKEN"],
)

project = client.create_project(name="My Project", organisation_id="org_01HXK9M2NB")
print(project.id)
```

---

## 11e. Testing and Quality Assurance

### 11e.1 Sandbox Environment

A dedicated sandbox environment is available for development and testing:

```
https://sandbox.api.nexusdata.io/v2/graphql
```

The sandbox:
- Uses separate data with no connection to production
- Resets to a known state every 24 hours at 00:00 UTC
- Has relaxed rate limits (10,000 complexity units per minute)
- Does not send real webhooks or emails
- Issues test tokens that are not valid in production

Obtain sandbox API keys from the developer console by selecting "Sandbox" in the environment dropdown.

### 11e.2 Test Data

The sandbox is pre-populated with the following test accounts:

| Email | Role | Description |
|-------|------|-------------|
| `admin@test.nexusdata.io` | Organisation Admin | Full admin access |
| `editor@test.nexusdata.io` | Editor | Can create/edit resources |
| `viewer@test.nexusdata.io` | Viewer | Read-only access |
| `service@test.nexusdata.io` | Service Account | API-key-only access |

Test API keys for these accounts are listed in the developer console sandbox section.

### 11e.3 Query Validation

The platform supports query validation without execution using the `X-Validate-Only: true` header. When this header is present, the request is parsed, validated against the schema, and complexity-checked, but not executed. The response indicates whether the query is valid:

```json
{
  "data": null,
  "extensions": {
    "validationResult": "VALID",
    "complexity": 14
  }
}
```

Use query validation in CI pipelines to catch schema drift before deploying new queries.

### 11e.4 Mock Mode

The GraphQL endpoint supports a mock mode (header `X-Mock-Response: true`) that returns synthetic data matching the response schema without executing resolvers. Mock mode is useful for frontend development when the backend logic is not yet ready.

---

## 11f. Security Model

### 11f.1 Transport Security

All API traffic is encrypted in transit using TLS 1.2 or later. TLS 1.0 and 1.1 are not supported. Certificate pinning is supported for mobile SDK integrations; contact support for pinning certificates.

### 11f.2 Scope-Based Access Control

All OAuth 2.0 scopes follow the pattern `resource:action`:

| Scope | Description |
|-------|-------------|
| `users:read` | Read user profiles |
| `users:write` | Create and update users |
| `projects:read` | Read project data |
| `projects:write` | Create, update, and delete projects |
| `audit:read` | Read audit log entries |
| `metrics:read` | Read operational metrics |
| `webhooks:manage` | Create, update, and delete webhooks |
| `plugins:manage` | Register and configure plugins |

Requesting unnecessary scopes is discouraged. The principle of least privilege applies: tokens should carry only the scopes needed for the intended operations.

### 11f.3 IP Allowlisting

Enterprise organisations can configure IP allowlists to restrict API access to specific IP ranges or CIDR blocks. Requests from non-allowlisted IPs receive a `403 Forbidden` response. Allowlists are managed via the organisation settings in the developer console.

### 11f.4 Data Residency

Data residency options are available on Enterprise plans:

| Region | Available |
|--------|-----------|
| EU (Frankfurt) | ✓ |
| US East (Virginia) | ✓ |
| APAC (Tokyo) | ✓ |
| US West (Oregon) | Coming 2024 Q3 |

Data residency is configured at the organisation level and applies to all data stored and processed for that organisation.

---

## 12. Changelog

| Version | Date | Summary |
|---------|------|---------|
| 2.0.0-draft | 2024-03-10 | Initial draft for internal review |

---

*For questions or feedback, open an issue in the internal `#api-v2` Slack channel or create a ticket in the Nexus Jira project under the `API-V2` epic.*
