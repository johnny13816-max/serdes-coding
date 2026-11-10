from dataclasses import fields
from pathlib import Path

import pytest

from serdes_coding.io.com_excel_io_178A import excel_to_config_178A
from serdes_coding.models import com_model_178A as model


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx"


def test_adapter_separates_channel_source_physical_and_algorithm_domains() -> None:
    cfg = excel_to_config_178A(str(CONFIG))

    assert isinstance(cfg.src, model.COMSourceConfig)
    assert cfg.src.channel.victim.path.endswith(".s4p")
    assert len(cfg.src.channel.next) == 2
    assert len(cfg.src.channel.fext) == 3
    assert all(
        binding.representation == "auto"
        for binding in cfg.src.channel.ordered()
    )
    assert {item.name for item in fields(type(cfg.channel))} == {
        "R0",
        "R_d_tx",
        "R_d_rx",
        "gamma_src",
        "gamma_load",
        "sparam_frequency_limit_Hz",
    }
    assert cfg.alg.missing_dc_policy == "mag_phase_trend_to_dc"


def test_source_binding_validates_interpretation_metadata() -> None:
    binding = model.COMSourceConfig.ChannelBinding

    with pytest.raises(ValueError, match="path"):
        binding(path="")
    with pytest.raises(ValueError, match="representation"):
        binding(path="victim.s4p", representation="s3p")
    with pytest.raises(ValueError, match="port_order"):
        binding(path="victim.s4p", port_order=(0, 0, 1, 2))


def test_only_com_source_config_is_a_public_top_level_source_type() -> None:
    assert not hasattr(model, "COMChannelSource")
    assert model.COMSourceConfig.ChannelBinding.__qualname__.startswith(
        "COMSourceConfig."
    )


def test_source_export_records_binding_and_physical_boundary_separately() -> None:
    cfg = excel_to_config_178A(str(CONFIG))
    exported = cfg.to_export_dict()

    assert exported["config"]["src"]["channel"]["victim"]["path"] == (
        cfg.src.channel.victim.path
    )
    assert exported["config"]["channel"]["sparam_frequency_limit_Hz"] == (
        cfg.channel.sparam_frequency_limit_Hz
    )
    assert exported["derived"]["alg"]["missing_dc_policy"] == (
        cfg.alg.missing_dc_policy
    )
