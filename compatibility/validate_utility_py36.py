"""Standalone validation for utility_py36.py.

Run with the exact Python 3.6.0 interpreter. This intentionally avoids pytest
so the compatibility artifact can be checked in a minimal legacy environment.
"""
from __future__ import print_function

import os
import sys
import tempfile

if sys.version_info[:3] != (3, 6, 0):
    raise RuntimeError(
        "validate_utility_py36.py requires CPython 3.6.0; found {}".format(
            sys.version.split()[0]
        )
    )

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
import scipy
import pandas
import matplotlib
import utility_py36 as utility
import skrf


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    expected_versions = {
        "numpy": (np.__version__, "1.19.5"),
        "scipy": (scipy.__version__, "1.5.4"),
        "pandas": (pandas.__version__, "0.25.3"),
        "matplotlib": (matplotlib.__version__, "3.3.4"),
        "scikit-rf": (skrf.__version__, "0.24.1"),
    }
    for name, versions in expected_versions.items():
        actual, expected = versions
        require(actual == expected, "{} version must be {}; found {}".format(name, expected, actual))

    public_names = (
        "ContinuousPSD",
        "SampledPSD",
        "Pmf1D",
        "LinkConfig",
        "SampledResponse",
        "LinkSegment",
        "SparamModel",
        "SparamProcessor",
    )
    for name in public_names:
        require(hasattr(utility, name), "missing public symbol: " + name)

    cfg = utility.LinkConfig.from_Nfft(fb=1.0e9, per_ui=8, Nfft=128)
    require(cfg.Nfft == 128, "LinkConfig Nfft mismatch")

    continuous = utility.ContinuousPSD.from_sigma(
        cfg.freqs, sigma=2.0e-3, f_start=0.0, f_stop=cfg.f_nyq
    )
    require(np.isclose(continuous.to_sigma(), 2.0e-3), "ContinuousPSD sigma mismatch")

    sampled_response = utility.SampledResponse.from_tf(
        theta=cfg.theta,
        tf=np.ones_like(cfg.theta, dtype=complex),
        fb=cfg.fb,
        nfft=cfg.sampled_nfft,
    )
    sampled = utility.SampledPSD.from_constant(cfg.theta, 1.0e-18, cfg.fb)
    filtered = sampled.filtered_by(sampled_response)
    require(np.allclose(filtered.psd, sampled.psd), "unity PSD filtering mismatch")
    require(np.isfinite(filtered.to_sigma()), "SampledPSD sigma is not finite")
    require(np.all(np.isfinite(filtered.to_autocorrelation())), "invalid autocorrelation")

    gaussian = utility.Pmf1D.gaussian(
        mu=0.0, sigma=1.0, dx=0.05, n_sigma=6.0, name="gaussian"
    )
    combined = gaussian.combine(gaussian, name="combined")
    require(np.isclose(np.sum(gaussian.pmf), 1.0), "Gaussian PMF mass mismatch")
    require(np.isclose(np.sum(combined.pmf), 1.0), "combined PMF mass mismatch")

    segment = utility.LinkSegment.from_tf(
        f_meas=cfg.freqs,
        H_meas=np.ones_like(cfg.freqs, dtype=complex),
        cfg=cfg,
    )
    require(np.allclose(segment.tf, 1.0), "LinkSegment unity TF mismatch")
    sampled_segment = segment.to_sampled_response(pos=0)
    require(sampled_segment.ir.ndim == 1, "invalid sampled response")

    freqs = np.array([0.0, 1.0e9, 2.0e9])
    sdd = np.zeros((len(freqs), 2, 2), dtype=complex)
    sdd[:, 1, 0] = np.array([1.0, 0.9, 0.8])
    sdd[:, 0, 1] = sdd[:, 1, 0]
    model = utility.SparamModel.from_sdd_array(freqs, sdd, z0=100.0)
    require(model.sdd.shape == (3, 2, 2), "SparamModel shape mismatch")
    require(model.renormalized(90.0).sdd.shape == (3, 2, 2), "renormalize failed")
    require(model.extrapolated_to_dc().sdd.shape == (3, 2, 2), "DC handling failed")
    new_freqs = np.array([0.0, 0.5e9, 1.0e9, 1.5e9, 2.0e9])
    require(model.resampled(new_freqs).sdd.shape == (5, 2, 2), "resample failed")
    require(model.cascade(model).sdd.shape == (3, 2, 2), "cascade failed")

    out_dir = tempfile.mkdtemp(prefix="utility_py36_")
    out_path = os.path.join(out_dir, "smoke.s2p")
    written = model.write_touchstone_s2p(out_path)
    require(os.path.isfile(str(written)), "Touchstone output was not created")
    restored = utility.SparamModel.from_touchstone(str(written), mode="sdd", z0=100.0)
    require(np.allclose(restored.sdd, model.sdd), "Touchstone write/read mismatch")

    plot_path = os.path.join(out_dir, "segment_tf.png")
    ax = segment.plot_tf(save_path=plot_path)
    require(ax is not None, "matplotlib smoke plot failed")
    require(os.path.isfile(plot_path), "matplotlib output was not created")

    print("utility_py36 validation passed on Python " + sys.version.split()[0])


if __name__ == "__main__":
    main()

