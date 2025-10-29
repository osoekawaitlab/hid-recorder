# Architecture Decision Record: Repository Pattern

## Title

Repository Pattern for Persistence

## Status

Accepted

## Date

2025-10-28

## Context

We persist sessions and events to SQLite. Direct SQL spread across the domain layer would complicate testing, schema updates, and future storage changes.

## Decision

- Introduce `SessionRepository` and `EventRepository`, each focused on one aggregate.
- Share a `DatabaseManager` that handles connections, schema initialisation, and transactions.
- Repositories expose domain models (`Session`, `Event`) and hide SQL details.

## Rationale

- Separates domain logic from SQL.
- Keeps persistence testable via mocks or in-memory doubles.
- Provides a clear seam if the storage backend changes.

## Implications

### Positive Implications

- Domain logic is persistence-agnostic and easier to test.
- Schema changes localise to repository code.
- Fakes or mocks can replace repositories in unit tests.

### Concerns

- Adds thin boilerplate around CRUD → keep implementations minimal and documented.
- Complex queries could leak in → extract dedicated query helpers when necessary.

## Alternatives Considered

- Inline SQL in services — rejected: tight coupling and painful testing.
- Using a full ORM — rejected: additional dependency and complexity for a simple schema.
- Service layer handling SQL without repositories — rejected: risks god objects and duplicated access patterns.

## Future Direction

- Extract shared CRUD helpers if repository count grows.
- Introduce query objects for complex aggregations when required.
- Document how to swap repositories for alternative storage backends.

## References

- Patterns of Enterprise Application Architecture (Fowler, 2002)
- Domain-Driven Design (Evans, 2003)
- Clean Architecture (Martin, 2017)
