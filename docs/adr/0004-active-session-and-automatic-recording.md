# Architecture Decision Record: Active Session & Automatic Recording

## Title

Active Session Management with Automatic Recording

## Status

Accepted

## Date

2025-10-28

## Context

Calling `record_event(event, session_id)` from every interceptor hook was error-prone and noisy. We needed a way to keep exactly one session active and automatically persist incoming events to it.

## Decision

- Track the active session in `Recorder._active_session_id`.
- Provide `Recorder.session(...)` which yields a `SessionHandle` exposing `.session`, `.hook`, `.run()`, and `.stop_event`, ensuring start/stop happen automatically.
- Keep `create_hook()` available; it records to the active session and raises if none exists.
- Share a single SQLite connection guarded by an `RLock` so hooks invoked from executor threads can write safely.

## Rationale

- Reduces boilerplate when wiring hid-interceptor hooks.
- Enforces a single active session, avoiding ambiguous event routing.
- Maintains thread-safety without exposing concurrency details to callers.

## Implications

### Positive Implications

- Minimal caller code: create a hook once, use it across runs.
- Async helper encapsulates lifecycle and integrates with `HIDInterceptor`.
- Fail-fast behaviour when no session is active prevents silent data loss.

### Concerns

- Only one session per `Recorder` at a time → spin up multiple `Recorder` instances for parallel capture.
- Active session state is implicit → document APIs like `list_active_sessions()` for inspection.
- Long-lived hooks require vigilance → runtime error makes misuse obvious.

## Alternatives Considered

- Multiple simultaneous active sessions with hook-per-session — rejected: raises ambiguity and complicates API.
- Creating hooks on the `Session` object — rejected: would tangle data models with persistence services.
- Requiring manual `record_event` calls — rejected: too much boilerplate and easy to misuse.

## Future Direction

- Provide `get_active_session()` helper if inspection becomes common.
- Document patterns for coordinating multiple recorder instances when running in parallel.
- Monitor thread-safety requirements; introduce finer-grained locks if contention appears.

## References

- ADR 0003: Facade for Public API
- Python PEP 343 — context manager protocol
- hid-interceptor documentation
