import numpy as np
import pytest

from serdes_coding.models.com_model_93A import COMChannelConfig
from serdes_coding.utilities.sparam import SparamModel


def test_matched_die_terminations_derive_zero_gamma():
    cfg = COMChannelConfig(R0=46.25, R_d_tx=46.25, R_d_rx=46.25)

    assert cfg.gamma_src == 0j
    assert cfg.gamma_load == 0j


def test_mismatched_die_terminations_derive_runtime_gamma():
    cfg = COMChannelConfig(R0=50.0, R_d_tx=40.0, R_d_rx=60.0)

    assert cfg.gamma_src == pytest.approx(complex(-1.0 / 9.0))
    assert cfg.gamma_load == pytest.approx(complex(1.0 / 11.0))


def test_derived_gamma_matches_terminated_vtf_equation():
    cfg = COMChannelConfig(R0=50.0, R_d_tx=40.0, R_d_rx=60.0)
    sdd = np.asarray([
        [[0.10 + 0.02j, 0.03 - 0.01j], [0.75 - 0.08j, -0.12 + 0.04j]],
        [[0.08 + 0.01j, 0.02 - 0.02j], [0.68 - 0.11j, -0.09 + 0.03j]],
    ])
    model = SparamModel.from_sdd_array(np.asarray([1e9, 2e9]), sdd, z0=100.0)
    delta_s = sdd[:, 0, 0] * sdd[:, 1, 1] - sdd[:, 0, 1] * sdd[:, 1, 0]
    expected = (
        sdd[:, 1, 0] * (1 - cfg.gamma_src) * (1 + cfg.gamma_load)
        / (
            1
            - sdd[:, 0, 0] * cfg.gamma_src
            - sdd[:, 1, 1] * cfg.gamma_load
            + cfg.gamma_src * cfg.gamma_load * delta_s
        )
    )

    np.testing.assert_allclose(
        model.voltage_transfer_function(cfg.gamma_src, cfg.gamma_load),
        expected,
        atol=1e-12,
        rtol=0.0,
    )


@pytest.mark.parametrize("name", ["R0", "R_d_tx", "R_d_rx"])
@pytest.mark.parametrize("value", [0.0, -1.0, np.nan, np.inf])
def test_termination_resistances_must_be_finite_and_positive(name, value):
    values = {"R0": 50.0, "R_d_tx": 50.0, "R_d_rx": 50.0, name: value}

    with pytest.raises(ValueError, match=name):
        COMChannelConfig(**values)


def test_gamma_is_not_a_constructor_input():
    with pytest.raises(TypeError):
        COMChannelConfig(
            R0=50.0,
            R_d_tx=50.0,
            R_d_rx=50.0,
            gamma_src=0.0,
        )
