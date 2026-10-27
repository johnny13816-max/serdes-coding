from pathlib import Path

import numpy as np
import pytest

from serdes_coding.utilities.sparam import SparamModel


@pytest.mark.parametrize(
    "reader_port_order",
    [(0, 1, 2, 3), (0, 2, 1, 3), (3, 1, 2, 0), (2, 0, 3, 1)],
)
def test_synthetic_s4p_touchstone_round_trip_preserves_target_sdd(
    tmp_path: Path, reader_port_order,
):
    rng = np.random.default_rng(401)
    freqs = np.asarray([0.0, 1e9, 2e9, 3e9])
    sdd = (rng.normal(size=(4, 2, 2)) + 1j * rng.normal(size=(4, 2, 2))) * 0.1
    original = SparamModel.from_sdd_array(freqs, sdd, z0=92.5)
    expected = original.renormalized(100.0)
    synthetic = original.s2p_to_synthetic_s4p(
        target_z0_diff=100.0,
        reader_port_order=reader_port_order,
    )
    output = synthetic.write_touchstone_s4p(tmp_path / "equivalent.s4p")
    recovered = SparamModel.from_touchstone(
        output, representation="s4p", port_order=reader_port_order,
    ).s4p_to_s2p()
    assert synthetic.representation == "s4p"
    assert synthetic.source_type == "synthetic_s4p"
    np.testing.assert_allclose(recovered.sdd, expected.sdd, atol=2e-15, rtol=0)
    np.testing.assert_allclose(recovered.z0, 100.0, atol=0, rtol=0)
    np.testing.assert_allclose(synthetic.z0, 50.0, atol=0, rtol=0)
    np.testing.assert_allclose(original.z0, 92.5, atol=0, rtol=0)
    text = output.read_text(encoding="ISO-8859-1")
    assert "Synthetic differential-only S4P" in text
    assert "Sdc=Scd=Scc=0" in text


def test_synthetic_s4p_records_inverse_non_self_inverse_reader_order():
    model = SparamModel.from_sdd_array(
        np.asarray([0.0, 1e9]), np.zeros((2, 2, 2), complex), z0=100.0,
    )
    synthetic = model.s2p_to_synthetic_s4p(
        target_z0_diff=100.0,
        reader_port_order=(2, 0, 3, 1),
    )
    parameters = dict(synthetic.history[-1].parameters)
    assert parameters["reader_port_order"] == "(2, 0, 3, 1)"
    assert parameters["writer_port_order"] == "(1, 3, 0, 2)"
