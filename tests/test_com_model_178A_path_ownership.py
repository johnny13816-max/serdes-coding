"""Frozen path-stage evidence for ARC-178A-004B ownership migration."""

import hashlib
from pathlib import Path

import numpy as np

from serdes_coding.io.com_excel_io_178A import excel_to_config_178A
from serdes_coding.models.com_model_178A import (
    COM,
    IEEECOMFilter,
    IEEECOMSparam,
    _build_channel_under_test,
)
from serdes_coding.utilities.link import LinkConfig


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx"


def _digest(arrays: list[np.ndarray], *, decimals: int = 12) -> str:
    sha = hashlib.sha256()
    for values in arrays:
        array = np.ascontiguousarray(np.round(np.asarray(values), decimals))
        sha.update(array.view(np.uint8).tobytes())
    return sha.hexdigest()


def test_legacy_93a_named_methods_are_thin_178a_compatibility_wrappers() -> None:
    freqs = np.array([0.0, 1e9, 2e9])
    canonical_s = IEEECOMSparam.shunt_capacitance(freqs, 10e-15, 46.25)
    legacy_s = IEEECOMSparam.shunt_capacitance_93A(freqs, 10e-15, 46.25)
    assert type(canonical_s) is IEEECOMSparam
    assert type(legacy_s) is IEEECOMSparam
    np.testing.assert_array_equal(canonical_s.sdd, legacy_s.sdd)

    link = LinkConfig(fb=100e9, per_ui=8, target_df=1e9)
    taps = np.array([-0.1, 0.8, -0.1])
    canonical_h = IEEECOMFilter.tx_ffe(link, taps, num_pre=1)
    legacy_h = IEEECOMFilter.tx_ffe_93A(link, taps, num_pre=1)
    assert type(canonical_h) is IEEECOMFilter
    assert type(legacy_h) is IEEECOMFilter
    np.testing.assert_array_equal(canonical_h.tf, legacy_h.tf)


def test_channel_ingestion_branches_keep_all_sdd_elements() -> None:
    cfg = excel_to_config_178A(str(CONFIG))
    expected = {
        "sdd_first": "57563c7336104f5ed91e498373e832cf9d36fa0bc791f5eaa40b39b69920c152",
        "s4p_first": "13e30d2be0da54b86d39a01e988e267b62f9597187312fb926ca99b890c9b091",
    }
    for method, digest in expected.items():
        channels = _build_channel_under_test(cfg.channel, method)
        assert len(channels) == 6
        assert all(channel.sdd.shape[1:] == (2, 2) for channel in channels)
        assert _digest([channel.sdd for channel in channels]) == digest


def test_reference_path_stage_layer_digests_are_unchanged() -> None:
    cfg = excel_to_config_178A(str(CONFIG))
    paths = COM(cfg).build_all_paths()

    assert [path.kind for path in paths] == [
        "victim", "next", "next", "fext", "fext", "fext"
    ]
    assert _digest([path.S_tx.sdd for path in paths]) == (
        "b94fef1d6a63c512a52b2d6058fc3fb7f672779aa560515c5549a9aaf1b272a7"
    )
    assert _digest([path.S_ch.sdd for path in paths]) == (
        "13e30d2be0da54b86d39a01e988e267b62f9597187312fb926ca99b890c9b091"
    )
    assert _digest([path.S_all.sdd for path in paths]) == (
        "611699d17140b23a19867dd40e2b14dd215b9079fdf6f8a7c0d9b0445d96badd"
    )
    assert _digest([path.H_21.tf for path in paths]) == (
        "0015a776f86beb5cbb7c83c60237b7ba9eea19e98ea299e3c1460953d8b8f59f"
    )
    assert _digest([path.H_all.tf for path in paths]) == (
        "2791db37bab92e454cee78e5fa60cd39019261fbdf96eaa73960998c18aa20fb"
    )
    assert _digest([path.pulse.ir for path in paths]) == (
        "f129b444e628dc9d3d00a001060defebdd29a57df34ac87ec3fc075741d11260"
    )

    shared = paths[0].shared
    assert _digest([
        shared.S_rx.sdd,
        shared.H_ffe.tf,
        shared.H_ffe_next.tf,
        shared.H_t.tf,
        shared.H_r.tf,
        shared.H_ctf.tf,
    ]) == "da7ca9643c7df78068598844d8b6913085f06e7e5640d9d0a2e55e4ca4b3d348"
