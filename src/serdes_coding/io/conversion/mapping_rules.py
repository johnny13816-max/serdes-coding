"""Versioned mapping contract shared by conversion, review and validation.

Only rules in this module belong in the Ad Hoc mapping view. Template policy
defaults and case/channel input are separate, even if they share a sheet.
"""
from dataclasses import dataclass
from typing import Callable
from functools import lru_cache

import numpy as np


@dataclass(frozen=True)
class MappingRule:
    sheet: str
    parameter: str
    sources: str
    method: str
    description: str
    evaluate: Callable
    optional: Callable = lambda values: False


class MappingContext:
    def __init__(self, source, selection=None, tx=None, rx=None):
        self.source = source
        self.selection = selection
        self.tx = tx
        self.rx = rx
        self.reads = []
        self.conditions = []

    def get(self, key, block=None, *, condition=False):
        item = self.source.require_one(key, block=block)
        (self.conditions if condition else self.reads).append(item)
        if isinstance(item.raw_value, str) and item.raw_value.startswith('=') and item.evaluated_value is None:
            raise ValueError(f'{item.sheet}!{item.value_cell}: formula has no cached result; recalculate the source in Excel.')
        value = item.value
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f'{key}: source value is blank')
        return value

    def number(self, key, block=None):
        return scalar(self.get(key, block))

    def integer(self, key, block=None):
        value = self.number(key, block)
        if not value.is_integer():
            raise ValueError(f'{key} must be an integer')
        return int(value)

    def condition_integer(self, key, block=None):
        value = scalar(self.get(key, block, condition=True))
        if not value.is_integer():
            raise ValueError(f'{key} must be an integer')
        return int(value)

    def profiles(self):
        names = str(self.get('PKG_NAME')).split()
        if len(names) != 2:
            raise ValueError('PKG_NAME must identify TX and RX profiles')
        tx, rx = self.tx or names[0], self.rx or names[1]
        if any(x not in self.source.descriptor.signature_blocks for x in (tx, rx)):
            raise ValueError('Selected package profile is not supported by this source format')
        return tx, rx

    def testcase(self):
        choices = array(self.get('z_p select')).ravel()
        if any(x < 1 or x != int(x) for x in choices):
            raise ValueError('z_p select requires positive integer indices')
        selected = self.selection
        if selected is None:
            if len(choices) != 1:
                raise ValueError('Choose one package testcase from z_p select')
            selected = int(choices[0])
        if selected not in choices:
            raise ValueError(f'Testcase {selected} is not offered by z_p select')
        return int(selected)-1


def array(value):
    if isinstance(value, (list, tuple, np.ndarray, int, float, np.number)):
        result = np.atleast_1d(np.asarray(value, dtype=float))
    else:
        rows = []
        for row in str(value).strip().strip('[]').split(';'):
            terms = row.replace(',', ' ').split()
            numbers = []
            for term in terms:
                if ':' in term:
                    parts = [float(v) for v in term.split(':')]
                    lo, step, hi = parts if len(parts) == 3 else (parts[0], 1., parts[1])
                    if step == 0 or (hi-lo)/step < 0:
                        raise ValueError('Invalid source range direction/step')
                    count = int(np.floor((hi-lo)/step+1e-9))+1
                    if count > 100000:
                        raise ValueError('Source range is too large')
                    numbers.extend(lo + step*np.arange(count))
                else:
                    numbers.append(float(term))
            if numbers:
                rows.append(numbers)
        if not rows:
            raise ValueError('Source array is empty')
        result = np.asarray(rows[0] if len(rows)==1 else rows, dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError('Source values must be finite')
    return result


def scalar(value):
    result = array(value).ravel()
    if result.size != 1:
        raise ValueError('A scalar is required; source contains multiple values')
    return float(result[0])


def sequence(value):
    return ','.join(f'{v:.15g}' for v in np.asarray(value).ravel())


def side_values(value, side):
    values = array(value)
    return values if values.ndim == 1 else values[side, :]


def selected_lengths(c, key, block):
    values = array(c.get(key, block))
    index = c.testcase()
    if values.ndim == 1:
        # Source rows are segments and columns are testcases, also for a
        # single-segment row. Do not treat a row of cases as a segment list.
        values = values.reshape(1, -1)
    if index >= values.shape[1]:
        raise ValueError(f'{key}: testcase {index+1} is outside source columns')
    return values[:, index]


def is_enabled(value):
    if isinstance(value, str):
        return value.strip().lower() in {'1','true','yes','on'}
    return bool(value)


@lru_cache(maxsize=2)
def rules_for(version):
    rules = []
    def add(target, source, fn=None, *, method='direct', note='', sheet='fixed_config', optional=None):
        rules.append(MappingRule(sheet, target, source, method, note or source,
                                 fn or (lambda c,k=source: c.number(k)),
                                 optional or (lambda values: False)))
    for target, source, scale in [('fb','f_b',1e9),('target_df','Delta_f',1e9),('Tr','T_r',1e-9),('eta_0','eta_0',1e-9)]:
        add(target,source,lambda c,k=source,s=scale:c.number(k)*s,method='converted',note=f'{source} × {scale:g}; keyword units govern')
    add('per_ui','M',lambda c:c.integer('M'))
    add('fr','f_r, f_b',lambda c:c.number('f_r')*c.number('f_b')*1e9,method='derived',note='f_r × f_b × 1e9 Hz')
    for name in ('R_LM','SNR_TX','sigma_RJ','A_DD','L','DER_0','N_b'):
        add(name,name,(lambda c,k=name:c.integer(k)) if name in {'L','N_b'} else None)
    add('c_m3','c(-3)')
    add('num_pre','TX tap layout',lambda c:3,method='derived',note='Main index of [c(-3), c(-2), c(-1), c(0), c(1)]')
    frequencies = [('f_z1','f_z'),('f_z2','f_HP_PZ'),('f_p3','f_HP_PZ')] if version=='178A' else [('f_z','f_z'),('f_LF','f_HP_PZ')]
    for target,key in frequencies+[('f_p1','f_p1'),('f_p2','f_p2')]:
        add(target,key,lambda c,k=key:c.number(k)*1e9,method='converted',note='GHz to Hz')
    gains = ('g_1','g_2') if version=='178A' else ('g_DC','g_DC2')
    for target,key in [('c_m2','c(-2)'),('c_m1','c(-1)'),('c_1','c(1)'),(gains[0],'g_DC'),(gains[1],'g_DC_HP')]:
        add(target,key,lambda c,k=key:sequence(array(c.get(k))),method='converted',note='Source search range; single-run baseline is separate',sheet='search_config')
    if version=='178A':
        def sparam_frequency_limit_GHz(c):
            value = c.number('flim')
            return value / 1e9 if value >= 1000.0 else value
        add(
            'sparam_frequency_limit_GHz',
            'flim',
            sparam_frequency_limit_GHz,
            method='converted',
            note='COM flim converted to an explicit GHz channel-ingestion boundary',
        )
        direct = {'c_0_min':'c(0)','b_first_max':'b_max(1)','b_first_min':'b_min(1)',
                  'w_pre1_max':'ffe_pre_tap1_max','w_post1_max':'ffe_post_tap1_max',
                  'N_wg':'N_bg','N_wf':'N_bf','w_fixed_rest_max':'ffe_tapn_max',
                  'w_float_max':'bmaxg','b_rest_max':'b_max(2..N_b)','b_rest_min':'b_min(2..N_b)',
                  'N_qb':'N_qb','P_qc':'P_qc','mlsd_enable':'MLSE'}
        for target,key in direct.items():
            fn=(lambda c,k=key:c.integer(k)) if target in {'N_wg','N_wf','N_qb','mlsd_enable'} else None
            add(target,key,fn)
        # Table 178A-10 / Eq. 178A-30/31 use tap counts, not zero-based
        # tap indices: d_w counts precursors, and N_fix includes precursor,
        # main cursor, and fixed postcursors.
        add('d_w','ffe_pre_tap_len',lambda c:c.integer('ffe_pre_tap_len'),method='derived',note='precursor count = ffe_pre_tap_len')
        add('N_fix','ffe_pre_tap_len, ffe_post_tap_len',lambda c:c.integer('ffe_pre_tap_len')+1+c.integer('ffe_post_tap_len'),method='derived',note='precursors + main cursor + fixed postcursors')
        def n_max(c):
            n_fix=c.integer('ffe_pre_tap_len')+1+c.integer('ffe_post_tap_len')
            n_max=n_fix if c.integer('N_bg')==0 else c.integer('ffe_pre_tap_len')+c.integer('N_f')+1
            if n_max<n_fix:
                raise ValueError(f'N_max={n_max} must be at least N_fix={n_fix}')
            return n_max
        add('N_max','ffe_pre_tap_len, ffe_post_tap_len, N_bg, N_f',n_max,method='derived',note='N_fix when N_bg=0; otherwise precursor count + N_f + main cursor')
        add('w_float_min','bmaxg',lambda c:-c.number('bmaxg'),method='derived',note='-bmaxg')
        inactive=lambda values:not is_enabled(values.get(('fixed_config','mlsd_enable')))
        def mlsd(c,key,integer=False,optional=False):
            if c.condition_integer('MLSE')==0:
                return None
            if optional and not c.source.find_all(key):
                return None
            return c.integer(key) if integer else c.number(key)
        def trunc(c):
            key='N_tc' if c.source.find_all('N_tc') else 'trunc'
            return mlsd(c,key,True)
        add('mlsd_trunc_len','N_tc (preferred), trunc',trunc,optional=inactive,note='Required when MLSE is enabled; no 128 default')
        add('minimum_com_limit','COM Pass threshold',lambda c:mlsd(c,'COM Pass threshold'),optional=inactive)
        add('delta_com_an','add_rx_noise',lambda c:mlsd(c,'add_rx_noise',optional=True),optional=lambda values:True,note='Optional; runtime owns fallback to minimum_com_limit')
    else:
        def dfe(c,limit):
            n=c.integer('N_b')
            if n==0:return 0.
            bounds=[c.number(f'{limit}(1)')]+([c.number(f'{limit}(2..N_b)')]*(n-1))
            return sequence(bounds) if n>1 else bounds[0]
        for limit in ('b_max','b_min'):
            add(limit,f'N_b, {limit}(1), {limit}(2..N_b)',lambda c,k=limit:dfe(c,k),method='derived',note='First-tap limit followed by N_b-1 remaining-tap limits')
    for prefix,length_key,side in [('txpkg_victim','z_p (TX)',0),('txpkg_fext','z_p (FEXT)',0),('txpkg_next','z_p (NEXT)',0),('rxpkg','z_p (RX)',1)]:
        profile=lambda c,s=side:c.profiles()[s]
        length_profile=lambda c,p=prefix,s=side:c.profiles()[1 if p=='txpkg_next' else s]
        if version=='178A':
            for name,key in [('C_d_seq','C_d'),('L_s_seq','L_s')]:
                add(f'{prefix}.device_term.{name}',key,lambda c,k=key,s=side:sequence(side_values(c.get(k),s)*1e-9),method='converted',note='Selected TX/RX device row; nF/nH to SI')
            add(f'{prefix}.device_term.C_b','C_b',lambda c,s=side:array(c.get('C_b')).ravel()[s]*1e-9,method='converted')
            add(f'{prefix}.device_pkg.z_p_seq',length_key,lambda c,k=length_key,p=length_profile:sequence(selected_lengths(c,k,p(c))),method='converted',note='Selected testcase column; NEXT lengths use RX profile')
            add(f'{prefix}.device_pkg.Z_c_seq','package_Z_c',lambda c,s=side,p=profile:sequence(array(c.get('package_Z_c',p(c)))[:,s]),method='converted')
            pkg=f'{prefix}.device_pkg'
        else:
            for name in ('C_d','L_s'):
                add(f'{prefix}.{name}',name,lambda c,k=name,s=side:float(np.max(side_values(c.get(k),s)))*1e-9,method='reduced',note='Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI')
            add(f'{prefix}.C_b','C_b',lambda c,s=side:array(c.get('C_b')).ravel()[s]*1e-9,method='converted')
            add(f'{prefix}.z_p',length_key,lambda c,k=length_key,p=length_profile:float(np.max(selected_lengths(c,k,p(c)))),method='reduced',note='Approved maximum selected testcase segment; no second segment')
            add(f'{prefix}.z_p2',length_key,lambda c:None,method='reduced',optional=lambda values:True,note='Maximum reduction uses one segment; second segment disabled')
            for z in ('Z_c','Z_c2'):
                add(f'{prefix}.{z}','package_Z_c',lambda c,s=side,p=profile:float(np.max(array(c.get('package_Z_c',p(c)))[:,s])),method='reduced',note='Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty')
            add(f'{prefix}.enable','PKG_NAME',lambda c:True,method='derived',note='Construct source profile including PKG_Null zero elements; no whole-package bypass inferred')
            pkg=prefix
        for index,name in enumerate(('gamma_0','a1','a2')):
            def gamma(c,i=index,p=profile):
                vals=array(c.get('package_tl_gamma0_a1_a2',p(c))).ravel()
                if len(vals)!=3:raise ValueError('TL coefficients must have exactly three entries')
                return float(vals[i])
            add(f'{pkg}.{name}','package_tl_gamma0_a1_a2',gamma,method='converted',note=f'Selected profile coefficient {index+1}; no maximum across different coefficients')
        add(f'{pkg}.tau','package_tl_tau',lambda c,p=profile:c.number('package_tl_tau',p(c)))
        add(f'{pkg}.C_p','C_p',lambda c,s=side,p=profile:array(c.get('C_p',p(c))).ravel()[s]*1e-9,method='converted')
        add(f'{prefix}.R0','R_0')
        if version=='178A':
            def enabled(c,s=side):
                mode=c.integer('Include PCB')
                if mode not in (0,1,2):raise ValueError('Include PCB must be 0, 1 or 2')
                return mode==1 or (mode==2 and s==1)
            add(f'{prefix}.partial_host.enable','Include PCB',enabled,method='derived')
            for name,key in [('C_0','C_0'),('C_1','C_1')]:
                add(f'{prefix}.partial_host.{name}',key,lambda c,k=key,s=side:array(c.get(k)).ravel()[s]*1e-9,method='converted')
            add(f'{prefix}.partial_host.z_h',length_key.replace('z_p','z_bp'))
            add(f'{prefix}.partial_host.Z_h','board_Z_c')
            for i,name in enumerate(('gamma_0','a1','a2')):
                add(f'{prefix}.partial_host.{name}','board_tl_gamma0_a1_a2',lambda c,i=i:array(c.get('board_tl_gamma0_a1_a2')).ravel()[i],method='converted')
            add(f'{prefix}.partial_host.tau','board_tl_tau')
    for name in ('A_v','A_fe','A_ne'):
        add(name,name,lambda c,k=name:c.number(k,c.profiles()[1 if k=='A_ne' else 0]),note='A_ne uses RX profile; A_v/A_fe use TX profile')
    add('R_0', 'R_0')
    add(
        'R_d_tx',
        'R_d',
        lambda c: float(array(c.get('R_d', c.profiles()[0])).ravel()[0]),
        method='converted',
        note='TX-side die termination from the selected TX package profile',
    )
    add(
        'R_d_rx',
        'R_d',
        lambda c: float(array(c.get('R_d', c.profiles()[1])).ravel()[1]),
        method='converted',
        note='RX-side die termination from the selected RX package profile',
    )
    return {(r.sheet,r.parameter):r for r in rules}


CASE_FIELDS={'case_id','source_config','source_note','case_source'}
BASELINES={'c_m2','c_m1','c_1','g_1','g_2','g_DC','g_DC2'}
POLICY_FIXED={'dy_rel_As','dy_abs_max','tap_rel_As','gaussian_n_sigma','keep_mass','missing_dc_policy'}
POLICY_FIXED_178A={
    'align_to_ref',
    'out_of_measured',
    'channel_renormalization_order',
    'pre_dte_adc_clipping_convention',
    'final_adc_quantization_convention',
    'noise_grid_num_ui',
}
SEARCH_POLICY={'keep_top_n','keep_all_rows','continue_on_error'}
# These source controls belong to MATLAB reporting, TDR/ERL/ICN calculations,
# or execution implementations. They are explicitly outside COM input mapping.
SOURCE_EXTERNAL_CONTROLS={
    'Parameter','DIAGNOSTICS','DISPLAY_WINDOW','CSV_REPORT','RESULT_DIR','SAVE_FIGURES','RUNTAG',
    'COM_CONTRIBUTION','TDR','ERL','ERL_ONLY','TR_TDR','N','TDR_Butterworth','beta_x','rho_x',
    'TDR_W_TXPKG','N_bx','fixture delay time','Tukey_Window','Z_t','ERL Pass threshold','FORCE_TR',
    'PMD_type','EW','ts_anchor','sample_adjustment','Local Search','zero_pad',
    'N_tail_start','TS_SRCH_MODE','Non-zero Local Search Method','Clip Method',
    'num_ui_RXFF_noise',
    'SAVE_CONFIG2MAT','RX_CALIBRATION','Sigma BBN step','T_t','f_v','T_ft','T_nt','f_f','f_n',
    'f_1','f_2','A_ft','A_nt','f_min',
}


def area_for(field, version):
    if field.sheet=='channels':return 'channels'
    if field.sheet=='fixed_config' and field.parameter in CASE_FIELDS:return 'case'
    if field.identity in rules_for(version):return 'mapping'
    if field.sheet=='fixed_config' and field.parameter in BASELINES:return 'baseline'
    if field.sheet=='fixed_config' and field.parameter in POLICY_FIXED:return 'policy'
    if field.sheet=='fixed_config' and version=='178A' and field.parameter in POLICY_FIXED_178A:return 'policy'
    if field.sheet=='search_config' and field.parameter in SEARCH_POLICY:return 'policy'
    if field.sheet=='run_config' and version=='178A':return 'policy'
    return 'unregistered'


def optional_field(field, version, values):
    if version=='178A':
        if field.sheet=='fixed_config' and field.parameter=='noise_grid_num_ui':
            return True
        if field.sheet=='run_config' and field.parameter.endswith('.pmf_dy_override'):
            return True
    rule=rules_for(version).get(field.identity)
    return bool(rule and rule.optional(values))


def outcome(field, version, values):
    from .draft import MappingStatus
    if field.status in {MappingStatus.MISSING,MappingStatus.UNSUPPORTED,MappingStatus.MANUAL}:
        return 'fail'
    blank=field.value is None or (isinstance(field.value,str) and not field.value.strip())
    if blank:return 'empty' if optional_field(field,version,values) else 'fail'
    if field.parameter.endswith('.enable') or field.parameter in {'mlsd_enable','keep_all_rows','continue_on_error'}:
        return 'success' if str(field.value).lower() in {'true','false','1','0'} else 'fail'
    if area_for(field,version) in {'mapping','baseline'} or str(field.unit).lower() not in {'text','enum','none',''}:
        try:
            numbers=array(field.value)
            if field.parameter in {'N_b','N_qb','N_wg','N_wf','N_fix','N_max','num_pre','d_w','per_ui','L','mlsd_trunc_len','noise_grid_num_ui'}:
                if np.any(numbers!=np.floor(numbers)) or np.any(numbers<0):return 'fail'
            if field.parameter=='mlsd_trunc_len' and np.any(numbers<=0):return 'fail'
        except (ValueError,TypeError):return 'fail'
    return 'success'
