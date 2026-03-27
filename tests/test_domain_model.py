from datetime import UTC, datetime

import pytest

from arm64nsd.domain.errors import EmptyParsingJobError
from arm64nsd.domain.model import (
    ParserVersion,
    ParseOutcome,
    ParseStatistics,
    ParsingJob,
    SourceUnit,
    SourceUnitId,
)


def test_parsing_job_requires_at_least_one_source_unit() -> None:
    with pytest.raises(EmptyParsingJobError):
        ParsingJob(job_id="job-1", created_at=datetime.now(tz=UTC), source_units=())


def test_parsing_job_tracks_outcomes() -> None:
    source_unit = SourceUnit(
        identifier=SourceUnitId("/tmp/example.s"),
        location="/tmp/example.s",
        content="    .text\n    mov x0, #0\n    ret\n",
    )
    job = ParsingJob(
        job_id="job-1",
        created_at=datetime.now(tz=UTC),
        source_units=(source_unit,),
    )

    outcome = ParseOutcome.success(
        source_unit=source_unit,
        parser_version=ParserVersion("test"),
        diagnostics=(),
        structural_elements=(),
        statistics=ParseStatistics(
            token_count=1,
            structural_element_count=0,
            diagnostic_count=0,
            elapsed_ms=1.0,
        ),
    )

    job.record_outcome(outcome)
    job.complete(datetime.now(tz=UTC))

    assert job.succeeded_count == 1
    assert job.technical_failure_count == 0
