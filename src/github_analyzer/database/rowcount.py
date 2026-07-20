# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""Helper for reading affected-row counts from DML statements."""

from typing import Any, cast

from sqlalchemy import CursorResult
from sqlalchemy.engine import Result


def affected_rows(result: Result[Any]) -> int:
    """Return the number of rows a DML statement affected.

    ``Session.execute`` is annotated as returning ``Result``, which has no
    ``rowcount``; for INSERT/UPDATE/DELETE it returns a ``CursorResult`` at
    runtime, which does. SQLAlchemy 2.0.51 tightened the stubs enough that
    reading ``.rowcount`` off the declared type is now an error, so the
    narrowing happens here once rather than at every call site.
    """
    return cast("CursorResult[Any]", result).rowcount
