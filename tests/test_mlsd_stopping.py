import numpy as np
import pytest

from serdes_coding.models.com_178a.config import COMNumericalControlConfig
from serdes_coding.models.com_model_178A import calculate_der_mlsd
from serdes_coding.utilities.pmf import Pmf1D


def test_stop_policy_is_independent_from_penalty():
    p = Pmf1D.gaussian(mu=0.0, sigma=1.0, dx=0.05, n_sigma=8)
    r = 0.7 ** np.arange(65)
    results = {}
    for penalty in ("fixed_length_sum", "matlab_relative_tail"):
        for stop in ("fixed_length", "relative_tail"):
            results[penalty, stop] = calculate_der_mlsd(
                p, r, L=4, As=4.0, b_lim_1=0.95, trunc_len=16,
                sequence_termination=penalty, stop_method=stop,
            )
    for penalty in ("fixed_length_sum", "matlab_relative_tail"):
        full, full_terms = results[penalty, "fixed_length"]
        early, early_terms = results[penalty, "relative_tail"]
        assert len(full_terms) == 16
        assert len(early_terms) < 16
        np.testing.assert_allclose(early_terms, full_terms[:len(early_terms)])
        assert early == pytest.approx(float(np.sum(early_terms)))
    assert results["matlab_relative_tail", "fixed_length"][0] != pytest.approx(
        np.sum(results["matlab_relative_tail", "fixed_length"][1]), rel=1e-8
    )


def test_relative_tail_caps_at_half_the_record():
    p = Pmf1D.gaussian(mu=0.0, sigma=1.0, dx=0.1, n_sigma=8)
    r = np.r_[1.0, np.zeros(7)]
    _, terms = calculate_der_mlsd(
        p, r, L=4, As=0.1, b_lim_1=0.5, trunc_len=20,
        stop_method="relative_tail",
    )
    assert len(terms) == 4
    with pytest.raises(ValueError, match="stop_method"):
        calculate_der_mlsd(p, r, L=4, As=0.1, b_lim_1=0.5, trunc_len=4, stop_method="invalid")


def test_numerical_control_defaults_and_validation():
    assert COMNumericalControlConfig().mlsd_stop_method == "fixed_length"
    with pytest.raises(ValueError, match="mlsd_stop_method"):
        COMNumericalControlConfig(mlsd_stop_method="invalid")


@pytest.mark.parametrize(
    ("trunc_len", "reference_der"),
    [(16, 1.4179897276359229e-05), (2, 7.104719185636097e-05)],
)
def test_sicopr_common_input_reference(trunc_len, reference_der):
    # SiCoPR 1.2.1 / 4p17p0: 16 stops before the penalty boundary;
    # 2 reaches the boundary and evaluates the penalty.
    p = Pmf1D.gaussian(mu=0.0, sigma=1.0, dx=0.05, n_sigma=8)
    k = np.arange(64)
    r = 0.7 ** np.minimum(k, 64 - k)
    der, terms = calculate_der_mlsd(
        p, r, L=4, As=4.0, b_lim_1=0.95, trunc_len=trunc_len,
        pmf_scaling_method="interpolate_ordinates",
        sequence_termination="matlab_relative_tail", stop_method="relative_tail",
        convolution_method="linear",
    )
    assert len(terms) == 2
    assert der == pytest.approx(reference_der, rel=1e-10, abs=2e-15)
