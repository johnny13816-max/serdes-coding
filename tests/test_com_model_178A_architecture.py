"""Architecture boundaries for the standalone Annex 178A root model."""

from dataclasses import fields
from types import SimpleNamespace

import numpy as np

from serdes_coding.models import com_model_93A as com_93A
from serdes_coding.models.com_model_178A import COM, COMStatus


def test_178a_root_types_do_not_inherit_93a_root_types() -> None:
    assert not issubclass(COM, com_93A.COM)
    assert not issubclass(COMStatus, com_93A.COMStatus)
    assert COM.__bases__ == (object,)


def test_178a_status_has_only_178a_root_stage_fields() -> None:
    assert [item.name for item in fields(COMStatus)] == [
        "paths",
        "run",
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
