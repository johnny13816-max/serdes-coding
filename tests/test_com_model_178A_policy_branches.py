from dataclasses import fields, replace
from pathlib import Path
from shutil import copy2

import numpy as np
import openpyxl
import pytest

from serdes_coding.io.com_excel_io import excel_to_config_178A
from serdes_coding.models.com_model_178A import (
    COM,
    COMPMFGridControl,
    COMPolicyConfig,
    COMRunConfig,
    _resolve_adc_input_pmf_config,
    _resolve_final_com_pmf_config,
)


def _with_methods(cfg, **changes):
    return replace(cfg, policy=replace(cfg.policy, **changes))


def test_178a_branch_registry_covers_policy_and_run_fields():
    root = Path(__file__).resolve().parents[1]
    registry = (
        root / "docs" / "models" / "178A" / "branch_behavior_registry.md"
    ).read_text(encoding="utf-8")
    for field in fields(COMPolicyConfig):
        assert field.name in registry
    for field in fields(COMRunConfig):
        assert field.name in registry


@pytest.fixture(scope="module")
def reference_cfg():
    root = Path(__file__).resolve().parents[1]
    return excel_to_config_178A(
        str(root / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx")
    )


def test_178a_out_of_measured_changes_only_scalar_vtf(reference_cfg):
    assert reference_cfg.policy.out_of_measured == "zero_padding"
    measured_cfg = _with_methods(reference_cfg, out_of_measured="cosine_decay")
    zero_paths = COM(reference_cfg).build_all_paths()
    measured_paths = COM(measured_cfg).build_all_paths()
    assert len(zero_paths) == len(measured_paths) == 6

    freqs = reference_cfg.link.freqs
    for zero, measured in zip(zero_paths, measured_paths):
        below = freqs <= zero.S_all.freqs[-1]
        above = ~below
        assert np.any(above)
        assert zero.kind == measured.kind
        np.testing.assert_array_equal(zero.S_ch.sdd, measured.S_ch.sdd)
        np.testing.assert_array_equal(zero.S_all.sdd, measured.S_all.sdd)
        np.testing.assert_allclose(zero.H_21.tf[below], measured.H_21.tf[below], rtol=0, atol=0)
        np.testing.assert_array_equal(zero.H_21.tf[above], np.zeros(np.count_nonzero(above)))


def test_178a_separated_grid_controls_do_not_leak_between_domains(reference_cfg):
    As = reference_cfg.imp.R_LM / (reference_cfg.L - 1)
    run_cfg = replace(
        reference_cfg.execution.search_sweep,
        adc_input_pmf_grid=replace(
            reference_cfg.execution.search_sweep.adc_input_pmf_grid,
            dy_override=2e-5,
        ),
    )
    resolved = _resolve_adc_input_pmf_config(reference_cfg.pmf, As, run_cfg)
    assert resolved.dy == 2e-5
    assert resolved.keep_mass == run_cfg.pmf_keep_mass
    final = _resolve_final_com_pmf_config(reference_cfg.pmf, As, run_cfg)
    assert final.dy == pytest.approx(
        run_cfg.final_pmf_grid.dy_rel_As * As
    )
    assert final.keep_mass == 1.0

    final_override = replace(
        run_cfg,
        final_pmf_grid=replace(run_cfg.final_pmf_grid, dy_override=3e-5),
    )
    assert _resolve_final_com_pmf_config(
        reference_cfg.pmf, As, final_override
    ).dy == pytest.approx(3e-5)
    assert _resolve_adc_input_pmf_config(
        reference_cfg.pmf, As, final_override
    ).dy == pytest.approx(2e-5)


def test_178a_pmf_grid_control_rules_and_override_precedence():
    As = 0.02
    relative = COMPMFGridControl(
        rule="relative_As", dy_rel_As=1e-3, dy_abs_max=1e-5
    )
    capped = replace(relative, rule="relative_As_with_cap")
    overridden = replace(capped, dy_override=4e-6)
    assert relative.resolve_dy(As) == pytest.approx(2e-5)
    assert capped.resolve_dy(As) == pytest.approx(1e-5)
    assert overridden.resolve_dy(As) == pytest.approx(4e-6)


@pytest.mark.parametrize("invalid", [0.0, -1e-5, np.nan, np.inf])
def test_178a_grid_control_rejects_invalid_numeric_values(invalid):
    with pytest.raises(ValueError, match="dy_override"):
        COMPMFGridControl(dy_override=invalid)
    with pytest.raises(ValueError, match="dy_rel_As"):
        COMPMFGridControl(dy_rel_As=invalid)


def test_178a_grid_control_rejects_unknown_rule():
    with pytest.raises(ValueError, match="rule"):
        COMPMFGridControl(rule="other")


def test_178a_legacy_shared_run_dy_override_remains_compatible(reference_cfg):
    As = reference_cfg.imp.R_LM / (reference_cfg.L - 1)
    legacy_override = COMRunConfig(pmf_dy_override=2e-5)
    assert _resolve_adc_input_pmf_config(
        reference_cfg.pmf, As, legacy_override
    ).dy == pytest.approx(2e-5)
    assert _resolve_final_com_pmf_config(
        reference_cfg.pmf, As, legacy_override
    ).dy == pytest.approx(2e-5)


def test_178a_canonical_adc_grid_takes_precedence_over_legacy_shared_override(reference_cfg):
    As = reference_cfg.imp.R_LM / (reference_cfg.L - 1)
    mixed = replace(
        reference_cfg.execution.search_sweep,
        pmf_dy_override=2e-5,
        adc_input_pmf_grid=replace(
            reference_cfg.execution.search_sweep.adc_input_pmf_grid,
            dy_override=3e-5,
        ),
    )
    assert _resolve_adc_input_pmf_config(
        reference_cfg.pmf, As, mixed
    ).dy == pytest.approx(3e-5)


@pytest.mark.parametrize("invalid", [0.0, -1e-5, np.nan, np.inf])
def test_178a_run_dy_override_rejects_nonpositive_or_nonfinite(invalid):
    with pytest.raises(ValueError, match="pmf_dy_override"):
        COMRunConfig(pmf_dy_override=invalid)


def test_178a_out_of_measured_rejects_unknown_method(reference_cfg):
    with pytest.raises(ValueError, match="out_of_measured"):
        _with_methods(reference_cfg, out_of_measured="other")


def test_178a_ctle_pulse_realization_defaults_and_rejects_unknown_method(reference_cfg):
    fields = COMPolicyConfig.__dataclass_fields__
    assert fields["ctle_pulse_realization"].default == "continuous_tf"
    assert fields["rxffe_record_realization"].default == "linear_fixed_grid"
    with pytest.raises(ValueError, match="ctle_pulse_realization"):
        _with_methods(reference_cfg, ctle_pulse_realization="other")
    with pytest.raises(ValueError, match="rxffe_record_realization"):
        _with_methods(reference_cfg, rxffe_record_realization="other")


def test_178a_eq_ch_imp_length_contract_and_reference_profile(reference_cfg):
    assert reference_cfg.policy.eq_ch_imp_len == "truncated"
    assert reference_cfg.policy.num_trunc_ui == 4096
    model = COM(reference_cfg)
    assert model._eq_ch_imp_record_cfg.sampled_nfft == 4096
    assert model._eq_ch_imp_record_cfg is not reference_cfg.link
    assert COM(replace(reference_cfg, policy=COMPolicyConfig()))._eq_ch_imp_record_cfg is reference_cfg.link
    with pytest.raises(ValueError, match="even num_trunc_ui"):
        COMPolicyConfig(eq_ch_imp_len="truncated", num_trunc_ui=4095)
    with pytest.raises(ValueError, match="num_trunc_ui=None"):
        COMPolicyConfig(eq_ch_imp_len="full", num_trunc_ui=4096)


def test_178a_rxffe_record_realization_resolves_stage5_grid(reference_cfg):
    fixed_cfg = replace(reference_cfg, policy=COMPolicyConfig())
    fixed_model = COM(fixed_cfg)
    assert fixed_model._resolve_post_ffe_response_cfg() is fixed_cfg.link

    expanded_cfg = replace(
        reference_cfg,
        policy=COMPolicyConfig(rxffe_record_realization="linear_expanded_grid"),
    )
    expanded_model = COM(expanded_cfg)
    expanded = expanded_model._resolve_post_ffe_response_cfg()
    expected = expanded_cfg.link.sampled_nfft + expanded_cfg.dte.N_max - 1
    if expected % 2:
        expected += 1
    assert expanded.sampled_nfft == expected
    assert expanded_model._resolve_post_ffe_imp_record_cfg(expanded) is expanded

    reference_model = COM(reference_cfg)
    assert reference_model._resolve_post_ffe_response_cfg() is reference_cfg.link
    assert (
        reference_model._resolve_post_ffe_imp_record_cfg(reference_cfg.link)
        is reference_model._eq_ch_imp_record_cfg
    )


def test_178a_eq_ch_imp_length_changes_only_psd_input_record(reference_cfg):
    response = np.arange(5000, dtype=float)
    original = response.copy()

    full_model = COM(replace(reference_cfg, policy=COMPolicyConfig()))
    full_record = full_model._realize_eq_ch_imp_record(
        response, source_name="test response"
    )
    assert full_record is response

    truncated_model = COM(reference_cfg)
    truncated_record = truncated_model._realize_eq_ch_imp_record(
        response, source_name="test response"
    )
    assert truncated_record.shape == (4096,)
    np.testing.assert_array_equal(truncated_record, response[:4096])
    np.testing.assert_array_equal(response, original)

    short = np.arange(8, dtype=float)
    padded = truncated_model._realize_eq_ch_imp_record(
        short, source_name="short response"
    )
    np.testing.assert_array_equal(padded[:8], short)
    np.testing.assert_array_equal(padded[8:], 0.0)


def test_178a_renormalization_policy_changes_only_channel_and_downstream(reference_cfg):
    assert reference_cfg.policy.channel_renormalization_order == "s4p_first"
    spec_cfg = _with_methods(reference_cfg, channel_renormalization_order="sdd_first")
    actual = COM(reference_cfg).build_all_paths()
    spec = COM(spec_cfg).build_all_paths()
    assert len(actual) == len(spec) == 6
    assert max(np.max(np.abs(a.S_ch.sdd - b.S_ch.sdd)) for a, b in zip(actual, spec)) > 1e-6
    for a, b in zip(actual, spec):
        np.testing.assert_array_equal(a.S_tx.sdd, b.S_tx.sdd)
        np.testing.assert_array_equal(a.S_rx.sdd, b.S_rx.sdd)
        np.testing.assert_array_equal(a.H_ffe.tf, b.H_ffe.tf)


def test_178a_renormalization_policy_rejects_unknown_method(reference_cfg):
    with pytest.raises(ValueError, match="channel_renormalization_order"):
        _with_methods(reference_cfg, channel_renormalization_order="unknown")


@pytest.mark.parametrize("pmf_method", ["gaussian_approx", "pmf_exact"])
def test_178a_pre_dte_adc_clipping_policy_changes_only_quantization_input(
    reference_cfg, pmf_method
):
    assert reference_cfg.policy.pre_dte_adc_clipping_convention == "matlab_4_17_reference_only"
    annex_cfg = _with_methods(reference_cfg, pre_dte_adc_clipping_convention="annex_d3")
    paths = COM(reference_cfg).build_all_paths()
    victim, xtalks = paths[0], paths[1:]
    model = COM(reference_cfg)
    common = model.calculate_pre_dte_imp_common(victim)
    common, h_xt_dsamp = model.prepare_sampling_phase_common(
        common, [path.pulse.ir for path in xtalks]
    )
    run_cfg = replace(
        reference_cfg.execution.single_run,
        pre_dte_pmf_method=pmf_method,
        pmf_dy_override=1e-5,
        pmf_keep_mass=1.0,
    )
    reference_eq, reference = model.calculate_pre_dte_imp_at_pos(
        victim, 23, common, h_xt_dsamp, run_cfg
    )
    annex_eq, annex = COM(annex_cfg).calculate_pre_dte_imp_at_pos(
        victim, 23, common, h_xt_dsamp, run_cfg
    )

    ref_psd = reference.pre_dte.psd
    annex_psd = annex.pre_dte.psd
    assert reference.pre_dte.adc_input.clipping_convention == "matlab_4_17_reference_only"
    assert annex.pre_dte.adc_input.clipping_convention == "annex_d3"
    assert reference.pre_dte.adc_input.V_qc < annex.pre_dte.adc_input.V_qc
    if pmf_method == "pmf_exact":
        assert reference.pre_dte.adc_input.p_n is reference.pre_dte.adc_input.p_ga
        assert annex.pre_dte.adc_input.p_n is annex.pre_dte.adc_input.p_ga
    np.testing.assert_array_equal(reference_eq.h_dsamp.ir, annex_eq.h_dsamp.ir)
    for name in ("S_rn", "S_xn", "S_tn", "S_jn"):
        np.testing.assert_array_equal(getattr(ref_psd, name).psd, getattr(annex_psd, name).psd)
    np.testing.assert_allclose(
        ref_psd.S_total.psd - annex_psd.S_total.psd,
        ref_psd.S_qn.psd - annex_psd.S_qn.psd,
        rtol=0,
        atol=1e-25,
    )


def test_178a_pre_dte_adc_clipping_policy_rejects_unknown_method(reference_cfg):
    with pytest.raises(ValueError, match="pre_dte_adc_clipping_convention"):
        _with_methods(reference_cfg, pre_dte_adc_clipping_convention="unknown")


def test_178a_final_com_vqc_policy_rejects_unknown_method(reference_cfg):
    assert reference_cfg.policy.final_com_vqc_convention == "sicopr_final_reconstruction"
    with pytest.raises(ValueError, match="final_com_vqc_convention"):
        _with_methods(reference_cfg, final_com_vqc_convention="unknown")


def test_178a_pdf_to_pmf_policy_rejects_unknown_method(reference_cfg):
    with pytest.raises(ValueError, match="pdf_to_pmf_method"):
        _with_methods(reference_cfg, pdf_to_pmf_method="unknown")


def test_178a_reference_execution_profile_is_expanded_by_excel_adapter(reference_cfg, tmp_path):
    source = (
        Path(__file__).resolve().parents[1]
        / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx"
    )
    workbook_path = tmp_path / "config_align_to_ref.xlsx"
    copy2(source, workbook_path)
    book = openpyxl.load_workbook(workbook_path)
    fixed = book["fixed_config"]
    raw_values = {
        "out_of_measured": "cosine_decay",
        "channel_renormalization_order": "sdd_first",
        "pre_dte_adc_clipping_convention": "annex_d3",
        "final_com_vqc_convention": "selected_phase_adc_input",
    }
    for row in fixed.iter_rows(min_row=4):
        name = row[1].value
        if name in raw_values:
            row[3].value = raw_values[name]
        if name == "align_to_ref":
            row[3].value = None
    run = book["run_config"]
    for row in run.iter_rows(min_row=4):
        if row[0].value == "control" and row[1].value == "execution_profile":
            row[2].value = "sicopr_reference_v1"
            break
    else:
        run.append([
            "control", "execution_profile", "sicopr_reference_v1", "enum",
            "Versioned project-to-runtime execution profile.",
        ])
    book.save(workbook_path)

    aligned = excel_to_config_178A(str(workbook_path))
    policy = aligned.policy
    assert aligned.policy.applied_config_profile == "sicopr_reference_v1"
    assert aligned.channel.missing_dc_policy == "mag_phase_trend_to_dc"
    assert policy.out_of_measured == "zero_padding"
    assert policy.channel_renormalization_order == "s4p_first"
    assert policy.pre_dte_adc_clipping_convention == "matlab_4_17_reference_only"
    assert policy.final_com_vqc_convention == "sicopr_final_reconstruction"
    assert policy.ctle_pulse_realization == "bilinear_iir"
    assert policy.rxffe_record_realization == "finite_record_circshift"
    assert policy.eq_ch_imp_len == "truncated"
    assert policy.num_trunc_ui == 4096
    assert policy.pmf_projection_method == "nearest"
    assert not hasattr(policy, "interference_pmf_method")
    assert policy.pdf_to_pmf_method == "pmf_sample"
    assert policy.pmf_scaling_method == "interpolate_ordinates"
    assert policy.added_noise_pdf == "scaled_total_pdf"
    assert policy.mlsd_quantization_psd == "main_tap_white"
    assert policy.sequence_termination == "matlab_relative_tail"
    assert policy.reported_der == "baseline_pdf_re_evaluation"
    assert policy.final_pmf_grid == "relative_As"
    assert policy.final_adc_pmf_projection == "reference_support"
    assert aligned.execution.single_run.target == "all_enabled"
    assert aligned.execution.search_sweep.target == "mse"
    assert aligned.execution.search_final.target == "all_enabled"
    effective = COM(aligned)._effective_run_cfg(aligned.execution.search_sweep)
    assert effective.pre_dte_pmf_method == "pmf_exact"
    assert effective.pmf_grid_quality == "fine"
    assert effective.pmf_keep_mass == 1.0
    assert effective.pmf_dy_override is None
    assert effective.adc_input_pmf_grid.rule == "relative_As_with_cap"
    assert effective.adc_input_pmf_grid.dy_override == pytest.approx(10e-6)
    assert effective.final_pmf_grid.rule == "relative_As"
    assert effective.final_pmf_grid.dy_override is None
    final_grid = _resolve_final_com_pmf_config(
        aligned.pmf, aligned.imp.R_LM / (aligned.L - 1), effective,
        final_pmf_grid=policy.final_pmf_grid,
    )
    assert final_grid.dy == pytest.approx(aligned.pmf.dy_rel_As * aligned.imp.R_LM / (aligned.L - 1))
    assert final_grid.gaussian_n_sigma == pytest.approx(8.0)
    exported = aligned.to_export_dict()["derived"]
    assert exported["policy"]["pmf_projection_method"] == "nearest"
    assert "interference_pmf_method" not in exported["policy"]
    assert exported["policy"]["applied_config_profile"] == "sicopr_reference_v1"
    overrides = exported["policy"]["config_profile_overrides"]
    assert overrides["channel.missing_dc_policy"] == {
        "raw": "skrf",
        "effective": "mag_phase_trend_to_dc",
        "overridden_by_profile": "sicopr_reference_v1",
    }
    assert overrides["policy.out_of_measured"] == {
        "raw": "cosine_decay",
        "effective": "zero_padding",
        "overridden_by_profile": "sicopr_reference_v1",
    }
    assert overrides["policy.ctle_pulse_realization"] == {
        "raw": "continuous_tf",
        "effective": "bilinear_iir",
        "overridden_by_profile": "sicopr_reference_v1",
    }
    assert overrides["policy.rxffe_record_realization"] == {
        "raw": "linear_fixed_grid",
        "effective": "finite_record_circshift",
        "overridden_by_profile": "sicopr_reference_v1",
    }
    assert overrides["policy.pdf_to_pmf_method"] == {
        "raw": "bin_integral",
        "effective": "pmf_sample",
        "overridden_by_profile": "sicopr_reference_v1",
    }
    assert overrides["policy.mlsd_quantization_psd"] == {
        "raw": "pre_dte_filtered",
        "effective": "main_tap_white",
        "overridden_by_profile": "sicopr_reference_v1",
    }
    assert overrides["numerical_control.adc_input_pmf_grid.dy_override"] == {
        "raw": None,
        "effective": 1e-5,
        "overridden_by_profile": "sicopr_reference_v1",
    }

    direct = replace(
        reference_cfg,
        policy=replace(
            policy,
            applied_config_profile=None,
            config_profile_overrides={},
        ),
        execution=aligned.execution,
    )
    assert direct.policy == replace(
        aligned.policy,
        applied_config_profile=None,
        config_profile_overrides={},
    )
    assert direct.execution == aligned.execution


def test_178a_new_template_exposes_b005_and_versioned_execution_profile():
    root = Path(__file__).resolve().parents[1]
    template = root / "cases" / "_templates" / "178A" / "config.xlsx"
    book = openpyxl.load_workbook(template, read_only=True, data_only=True)
    fields = {row[1].value for row in book["fixed_config"].rows if len(row) > 1}
    assert "align_to_ref" not in fields
    run_rows = {
        (row[0].value, row[1].value): row[2].value
        for row in book["run_config"].rows
        if len(row) > 2
    }
    assert run_rows[("control", "execution_profile")] == "project_standard"
    assert run_rows[("single_run", "target")] == "dfe"
    assert run_rows[("search_sweep", "target")] == "mse"
    assert run_rows[("search_final", "target")] == "dfe"
    assert "eq_ch_imp_len" in fields
    assert "num_trunc_ui" in fields
    assert "rxffe_record_realization" in fields
    assert "noise_grid_num_ui" not in fields
    canonical_grid_fields = {
        f"{family}.{field}"
        for family in ("adc_input_pmf_grid", "final_pmf_grid")
        for field in ("rule", "dy_rel_As", "dy_abs_max", "dy_override")
    }
    assert canonical_grid_fields.issubset(fields)
    assert "dy_rel_As" not in fields
    assert "dy_abs_max" not in fields
    run_fields = {parameter for _, parameter in run_rows}
    assert "pmf_grid_quality" not in run_fields
    assert "pmf_dy_override" not in run_fields
    for old_field in (
        "out_of_measured", "channel_renormalization_order",
        "pre_dte_adc_clipping_convention", "final_com_vqc_convention",
    ):
        assert old_field not in fields


def test_178a_legacy_align_to_ref_remains_a_compatible_alias(tmp_path):
    source = (
        Path(__file__).resolve().parents[1]
        / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx"
    )
    workbook_path = tmp_path / "legacy_align_to_ref.xlsx"
    copy2(source, workbook_path)
    book = openpyxl.load_workbook(workbook_path)
    run = book["run_config"]
    for row in run.iter_rows(min_row=4):
        if row[0].value == "control" and row[1].value == "execution_profile":
            row[2].value = None
    book["fixed_config"].append(
        ["policy", "align_to_ref", "compatibility", True, "boolean", "legacy alias"]
    )
    book.save(workbook_path)

    cfg = excel_to_config_178A(str(workbook_path))
    assert cfg.policy.applied_config_profile == "sicopr_reference_v1"
    assert cfg.policy.mlsd_quantization_psd == "main_tap_white"
