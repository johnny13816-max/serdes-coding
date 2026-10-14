import numpy as np

from serdes_coding.utilities.pmf import Pmf1D


def test_reference_atom_deposition_rounds_half_away_from_zero():
    values = np.array([-0.375, -0.125, 0.125, 0.375])
    masses = np.array([0.1, 0.2, 0.3, 0.4])
    nearest = Pmf1D.multi_dirac(values, masses, dx=0.25, placement="nearest")
    linear = Pmf1D.multi_dirac(values, masses, dx=0.25)
    np.testing.assert_array_equal(nearest.x, np.array([-0.5, -0.25, 0.0, 0.25, 0.5]))
    np.testing.assert_allclose(nearest.pmf, [0.1, 0.2, 0.0, 0.3, 0.4], rtol=0, atol=1e-15)
    assert not np.array_equal(nearest.pmf, linear.pmf)


def test_reference_fir_uses_unrounded_symbols_for_each_tap():
    symbols = np.array([-1.0, -1.0 / 3.0, 1.0 / 3.0, 1.0])
    weights = np.full(4, 0.25)
    tap = np.array([0.37])
    direct = Pmf1D.fir_filter_atoms(symbols, weights, tap, dx=0.1, keep_mass=1.0)
    expected = Pmf1D.multi_dirac(tap[0] * symbols, weights, dx=0.1, placement="nearest")
    np.testing.assert_array_equal(direct.x, expected.x)
    np.testing.assert_allclose(direct.pmf, expected.pmf, rtol=0, atol=1e-15)
    pregridded = Pmf1D.multi_dirac(symbols, weights, dx=0.1, placement="nearest")
    assert not np.array_equal(direct.pmf, pregridded.fir_filter(tap, dx_ref=0.1).pmf)


def test_reference_gaussian_and_uniform_use_distinct_construction_rules():
    sigma = 0.2
    dx = 0.1
    gaussian = Pmf1D.gaussian(0.0, sigma, dx, n_sigma=2, method="reference_sample")
    extent = round(2 * 2 * sigma / dx)
    x = np.arange(-extent, extent + 1) * dx
    expected = np.exp(-x**2 / (2 * sigma**2 + np.finfo(float).eps))
    expected /= expected.sum()
    np.testing.assert_allclose(gaussian.pmf, expected, rtol=1e-15, atol=1e-15)

    cfg = type("Grid", (), {"dy": dx})()
    uniform = Pmf1D.uniform(0.36, cfg, method="nearest_centers")
    np.testing.assert_allclose(uniform.x, np.arange(-2, 3) * dx, rtol=0, atol=1e-15)
    np.testing.assert_allclose(uniform.pmf, np.full(5, 0.2), rtol=0, atol=1e-15)
    assert not np.array_equal(uniform.pmf, Pmf1D.uniform(0.36, cfg).pmf)


def test_reference_scale_interpolates_ordinates_not_mass():
    source = Pmf1D(dx=0.1, st_idx=-2, pmf=np.array([0.1, 0.2, 0.4, 0.2, 0.1]))
    scaled = source.scale_x(1.5, keep_dx=True, method="interpolate_ordinates")
    target_x = np.arange(-3, 4) * 0.1
    expected = np.interp(target_x, source.x * 1.5, source.pmf, left=np.nan, right=np.nan)
    expected[0], expected[-1] = expected[1], expected[-2]
    expected /= expected.sum()
    np.testing.assert_allclose(scaled.x, target_x, rtol=0, atol=1e-15)
    np.testing.assert_allclose(scaled.pmf, expected, rtol=1e-15, atol=1e-15)
    assert not np.array_equal(scaled.pmf, source.scale_x(1.5, keep_dx=True).pmf)


def test_reference_quantizer_retains_noise_axis_support_before_ffe():
    noise_support = Pmf1D(dx=0.1, st_idx=-4, pmf=np.full(9, 1.0 / 9.0))
    grid = type("Grid", (), {"dy": 0.1})()
    quantizer = Pmf1D.uniform(
        0.2, grid, method="nearest_centers", support=noise_support,
    )
    assert quantizer.st_idx == noise_support.st_idx
    assert len(quantizer.pmf) == len(noise_support.pmf)
    np.testing.assert_allclose(quantizer.pmf[3:6], np.full(3, 1.0 / 3.0))
    filtered = quantizer.fir_filter(
        np.array([0.5]), keep_mass=1.0, dx_ref=0.1,
        tap_abs_th=np.nextafter(0.0, 1.0),
        scaling_method="interpolate_ordinates",
        initial_bin_range=(-4, 4),
    )
    assert filtered.st_idx == -6
    assert len(filtered.pmf) == 13
    assert np.isclose(filtered.pmf.sum(), 1.0)
