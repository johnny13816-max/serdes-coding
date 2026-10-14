from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np
import pytest
from openpyxl import load_workbook

from serdes_coding.io.conversion.adhoc_to_project import build_project_config_draft, _map_contract, _read_project_schema
from serdes_coding.io.conversion.draft import ConversionDraft, MappingStatus
from serdes_coding.io.conversion.mapping_rules import area_for, rules_for, outcome
from serdes_coding.io.conversion.channels import replace_channels
from serdes_coding.io.conversion.project_writer import write_project_config, write_conversion_audit
from serdes_coding.io.conversion.existing_project import load_existing_project, save_existing_project
from serdes_coding.io.com_excel_common import _validate_channel_package_R0
from serdes_coding.models.com_model_93A import COMChannelConfig

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'reference_data/COM_adhoc_config/sicopr/config_com_dj_200G_CAKR_178_PKGA_06_2_2025__Case1.xlsx'


@pytest.fixture
def source():
    if not SOURCE.exists():pytest.skip('External reference not available')
    return build_project_config_draft(SOURCE,target_version='178A',base_project_path=ROOT/'cases/_templates/178A/config.xlsx').source


def changed(source, changes, drop=()):
    settings=[]
    for s in source.settings:
        identity=(s.key,s.block)
        if s.key in drop:continue
        if identity not in changes and s.key not in changes:
            settings.append(s)
            continue
        value=changes.get(identity,changes.get(s.key,s.raw_value))
        settings.append(replace(s,raw_value=value,evaluated_value=value))
    return replace(source,settings=tuple(settings))


def mapped(source,version='178A',**kwargs):
    path=ROOT/'cases/_templates'/version/'config.xlsx'
    draft=ConversionDraft(source,version,path,_read_project_schema(path),'manual','exact',**kwargs)
    _map_contract(source,draft)
    return draft


def test_missing_source_does_not_hide_other_fields(source):
    d=mapped(changed(source,{},drop=('N_qb',)))
    assert d.get('fixed_config','N_qb').status is MappingStatus.MISSING
    assert d.get('fixed_config','P_qc').value==1e-7
    assert d.get('fixed_config','fb').value==106.25e9
    noise_grid = d.get('fixed_config','noise_grid_num_ui')
    assert noise_grid.value is None
    assert noise_grid.status is MappingStatus.FALLBACK
    assert noise_grid.method == 'project default'
    assert area_for(noise_grid,'178A')=='policy'
    assert area_for(d.get('fixed_config','dy_rel_As'),'178A')=='policy'
    assert area_for(d.get('fixed_config','c_m2'),'178A')=='baseline'


def test_formula_without_cache_is_not_missing(source):
    fields=tuple(replace(s,raw_value='=2*3',evaluated_value=None) if s.key=='N_qb' else s for s in source.settings)
    d=mapped(replace(source,settings=fields))
    f=d.get('fixed_config','N_qb')
    assert f.status is MappingStatus.MISSING and 'cached result' in f.note


def test_testcase_selection_and_next_rx_block(source):
    tx,rx='PKG_LowR_CLASSA','PKG_HiR_CLASSB'
    s=changed(source,{'PKG_NAME':f'{tx} {rx}','z_p select':'[1 2]',('z_p (NEXT)',rx):'[11 22; 1 2]',('A_ne',rx):0.123})
    d=mapped(s)
    assert d.get('fixed_config','txpkg_next.device_pkg.z_p_seq').status is MappingStatus.MISSING
    d=mapped(s,package_selection=2)
    assert d.get('fixed_config','txpkg_next.device_pkg.z_p_seq').value=='22,2'
    assert d.get('fixed_config','A_ne').value==0.123


def test_reference_resistance_and_die_terminations_have_source_provenance(source):
    d = mapped(source)
    frequency_limit = d.get('fixed_config', 'sparam_frequency_limit_GHz')
    assert frequency_limit.value == pytest.approx(67.0)
    assert frequency_limit.status is MappingStatus.CONVERTED
    assert frequency_limit.source_key == 'flim'
    assert d.get('fixed_config', 'R_0').value == pytest.approx(46.25)
    assert d.get('fixed_config', 'R_d_tx').value == pytest.approx(46.25)
    assert d.get('fixed_config', 'R_d_rx').value == pytest.approx(46.25)
    assert d.get('fixed_config', 'R_d_tx').source_block == 'PKG_LowR_CLASSA'
    assert d.get('fixed_config', 'R_d_rx').source_block == 'PKG_LowR_CLASSA'
    for prefix in ('txpkg_victim', 'txpkg_fext', 'txpkg_next', 'rxpkg'):
        assert d.get('fixed_config', f'{prefix}.R0').value == pytest.approx(46.25)


def test_runtime_adapter_rejects_package_reference_impedance_mismatch():
    channel = COMChannelConfig(R0=46.25, R_d_tx=46.25, R_d_rx=46.25)
    matching = SimpleNamespace(R0=46.25)
    mismatch = SimpleNamespace(R0=50.0)
    _validate_channel_package_R0(channel, matching)
    with pytest.raises(ValueError, match=r"package\[1\]\.R0=50"):
        _validate_channel_package_R0(channel, matching, mismatch)


def test_93a_reduction_and_dfe_bounds(source):
    s=changed(source,{'MLSE':0,'N_b':3,'b_max(2..N_b)':0.2,'b_min(2..N_b)':-0.1})
    d=mapped(s,'93A')
    assert d.get('fixed_config','b_max').value=='0.85,0.2,0.2'
    assert d.get('fixed_config','b_min').value=='0,-0.1,-0.1'
    assert d.get('fixed_config','txpkg_victim.C_d').value==pytest.approx(1.1e-4*1e-9)
    assert d.get('fixed_config','txpkg_victim.z_p2').value is None


@pytest.mark.parametrize(
    ('n_bg', 'expected'),
    [
        (2, (6, 15, 87)),
        (0, (6, 15, 15)),
    ],
)
def test_178a_rx_ffe_layout_uses_source_tap_counts(source, n_bg, expected):
    d=mapped(changed(source,{
        'ffe_pre_tap_len':6,
        'ffe_post_tap_len':8,
        'N_f':80,
        'N_bg':n_bg,
    }))
    d_w, n_fix, n_max=expected
    assert d.get('fixed_config','d_w').value==d_w
    assert d.get('fixed_config','N_fix').value==n_fix
    assert d.get('fixed_config','N_max').value==n_max
    assert n_fix-d_w-1==8
    assert n_max-d_w-1==(80 if n_bg else 8)


def test_178a_rx_ffe_layout_rejects_floating_extent_before_fixed_taps(source):
    d=mapped(changed(source,{
        'ffe_pre_tap_len':6,
        'ffe_post_tap_len':8,
        'N_f':7,
        'N_bg':1,
    }))
    n_max=d.get('fixed_config','N_max')
    assert n_max.status is MappingStatus.MISSING
    assert 'N_max=14 must be at least N_fix=15' in n_max.note


def test_override_retains_failure_and_rejects_blank(source):
    d=mapped(source)
    f=d.get('fixed_config','mlsd_trunc_len')
    d.set_override('fixed_config','mlsd_trunc_len',128)
    assert f.original_status is MappingStatus.MISSING
    assert outcome(f,'178A',{x.identity:x.value for x in d.fields})=='success'
    d.set_override('fixed_config','mlsd_trunc_len',None)
    assert outcome(f,'178A',{x.identity:x.value for x in d.fields})=='fail'
    d.set_override('fixed_config','P_qc','abc')
    assert outcome(d.get('fixed_config','P_qc'),'178A',{})=='fail'


def test_mlsd_condition_is_not_reported_as_target_source(source):
    d=mapped(source)
    trunc=d.get('fixed_config','mlsd_trunc_len')
    delta=d.get('fixed_config','delta_com_an')
    assert trunc.status is MappingStatus.MISSING
    assert trunc.source_cell is None
    assert trunc.source_value is None
    assert trunc.condition_key=='MLSE'
    assert trunc.condition_value==1
    assert delta.status is MappingStatus.EMPTY
    assert delta.source_cell is None
    assert delta.condition_key=='MLSE'


def test_case_fields_have_explicit_provenance(source):
    d=mapped(source)
    case_id=d.get('fixed_config','case_id')
    source_config=d.get('fixed_config','source_config')
    source_note=d.get('fixed_config','source_note')
    assert case_id.method=='case input'
    assert 'case-folder name' in case_id.note
    assert source_config.method=='source provenance'
    assert source_config.source_value==str(source.source_path)
    assert source_note.method=='source provenance'
    assert source.descriptor.format_id in source_note.value
    assert source.source_sha256 in source_note.value


def test_unknown_source_and_unsupported_taps_block_export(source):
    item=replace(source.settings[0],key='unreviewed_model_control',raw_value=1,evaluated_value=1)
    d=mapped(replace(source,settings=source.settings+(item,)))
    assert any('unreviewed_model_control' in e for e in d.validation_errors())
    d=mapped(changed(source,{'c(-4)':0.1}))
    assert any('nonzero TX tap' in e for e in d.validation_errors())


def test_clear_optional_value_and_preserve_original_failure(source,tmp_path):
    d=mapped(source)
    d.set_override('fixed_config','case_id','optional')
    d.set_override('fixed_config','mlsd_trunc_len',128)
    d.set_override('fixed_config','delta_com_an',2.)
    channel=tmp_path/'channel.s4p';channel.write_text('# Hz S RI R 50\n')
    row={'S4P Path':str(channel),'Port Order':'1,2,3,4','Use':True}
    replace_channels(d,[('victim',row)])
    out=tmp_path/'cases/optional/178A/config.xlsx'
    write_project_config(d,out);write_conversion_audit(d,out)
    opened=load_existing_project(out,tmp_path)
    assert opened.get('fixed_config','mlsd_trunc_len').original_status is MappingStatus.MISSING
    opened.set_override('fixed_config','delta_com_an',None)
    save_existing_project(opened,out,tmp_path)
    assert load_existing_project(out,tmp_path).get('fixed_config','delta_com_an').value is None


@pytest.mark.parametrize('version',['93A','178A'])
def test_export_runtime_and_reopen(source,tmp_path,version):
    d=mapped(changed(source,{'MLSE':0}),version)
    d.set_override('fixed_config','case_id','review')
    channel=tmp_path/'channel.s4p';channel.write_text('# Hz S RI R 50\n')
    row={'S4P Path':str(channel),'Port Order':'1,2,3,4','Use':True}
    replace_channels(d,[('victim',row),('fext',row),('next',row)])
    channel_names={f.parameter.rsplit('.',1)[0] for f in d.fields if f.sheet=='channels'}
    assert channel_names=={'victim[0]','fext[1]','next[1]'}
    assert not d.validation_errors(),d.validation_errors()
    out=tmp_path/'cases/review'/version/'config.xlsx'
    write_project_config(d,out);write_conversion_audit(d,out)
    opened=load_existing_project(out,tmp_path)
    assert opened.get('fixed_config','fb').value==106.25e9
    assert opened.get('fixed_config','fb').status is MappingStatus.CONVERTED
    if version=='178A':
        assert opened.get('fixed_config','mlsd_trunc_len').condition_key=='MLSE'
    if version=='93A':
        from serdes_coding.io.com_excel_io_93A import excel_to_config_93A
        cfg=excel_to_config_93A(str(out))
        np.testing.assert_allclose(cfg.dfe.fixed_lower,[0])
    replace_channels(opened,[('victim',row)])
    opened.set_override('fixed_config','fb',100e9)
    save_existing_project(opened,out,tmp_path)
    again=load_existing_project(out,tmp_path)
    assert len([f for f in again.fields if f.sheet=='channels' and f.parameter.endswith('.S4P Path')])==1
    assert again.get('fixed_config','fb').value==100e9
    before=out.read_bytes()
    again.set_override('fixed_config','fb',None)
    with pytest.raises(ValueError):save_existing_project(again,out,tmp_path)
    assert out.read_bytes()==before


def test_gui_separates_mapping_and_policy(source):
    import tkinter as tk
    from serdes_coding.interfaces.com_config_conversion_gui import COMConfigConversionGui
    root=tk.Tk();root.withdraw()
    try:
        gui=COMConfigConversionGui(root)
        gui.draft=mapped(source)
        gui._populate_packages();gui._refresh();root.update_idletasks()
        assert len(gui.trees['mapping'].get_children())==len(rules_for('178A'))
        assert all(area_for(f,'178A')=='mapping' for (tree,_),f in gui.row_fields.items() if tree==gui.trees['mapping'])
        with patch('serdes_coding.interfaces.com_config_conversion_gui.messagebox.askyesno',return_value=False):
            gui.dirty=True;gui.version.set('93A');gui._version_changed()
            assert gui.version.get()=='178A'
        assert gui.package_selection.get()=='1'
    finally:root.destroy()
