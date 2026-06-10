import math

import pytest

from nam_agentic.tools.services.embedding import fit_embedding_dimension


def test_fit_embedding_dimension_truncates_nomic_output() -> None:
    vector = fit_embedding_dimension([3.0, 4.0] + [0.0] * 766, target_dim=384)
    assert len(vector) == 384
    norm = math.sqrt(sum(value * value for value in vector))
    assert norm == pytest.approx(1.0)


def test_fit_embedding_dimension_passes_through_exact_match() -> None:
    vector = [0.5, 0.5, 0.5, 0.5]
    assert fit_embedding_dimension(vector, target_dim=4) == vector


def test_fit_embedding_dimension_rejects_too_short() -> None:
    with pytest.raises(ValueError, match="at least 384"):
        fit_embedding_dimension([1.0, 0.0], target_dim=384)
