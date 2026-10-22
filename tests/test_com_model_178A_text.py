"""Semantic text contracts for Annex 178A config, status, and search objects."""

from dataclasses import fields
from io import StringIO
import inspect
from types import SimpleNamespace

import numpy as np

from serdes_coding.models.com_dataclass_text import COMDataclassText
from serdes_coding.models import com_model_178A as model
from serdes_coding.search import com_search_178A as search


MODEL_TEXT_CLASSES = (
    model.COMBilinearCTLE,
    model.COMSharedPath,
    model.COMDeviceTermConfig,
    model.COMDevicePackageConfig,
    model.COMPartialHostConfig,
    model.COMPkgConfig,
    model.COMFilterConfig,
    model.COMDTEConfig,
    model.COMRunConfig,
    model.COMExecutionConfig,
    model.COMImpairmentConfig,
    model.COMMLSDConfig,
    model.COMPolicyConfig,
    model.COMConfig,
    model.COMPSDStatus,
    model.COMAddedNoiseIterationStatus,
    model.COMAddedNoiseStatus,
    model.COMMLSDNoiseStatus,
    model.COMMLSDStatus,
    model.COMEqChannelStatus,
    model.COMAdcInputPMF,
    model.COMImpStageStatus,
    model.COMImpairmentStatus,
    model.COMDTEStatus,
    model.COMRunStatus,
    model.COMStatus,
)

SEARCH_TEXT_CLASSES = (search.COMSearchRow, search.COMSearchStatus)


def _blank_instance(cls: type[COMDataclassText]) -> COMDataclassText:
    instance = object.__new__(cls)
    for item in fields(cls):
        object.__setattr__(instance, item.name, None)
    if cls is model.COMStatus:
        object.__setattr__(instance, "paths", [])
    if cls is search.COMSearchStatus:
        object.__setattr__(instance, "best", SimpleNamespace(final_COM=None))
        object.__setattr__(instance, "rows", [])
    return instance


def test_all_178a_owned_dataclasses_implement_semantic_text_contract() -> None:
    for cls in MODEL_TEXT_CLASSES + SEARCH_TEXT_CLASSES:
        assert issubclass(cls, COMDataclassText), cls.__name__
        assert not inspect.isabstract(cls), cls.__name__
        assert "_text_sections" in cls.__dict__, cls.__name__
        assert "_repr_fields" in cls.__dict__, cls.__name__


def test_every_dataclass_field_has_an_explicit_semantic_text_entry() -> None:
    for cls in MODEL_TEXT_CLASSES + SEARCH_TEXT_CLASSES:
        instance = _blank_instance(cls)
        selected = {
            field.source_name
            for section in instance._text_sections()
            for field in section.fields
            if "." not in field.source_name and field.source_name not in {"COM", "final_COM"}
        }
        assert selected == {item.name for item in fields(cls)}, cls.__name__
        assert all(
            field.unit is not None
            for section in instance._text_sections()
            for field in section.fields
        ), cls.__name__


def test_filter_text_applies_explicit_engineering_units() -> None:
    cfg = model.COMFilterConfig(
        Tr=4e-12,
        fr=58.4375e9,
        g_1=-20.0,
        g_2=-2.0,
        f_z1=42.5e9,
        f_z2=1.328125e9,
        f_p1=42.5e9,
        f_p2=106.25e9,
        f_p3=1.328125e9,
        A_v=0.385,
        A_fe=0.385,
        A_ne=0.481,
    )

    text = cfg.to_string()
    assert "20%-80% transition time: 4 ps" in text
    assert "receiver noise-filter bandwidth: 58.4375 GHz" in text
    assert "victim pulse amplitude: 385 mV" in text
    assert "TX FFE tap vector:" in text
    assert "dimensionless" in text


def test_dte_text_is_semantic_bounded_and_unit_aware() -> None:
    array = np.linspace(-0.25, 1.0, 12)
    status = model.COMDTEStatus(
        ts=101,
        pos=5,
        d=6,
        w_lim=array,
        b_lim=np.array([0.1, -0.02]),
        mse=6.2e-3,
        H_all=np.ones((20, 20)),
        Rnn_all=np.eye(20),
        pruned_index=np.array([1, 2, 3]),
        H=np.ones((4, 4)),
        R_nn=np.eye(4),
        H_b=np.ones((4, 2)),
        w=array,
        b=np.array([0.11, -0.01]),
    )

    text = status.to_string()
    assert "[Sampling]" in text
    assert "sampling phase: 5 sample index" in text
    assert "mean-square error: 6200 mV^2" in text
    assert "full channel matrix: shape=(20, 20), dtype=float64 V" in text
    assert "..." in text
    assert len(text) < 3000

    one_line = repr(status)
    assert "\n" not in one_line
    assert "0x" not in one_line
    assert "mse=0.0062 V^2" in one_line


def test_print_matches_to_string_and_none_is_explicit() -> None:
    cfg = model.COMRunConfig(pmf_dy_override=None)
    stream = StringIO()
    cfg.print(file=stream)
    assert stream.getvalue() == cfg.to_string() + "\n"
    assert "PMF voltage-grid spacing override: <not available>" in cfg.to_string()


def test_search_row_names_every_equalizer_coefficient() -> None:
    candidate = search.COMSearchCandidate(
        c_m2=0.06,
        c_m1=-0.26,
        c_1=0.0,
        g_DC=-16.0,
        g_DC2=-4.0,
    )
    row = search.COMSearchRow(idx=17, candidate=candidate, mse=6.2e-3)

    text = row.to_string()
    assert "c_m2=0.06" in text
    assert "c_m1=-0.26" in text
    assert "c_1=0" in text
    assert "g_1=-16 dB" in text
    assert "g_2=-4 dB" in text


def test_root_status_reports_stage_lifecycle_without_expanding_full_status() -> None:
    dte = SimpleNamespace(pos=19, ts=65264, mse=0.006203013107434269)
    pmf = SimpleNamespace(COM=1.524760783422)
    mlsd = SimpleNamespace(delta_COM=1.371137901447, COM_MLSD=2.895898684873)
    status = model.COMStatus(paths=[object()] * 6, dte=dte, pmf=pmf, mlsd=mlsd)

    text = status.to_string()
    assert "channel paths: 6 path count" in text
    assert "DTE stage: complete" in text
    assert "COM DFE: 1.52476078 dB" in text
    assert "COM MLSD: 2.89589868 dB" in text
    assert "SimpleNamespace" not in text


def test_json_snapshot_contract_remains_available() -> None:
    cfg = model.COMRunConfig(target="mse", pmf_dy_override=2.5e-6)
    assert cfg._json_value(cfg) == {
        "target": "mse",
        "pre_dte_pmf_method": "gaussian_approx",
        "pmf_grid_quality": "fine",
        "pmf_keep_mass": 0.99999,
        "pmf_dy_override": 2.5e-6,
        "floating_mode": "heuristic",
        "pos_sweep_method": "each_phase",
        "pos_coarse_stride": 4,
    }
