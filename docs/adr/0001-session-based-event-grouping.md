# Architecture Decision Record: Session-based Event Grouping

## Title

Session-based Event Grouping

## Status

Accepted

## Date

2025-10-28

## Context

hid-recorder must group HID events per run so that recordings can be started, stopped, and queried as cohesive units. Without an explicit boundary, operators would have to manage timestamps or IDs manually.

## Decision

- Introduce a `Session` aggregate identified by ULID.
- Every event belongs to exactly one session.
- Each `Recorder` maintains at most one active session (`_active_session_id`).
- Session metadata captures contextual information for later queries.

## Rationale

- Aggregate root model fits automated test runs.
- Explicit identifiers simplify retrieval and auditing.
- Mutual exclusivity prevents ambiguity about event routing.

## Implications

### Positive Implications

- Clear `start → record → end` workflow with minimal boilerplate.
- Queries, exports, and clean-up operate on well-defined session IDs.
- Foreign-key constraints ensure referential integrity.

### Concerns

- Parallel capture requires multiple `Recorder` instances.
- Crashes may leave sessions active; expose `list_active_sessions()` for recovery.
- Cascading deletes must be documented to avoid accidental data loss.

## Alternatives Considered

- Flat event table with timestamp filtering → rejected: no logical grouping.
- Tag-based grouping → rejected: error-prone and lacks lifecycle semantics.
- Time-window auto grouping → rejected: implicit boundaries break the explicit start/stop workflow.

## Future Direction

- Document multi-recorder coordination for simultaneous sessions.
- Provide utility helpers for merging or exporting sessions if requested.

## References

- Domain-Driven Design (Evans, 2003)
- Clean Architecture (Martin, 2017)
- hid-interceptor documentation
