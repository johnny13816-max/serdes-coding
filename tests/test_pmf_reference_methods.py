import numpy as np
import pytest

from serdes_coding.utilities.pmf import Pmf1D


def test_reference_atom_deposition_rounds_half_away_from_zero():
    values = np.array([-0.375, -0.125, 0.125, 0.375])
    masses = np.array([0.1, 0.2, 0.3, 0.4])
    nearest = Pmf1D.multi_dirac(
        values, masses, dx=0.25, projection_method="nearest",
    )
    linear = Pmf1D.multi_dirac(values, masses, dx=0.25)
    np.testing.assert_array_equal(nearest.x, np.array([-0.5, -0.25, 0.0, 0.25, 0.5]))
    np.testing.assert_allclose(nearest.pmf, [0.1, 0.2, 0.0, 0.3, 0.4], rtol=0, atol=1e-15)
    assert not np.array_equal(nearest.pmf, linear.pmf)


def test_reference_fir_uses_unrounded_symbols_for_each_tap():
    symbols = np.array([-1.0, -1.0 / 3.0, 1.0 / 3.0, 1.0])
    weights = np.full(4, 0.25)
    tap = np.array([0.8])
    source = Pmf1D.multi_dirac(
        symbols, weights, dx=1.0 / 3.0,
    )
    direct = source.fir_filter(
        tap, dx_ref=0.1, keep_mass=1.0, projection_method="nearest",
    )
    expected = Pmf1D.multi_dirac(
        tap[0] * symbols, weights, dx=0.1, projection_method="nearest",
    )
    np.testing.assert_array_equal(direct.x, expected.x)
    np.testing.assert_allclose(direct.pmf, expected.pmf, rtol=0, atol=1e-15)
    pregridded = Pmf1D.multi_dirac(
        symbols, weights, dx=0.1, projection_method="nearest",
    )
    assert not np.array_equal(
        direct.pmf,
        pregridded.fir_filter(
            tap, dx_ref=0.1, projection_method="nearest",
        ).pmf,
    )


def test_pmf_projection_method_is_operation_level_only():
    source = Pmf1D.multi_dirac(np.array([-1.0, 1.0]), dx=1.0)
    nearest = source.resample_dx(0.3, projection_method="nearest")
    linear = source.resample_dx(0.3, projection_method="linear")

    assert not hasattr(source, "placement")
    assert not np.array_equal(nearest.pmf, linear.pmf)
    combined = nearest.combine(linear)
    assert np.isclose(combined.pmf.sum(), 1.0)


def test_scale_x_uses_projection_method_only_for_mass_deposit():
    source = Pmf1D.multi_dirac(np.array([-1.0, 1.0]), dx=1.0)

    nearest = source.scale_x(
        0.8, keep_dx=True, dx_ref=0.3,
        method="mass_deposit", projection_method="nearest",
    )
    linear = source.scale_x(
        0.8, keep_dx=True, dx_ref=0.3,
        method="mass_deposit", projection_method="linear",
    )
    assert not np.array_equal(nearest.pmf, linear.pmf)

    interpolated_nearest = source.scale_x(
        0.8, keep_dx=True, dx_ref=0.3,
        method="interpolate_ordinates", projection_method="nearest",
    )
    interpolated_linear = source.scale_x(
        0.8, keep_dx=True, dx_ref=0.3,
        method="interpolate_ordinates", projection_method="linear",
    )
    np.testing.assert_array_equal(
        interpolated_nearest.x, interpolated_linear.x,
    )
    np.testing.assert_array_equal(
        interpolated_nearest.pmf, interpolated_linear.pmf,
    )


def test_pmf_sample_uses_distribution_specific_construction_rules():
    sigma = 0.2
    dx = 0.1
    n_sigma = 2
    gaussian = Pmf1D.gaussian(
        0.0, sigma, dx, n_sigma=n_sigma, pdf_to_pmf_method="pmf_sample",
    )
    extent = round(n_sigma * sigma / dx)
    x = np.arange(-extent, extent + 1) * dx
    expected = np.exp(-x**2 / (2 * sigma**2 + np.finfo(float).eps))
    expected /= expected.sum()
    integrated = Pmf1D.gaussian(
        0.0, sigma, dx, n_sigma=n_sigma, pdf_to_pmf_method="bin_integral",
    )
    np.testing.assert_array_equal(gaussian.x, integrated.x)
    np.testing.assert_allclose(gaussian.pmf, expected, rtol=1e-15, atol=1e-15)

    cfg = type("Grid", (), {"dy": dx})()
    uniform = Pmf1D.uniform(0.36, cfg, pdf_to_pmf_method="pmf_sample")
    np.testing.assert_allclose(uniform.x, np.arange(-2, 3) * dx, rtol=0, atol=1e-15)
    np.testing.assert_allclose(uniform.pmf, np.full(5, 0.2), rtol=0, atol=1e-15)
    assert not np.array_equal(uniform.pmf, Pmf1D.uniform(0.36, cfg).pmf)


def test_pdf_to_pmf_method_rejects_unknown_method():
    cfg = type("Grid", (), {"dy": 0.1})()
    with pytest.raises(ValueError, match="pdf_to_pmf_method"):
        Pmf1D.gaussian(0.0, 0.2, 0.1, pdf_to_pmf_method="unknown")
    with pytest.raises(ValueError, match="pdf_to_pmf_method"):
        Pmf1D.uniform(0.2, cfg, pdf_to_pmf_method="unknown")


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


def test_reference_scale_negative_uses_same_grid_and_mirrors_ordinates():
    source = Pmf1D(dx=0.1, st_idx=-2, pmf=np.array([0.05, 0.15, 0.5, 0.2, 0.1]))

    positive = source.scale_x(
        1.5, keep_dx=True, dx_ref=0.1, method="interpolate_ordinates",
    )
    negative = source.scale_x(
        -1.5, keep_dx=True, dx_ref=0.1, method="interpolate_ordinates",
    )

    np.testing.assert_array_equal(negative.x, positive.x)
    np.testing.assert_array_equal(negative.pmf, positive.pmf[::-1])

    zero = source.scale_x(
        0.0, keep_dx=True, dx_ref=0.1, method="interpolate_ordinates",
    )
    np.testing.assert_array_equal(zero.x, np.array([0.0]))
    np.testing.assert_allclose(zero.pmf, np.array([1.0]), rtol=0.0, atol=1e-15)


def test_fir_filter_uses_mass_deposit_not_scalar_resampling():
    source = Pmf1D(dx=0.1, st_idx=-2, pmf=np.array([0.1, 0.2, 0.4, 0.2, 0.1]))
    filtered = source.fir_filter(
        np.array([0.5]), keep_mass=1.0, dx_ref=0.1,
        projection_method="nearest",
    )
    expected = source.scale_x(
        0.5, keep_dx=True, dx_ref=0.1,
        method="mass_deposit", projection_method="nearest",
    )
    interpolated = source.scale_x(
        0.5, keep_dx=True, dx_ref=0.1,
        method="interpolate_ordinates",
    )
    np.testing.assert_array_equal(filtered.x, expected.x)
    np.testing.assert_allclose(filtered.pmf, expected.pmf, rtol=0, atol=1e-15)
    assert not np.array_equal(filtered.pmf, interpolated.pmf)


def test_reference_quantizer_retains_noise_axis_support_before_ffe():
    noise_support = Pmf1D(dx=0.1, st_idx=-4, pmf=np.full(9, 1.0 / 9.0))
    grid = type("Grid", (), {"dy": 0.1})()
    quantizer = Pmf1D.uniform(
        0.2, grid, pdf_to_pmf_method="pmf_sample", support=noise_support,
    )
    assert quantizer.st_idx == noise_support.st_idx
    assert len(quantizer.pmf) == len(noise_support.pmf)
    np.testing.assert_allclose(quantizer.pmf[3:6], np.full(3, 1.0 / 3.0))
    filtered = quantizer.fir_filter(
        np.array([0.5]), keep_mass=1.0, dx_ref=0.1,
        tap_abs_th=np.nextafter(0.0, 1.0),
        initial_bin_range=(-4, 4),
    )
    assert filtered.st_idx == -6
    assert len(filtered.pmf) == 13
    assert np.isclose(filtered.pmf.sum(), 1.0)
