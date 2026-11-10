"""Architecture boundaries for the standalone Annex 178A root model."""

from dataclasses import fields
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

from serdes_coding.models import com_model_93A as com_93A
from serdes_coding.models import com_178a
from serdes_coding.models import com_model_178A as com_178A
from serdes_coding.models.com_model_178A import (
    COM,
    COMChannelConfig,
    COMConfig,
    COMPMFConfig,
    COMPMFRuntimeConfig,
    COMPMFStatus,
    COMPath,
    COMSharedPath,
    COMSourceConfig,
    COMStatus,
)
from serdes_coding.search.com_search_178A import COMSearchCandidate, COMSearchConfig
from serdes_coding.utilities.link import LinkSegment
from serdes_coding.utilities.sparam import SparamModel


def test_178a_root_types_do_not_inherit_93a_root_types() -> None:
    assert not issubclass(COM, com_93A.COM)
    assert not issubclass(COMStatus, com_93A.COMStatus)
    assert COM.__bases__ == (object,)


def test_178a_path_types_have_only_neutral_utility_parents() -> None:
    assert com_178A.IEEECOMSparam.__bases__ == (SparamModel,)
    assert com_178A.IEEECOMFilter.__bases__ == (LinkSegment,)
    assert com_178A.IEEECOMSparam.__module__ == "serdes_coding.models.com_178a.path_stage"
    assert com_178A.IEEECOMFilter.__module__ == "serdes_coding.models.com_178a.path_stage"
    assert com_178A.COMBilinearCTLE.__module__ == "serdes_coding.models.com_178a.path_stage"
    assert not issubclass(com_178A.IEEECOMSparam, com_93A.IEEECOMSparam)
    assert not issubclass(com_178A.IEEECOMFilter, com_93A.IEEECOMFilter)


def test_178a_config_and_status_leaves_are_version_owned() -> None:
    owned_types = (
        COMChannelConfig,
        COMConfig,
        COMPMFConfig,
        COMPMFRuntimeConfig,
        COMPMFStatus,
        COMPath,
        COMSharedPath,
        COMStatus,
    )
    assert all(item.__module__.startswith("serdes_coding.models.com_178a") for item in owned_types)
    assert not issubclass(COMSharedPath, com_93A.COMSharedPath)
    assert COMPath is not com_93A.COMPath
    assert COMPMFStatus is not com_93A.COMPMFStatus


def test_every_178a_contract_export_is_owned_and_reexported_by_the_facade() -> None:
    for name in com_178a.__all__:
        contract = getattr(com_178a, name)
        assert contract.__module__.startswith("serdes_coding.models.com_178a")
        assert getattr(com_178A, name) is contract

    assert COMSearchCandidate.__module__ == "serdes_coding.search.com_search_178A"
    assert COMSearchConfig.__module__ == "serdes_coding.search.com_search_178A"
    assert com_178A.COMSearchCandidate is COMSearchCandidate
    assert com_178A.COMSearchConfig is COMSearchConfig


def test_178a_modules_import_cleanly_in_fresh_processes() -> None:
    modules = (
        "serdes_coding.models.com_178a.config",
        "serdes_coding.models.com_178a.status",
        "serdes_coding.search.com_search_178A",
        "serdes_coding.models.com_model_178A",
        "serdes_coding.io.com_excel_io_178A",
    )
    for module in modules:
        completed = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr


def test_178a_migrated_leaf_contracts_preserve_only_shared_version_neutral_fields() -> None:
    for owned, previous in (
        (COMPMFRuntimeConfig, com_93A.COMPMFRuntimeConfig),
        (COMSearchCandidate, com_93A.COMSearchCandidate),
    ):
        assert [(item.name, item.default, item.default_factory) for item in fields(owned)] == [
            (item.name, item.default, item.default_factory) for item in fields(previous)
        ]

    assert [item.name for item in fields(COMChannelConfig)] == [
        "R0",
        "R_d_tx",
        "R_d_rx",
        "gamma_src",
        "gamma_load",
        "sparam_frequency_limit_Hz",
    ]
    assert [item.name for item in fields(COMSourceConfig)] == ["channel"]
    assert [item.name for item in fields(COMSourceConfig.Channel)] == [
        "victim",
        "next",
        "fext",
    ]
    assert [item.name for item in fields(COMPMFConfig)] == [
        item.name for item in fields(com_93A.COMPMFConfig)
        if item.name != "gaussian_n_sigma"
    ]
    assert [item.name for item in fields(COMSearchConfig)] == [
        "c_m2_values",
        "c_m1_values",
        "c_1_values",
        "g_DC_values",
        "g_DC2_values",
        "pos_sweep_method",
        "pos_coarse_stride",
        "keep_top_n",
        "keep_all_rows",
        "continue_on_error",
        "group_size",
        "final_top_k",
    ]

    path_fields = fields(COMPath)
    assert [item.name for item in path_fields] == [
        "kind",
        "shared",
        "S_tx",
        "S_ch",
        "S_all",
        "H_21_measured_freqs",
        "H_21_measured_tf",
        "H_21",
        "H_all",
        "X",
        "pulse",
        "pulse_no_txffe",
    ]
    assert path_fields[-1].default is None

    assert [item.name for item in fields(COMSharedPath)] == [
        *[item.name for item in fields(com_93A.COMSharedPath)],
        "ctle_iir",
        "ctle_pulse_realization",
    ]
    assert [item.name for item in fields(COMPMFStatus)] == [
        "dy",
        "tap_abs_th",
        "final_vqc_convention",
        "final_V_qc",
        "final_delta",
        *[item.name for item in fields(com_93A.COMPMFStatus)][2:],
    ]


def test_178a_status_has_only_178a_root_stage_fields() -> None:
    assert [item.name for item in fields(COMStatus)] == [
        "paths",
        "run",
        "eq_ch",
        "dte",
        "imp",
        "pmf",
        "mlsd",
    ]
    status = COMStatus()
    assert not hasattr(status, "dfe")
    assert not hasattr(status, "FOM")


def test_178a_model_does_not_expose_93a_orchestration_surface() -> None:
    for name in (
        "_run_search",
        "build_all_paths_93A",
        "find_pos_and_dfe_93A",
        "calculate_imp_93A",
        "calculate_COM_93A",
        "report",
        "dfe_status",
    ):
        assert not hasattr(COM, name), name

    for name in (
        "_validate_victim_time_alignment",
        "dte_status",
        "imp_status",
        "pmf_status",
        "mlsd_status",
        "t_dsamp_ui",
        "h_XT",
    ):
        assert name in COM.__dict__, name


def test_178a_status_proxies_use_the_dte_stage() -> None:
    victim_h = np.arange(21, dtype=float)
    xtalk_h = -np.arange(21, dtype=float)
    victim = SimpleNamespace(pulse=SimpleNamespace(ir=victim_h))
    xtalk = SimpleNamespace(pulse=SimpleNamespace(ir=xtalk_h))
    dte = SimpleNamespace(pos=1, ts=9)
    imp = object()
    pmf = object()
    mlsd = object()

    model = COM.__new__(COM)
    model.cfg = SimpleNamespace(link=SimpleNamespace(per_ui=4))
    model.status = COMStatus(
        paths=[victim, xtalk],
        dte=dte,
        imp=imp,
        pmf=pmf,
        mlsd=mlsd,
    )

    assert model.victim is victim
    assert model.xtalks == [xtalk]
    assert model.dte_status is dte
    assert model.imp_status is imp
    assert model.pmf_status is pmf
    assert model.mlsd_status is mlsd
    np.testing.assert_array_equal(model.h_dsamp, victim_h[1::4])
    np.testing.assert_array_equal(model.t_dsamp_ui, np.arange(5, dtype=float) - 2.0)
    assert len(model.h_XT) == 1
    np.testing.assert_array_equal(model.h_XT[0], xtalk_h)
