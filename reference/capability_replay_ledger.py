"""SQLite transaction reference for reserving non-replayable capability requests.

Development-only. This never executes tools. The backend must establish trusted
authority for AuthorizedRoute, own the database connection, configure durable
storage, monitor faults, enforce retention, and reauthorize at the effect boundary.
Do not use an in-memory SQLite database for real actions.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from reference.capability_authorization import AuthorizedRoute

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_FINAL = frozenset({"succeeded", "failed", "unknown"})


class ReplayError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Reservation:
    """Not a token or live execution permit. Never expose this to model output."""
    key_hash: str
    request_hash: str


def _fingerprints(plan: AuthorizedRoute) -> tuple[str, str]:
    # The database stores no raw request IDs, subjects, resource paths, or args.
    identity = json.dumps([plan.tenant, plan.request_id], ensure_ascii=True,
                          separators=(",", ":"))
    context = json.dumps([
        plan.tenant, plan.subject, plan.session, plan.request_id,
        plan.service, plan.operation, plan.resource, plan.arguments_sha256,
        plan.risk, plan.policy_revision, plan.requirement_revision,
        plan.route.service, plan.route.operation, plan.route.transport,
        plan.route.connection_id,
    ], ensure_ascii=True, separators=(",", ":"))
    return (hashlib.sha256(identity.encode("utf-8")).hexdigest(),
            hashlib.sha256(context.encode("utf-8")).hexdigest())


class ReplayLedger:
    """Rejects repeated request IDs, even after a failed or unknown outcome.

    Separate processes can use the same durable SQLite file with BEGIN IMMEDIATE.
    This is a reference, not a production replay or exactly-once guarantee.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        if type(connection) is not sqlite3.Connection:
            raise ReplayError("invalid_store")
        self._connection = connection
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS capability_request_reservations (
                    key_hash TEXT PRIMARY KEY NOT NULL,
                    request_hash TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN (
                        'reserved', 'succeeded', 'failed', 'unknown')),
                    reserved_at INTEGER NOT NULL,
                    resolved_at INTEGER
                )
            """)
            connection.commit()
        except sqlite3.Error as exc:
            raise ReplayError("ledger_unavailable") from exc

    @staticmethod
    def _clock(now: object) -> None:
        if type(now) is not int or not 0 <= now <= 253402300799:
            raise ReplayError("invalid_clock")

    def reserve(self, plan: AuthorizedRoute, *, now: int) -> Reservation:
        """Atomically reserve one authenticated request before any side effect.

        This does not grant permission to act. On a database error, fail closed.
        If execution outcome becomes ambiguous, retain the reservation.
        """
        if type(plan) is not AuthorizedRoute:
            raise ReplayError("invalid_plan")
        self._clock(now)
        try:
            key, fingerprint = _fingerprints(plan)
            if not _DIGEST.fullmatch(key) or not _DIGEST.fullmatch(fingerprint):
                raise ReplayError("invalid_plan")
        except (TypeError, ValueError, UnicodeError, AttributeError) as exc:
            raise ReplayError("invalid_plan") from exc
        conn = self._connection
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO capability_request_reservations "
                "(key_hash, request_hash, state, reserved_at) "
                "VALUES (?, ?, 'reserved', ?)",
                (key, fingerprint, now),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ReplayError("replay_detected") from exc
        except sqlite3.Error as exc:
            conn.rollback()
            raise ReplayError("ledger_unavailable") from exc
        return Reservation(key, fingerprint)

    def resolve(self, reservation: Reservation, *, outcome: str, now: int) -> None:
        """Record one terminal outcome; uncertain outcomes must not be retried."""
        if (type(reservation) is not Reservation
                or any(type(value) is not str or _DIGEST.fullmatch(value) is None
                       for value in (reservation.key_hash, reservation.request_hash))):
            raise ReplayError("invalid_reservation")
        if type(outcome) is not str or outcome not in _FINAL:
            raise ReplayError("invalid_outcome")
        self._clock(now)
        conn = self._connection
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT state, reserved_at, request_hash "
                "FROM capability_request_reservations WHERE key_hash = ?",
                (reservation.key_hash,),
            ).fetchone()
            if (row is None or row[0] != "reserved"
                    or row[2] != reservation.request_hash or now < row[1]):
                conn.rollback()
                raise ReplayError("reservation_unavailable")
            affected = conn.execute(
                "UPDATE capability_request_reservations "
                "SET state = ?, resolved_at = ? "
                "WHERE key_hash = ? AND request_hash = ? AND state = 'reserved'",
                (outcome, now, reservation.key_hash, reservation.request_hash),
            ).rowcount
            if affected != 1:
                conn.rollback()
                raise ReplayError("reservation_unavailable")
            conn.commit()
        except ReplayError:
            raise
        except sqlite3.Error as exc:
            conn.rollback()
            raise ReplayError("ledger_unavailable") from exc

    def status(self, reservation: Reservation) -> str:
        if (type(reservation) is not Reservation
                or any(type(value) is not str or _DIGEST.fullmatch(value) is None
                       for value in (reservation.key_hash, reservation.request_hash))):
            raise ReplayError("invalid_reservation")
        try:
            row = self._connection.execute(
                "SELECT state FROM capability_request_reservations "
                "WHERE key_hash = ? AND request_hash = ?",
                (reservation.key_hash, reservation.request_hash),
            ).fetchone()
        except sqlite3.Error as exc:
            raise ReplayError("ledger_unavailable") from exc
        if row is None:
            raise ReplayError("reservation_unavailable")
        return row[0]

    def was_reserved(self, *, tenant: str, request_id: str) -> bool:
        """Advisory duplicate precheck; never a substitute for atomic reserve.

        A negative result can become stale at once. Call reserve() after fresh
        authorization even when this returns False. This is no execution grant.
        """
        identifier = re.compile(r"^[a-z][a-z0-9_.:-]{0,127}$")
        if (type(tenant) is not str or identifier.fullmatch(tenant) is None
                or type(request_id) is not str
                or identifier.fullmatch(request_id) is None):
            raise ReplayError("invalid_request")
        raw = json.dumps([tenant, request_id], ensure_ascii=True,
                         separators=(",", ":")).encode("utf-8")
        key = hashlib.sha256(raw).hexdigest()
        try:
            row = self._connection.execute(
                "SELECT 1 FROM capability_request_reservations WHERE key_hash = ?",
                (key,),
            ).fetchone()
        except sqlite3.Error as exc:
            raise ReplayError("ledger_unavailable") from exc
        return row is not None
