# Architecture Decision Record: Facade for Public API

## Title

Facade for Public API (Recorder)

## Status

Accepted

## Date

2025-10-28

## Context

hid-recorder exposes several internal components (repositories, converters, database manager). Libraries consuming it should not wire these pieces individually; they only need a simple way to start, stop, and query recordings.

## Decision

- Provide a single `Recorder` facade that owns repositories and the database manager.
- Surface high-level methods (`start_session`, `record_event`, `end_session`) plus an async helper `session()` that yields a `SessionHandle` with `.hook` and `.run()`.
- Keep internal collaborators private; only `Recorder` forms the public API entry point.

## Rationale

- Simplifies the mental model for client libraries.
- Keeps internal refactors isolated from consumers.
- Supports both synchronous and asynchronous workflows consistently.

## Implications

### Positive Implications

- Callers import one class and can work in both sync and async styles.
- Internal refactors stay behind the facade boundary.
- Tests can mock `Recorder` without touching persistence layers.

### Concerns

- Advanced scenarios may need lower-level access → repositories remain importable for power users.
- Facade growth risks sprawling method sets → periodically review and split by concern if necessary.

## Alternatives Considered

- Exposing repositories and database manager directly — rejected: increases cognitive load and error risk.
- Functional API wrapping DB calls — rejected: harder lifecycle management and testing.
- Builder-style fluent API — rejected: obscures control flow and deviates from Python idioms.

## Future Direction

- Monitor facade surface area; break into sub-facades if responsibilities grow.
- Provide guidance for advanced users when direct repository access is appropriate.

## References

- Design Patterns (Gamma et al., 1994)
- Effective Python (Slatkin, 2019)
- Python PEP 343 — context manager protocol
