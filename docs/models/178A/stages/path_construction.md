# 178A path-construction stage

> **Review state:** the software boundary, configuration ownership, data flow, status output, and failure behavior below are confirmed from current source. The individual S-parameter and filter equations have not been independently revalidated by this documentation change.

## Purpose and ownership

This stage converts workbook-derived channel, package, and filter configuration into the ordered `COMPath` objects used by every later 178A stage.

The complete implementation lives in
`src/serdes_coding/models/com_178a/path_stage.py`. `com_model_178A.py` imports
and re-exports its established symbols for compatibility, but does not own the
path algorithms.

It owns:

- loading and aligning the measured victim, NEXT, and FEXT S-parameter files;
- constructing the shared RX package and shared scalar filters;
- constructing the path-specific TX package, augmented S-parameter network, transfer responses, symbol pulse, and time-domain pulse;
- preserving victim/NEXT/FEXT order and package selection.

It does not own sampling-phase selection, impairment PSDs, DTE coefficients, PMFs, COM, search ranking, or plotting.

## Governing references

Current source identifies these specification-facing builders:

| Functional block | Reference named by current source | Validation state |
|---|---|---|
| device termination ladder | IEEE 802.3 Annex 178A, Eq. 178A-7 | implementation reference recorded; equation not revalidated here |
| device package | IEEE 802.3 Annex 178A, Eq. 178A-9 | implementation reference recorded; equation not revalidated here |
| partial host | IEEE 802.3 Annex 178A, Eq. 178A-10 | implementation reference recorded; equation not revalidated here |
| augmented path transfer | Annex 178A path-transfer definition; implemented through shared `SparamModel.to_LinkSegment()` | conversion boundary confirmed from source; equation not revalidated here |

The 178A concrete `IEEECOMSparam` and `IEEECOMFilter` types directly inherit
the neutral `SparamModel` and `LinkSegment` utilities. They own the COM
primitive implementations used by this stage. `_93A`-named methods remain thin
public compatibility wrappers; the 178A stage calls version-owned canonical
methods without a version suffix. No 178A path operation imports a 93A model
class or channel loader.

## Entry and result

```text
COM.build_all_paths() -> list[COMPath]
```

The returned order is fixed:

```text
index 0                  victim
next indices             NEXT paths in workbook/config order
remaining indices        FEXT paths in workbook/config order
```

`COM._run_once()` assigns this list to `status.paths`, selects `paths[0]` as the victim, treats `paths[1:]` as crosstalk paths, and then performs the victim time-alignment guard before entering pre-DTE processing.

## Required input objects

| Input | Fields used by this stage | Role |
|---|---|---|
| `COMConfig.link` | frequency/time grid and symbol timing consumed by filter and response constructors | common response grid |
| `COMConfig.channel` | victim/NEXT/FEXT paths, port order, `R0`, source/load reflection coefficients, `missing_dc_policy`, optional `sparam_frequency_limit_Hz` | measured channel ingestion and transfer conversion |
| `COMConfig.policy.out_of_measured` | shared `cosine_decay`／`zero_padding` policy | measured-to-analysis-grid conversion of terminated scalar `H_21` |
| `COMConfig.policy.channel_renormalization_order` | `sdd_first`／`s4p_first` for six measured channels | S4P ingestion before package cascade |
| `COMConfig.policy.ctle_pulse_realization` | `continuous_tf`／`bilinear_iir` | composite pre-CTLE response to pulse realization |
| `COMConfig.filter` | TX FFE taps and cursor constraint, transition time, receiver filter/equalizer controls, victim/NEXT/FEXT amplitudes | shared and path-specific scalar responses |
| `txpkg_victim` | nested termination/package/partial-host config | victim TX package |
| `txpkg_next` | nested termination/package/partial-host config | NEXT TX package |
| `txpkg_fext` | nested termination/package/partial-host config | FEXT TX package |
| `rxpkg` | nested termination/package/partial-host config | shared RX package |

The exact field and workbook mappings are authoritative in [Configuration tree](../config_tree.md). This stage receives resolved runtime config and does not read the workbook `execution_profile` selector directly.

No `COMRunConfig` field controls path construction. Search candidates affect this stage only because search creates a copied `COMConfig.filter` with concrete TX FFE and CTF gains before calling the model.

## Output ownership

Every returned path references one shared `COMSharedPath` instance:

```text
COMSharedPath
├── H_ffe
├── H_ffe_next
├── H_t
├── S_rx
├── H_r
├── H_ctf
└── ctle_iir: COMBilinearCTLE | None
```

Each `COMPath` adds path-specific data:

```text
COMPath
├── kind
├── shared
├── S_tx
├── S_ch
├── S_all
├── H_21
├── H_all
├── X
└── pulse
```

The full types and lifecycle are defined in [Status tree](../status_tree.md). The stage replaces `status.paths` as one list; it does not merge individual paths into an existing list.

## Ordered functional blocks

### 1. Load and align measured channels

```text
_build_channel_under_test(channel_cfg, renormalization_order)
├── read raw single-ended S4P without conversion
├── sdd_first: optional frequency limit -> s4p_to_s2p()
│   └── renormalized(2*R_0) in the differential two-port domain
└── s4p_first: renormalized(R_0) on the full S4P
    └── optional frequency limit -> s4p_to_s2p()
preserve victim -> NEXT -> FEXT order
align all six Sdd channels to one measured-domain intersection grid
```

Grid alignment uses the overlapping measured frequency band. It performs in-band interpolation and does not intentionally extrapolate the S-parameter files to the model FFT grid at this point.
When `sparam_frequency_limit_Hz` is set, ingestion retains the first measured
sample at or above the requested limit and discards later samples. A file that
ends below the requested limit remains unchanged. For `s4p_first`, the order is
full S4P renormalization, frequency limit, then mixed-mode Sdd conversion.
The policy selects the ingestion order only; `_build_path()` never renormalizes
an already constructed `S_ch`. The default `sdd_first` retains the original
two-port path, while the SiCoPR case selects `s4p_first`.
The representation and conversion API is defined by the
[S-parameter model contract](../../../architecture/sparameter_model_contract.md).

### 2. Build shared responses

```text
_build_shared_path(cfg, channel_freqs)
├── _build_H_ffe(...)
├── _build_H_ffe_next(...)
├── _build_H_t(...)
├── _build_rxpkg(...)
├── _build_H_r(...)
└── _build_H_ctf(...)
```

The victim and FEXT paths use the configured TX FFE. NEXT uses a fixed
unity/main-cursor TX FFE response. All paths share the RX package,
transition-time response, receiver-noise response, and continuous CTF object.
When `ctle_pulse_realization="bilinear_iir"`, `_build_shared_path()` also builds
one `COMBilinearCTLE` containing the two digital sections and `Fs`; all six path
objects and the TX-noise pulse reuse it. The continuous method stores `None`.

TX FFE 的 tap 陣列以 `num_pre` 標出 main cursor；頻域指數使用規範索引 `n = idx - num_pre`（Eq. 178A-13），因此 `c(0)` 的相位為零。Victim/FEXT 共用此設定，NEXT 的 `[0, 1, 0]` 在 `num_pre=1` 時為全頻 unity。這項時間原點契約只作用於 TX FFE，不改變 S-parameter cascade 或 tap 幅度。

### 3. Build package networks

TX package order in current source:

```text
device termination -> device package -> partial host
```

RX package order in current source:

```text
partial host -> device package -> device termination
```

`partial_host.enable=False` returns an identity-equivalent two-port for that block. Package construction uses the channel's aligned measured frequency grid.

### 4. Build every path

`_build_paths()` verifies that the number of loaded channels equals one victim plus configured NEXT and FEXT counts. It then chooses the TX package, TX FFE, and rectangular-pulse amplitude by `kind`:

| Kind | TX package | TX FFE | Pulse amplitude |
|---|---|---|---|
| victim | `txpkg_victim` | configured shared `H_ffe` | `A_v` |
| NEXT | `txpkg_next` | shared `H_ffe_next` | `A_ne` |
| FEXT | `txpkg_fext` | configured shared `H_ffe` | `A_fe` |

For each path, current source performs these semantic operations:

```text
S_tx + S_ch + S_rx cascade
          -> S_all
S_all plus source/load mismatch and missing-DC policy
          -> H_21 on measured grid
SparamModel.to_LinkSegment -> LinkSegment.from_tf -> resample_tf
          -> H_21 on analysis grid, applying out_of_measured above measured f_max
H_ffe + H_t + H_21 + H_r cascade
          -> pre-CTLE response
pre-CTLE response + selected CTLE realization
          -> post-CTLE response
post-CTLE response + common rectangular symbol pulse
          -> pulse
pre-CTLE response + continuous H_ctf
          -> H_all for VTF/reporting
```

`ctle_pulse_realization` 控制完整的 pre-CTLE-to-pulse realization。
TX FFE 在上游依 path kind 選定並完成串接，不屬於 CTLE 分支。
`_realize_ctle_response()` 擁有 CTLE method selection；
`_apply_rectangular_unit_pulse()` 擁有共同的一 UI symbol-pulse formation。
`continuous_tf` 直接在 analysis grid 串接 continuous CTF 與 unit-pulse TF。
`bilinear_iir` 則由 `_evaluate_pre_ctle_on_measured_grid()` 重建 measured-domain
composite TF，經 `_reference_fd_to_td_record()` 建立 reference spacing 的 raw
IFFT finite record、保留 3Tr 時間原點、停用 causality correction，並以固定
`1e-3` peak threshold 截尾，再通過共用 `COMBilinearCTLE` 與 boxcar unit pulse。
這些是該具名方法的固定定義，不拆成額外 policy 欄位。
後者依前者的 frequency／finite-record 表示法保留原本的 convolution semantics，
但不引入額外 project policy。

`_build_path()` forwards the chosen policy; it does not edit the resulting
sampled response. `SparamModel.to_LinkSegment()` owns the S-parameter-to-link
boundary, and `LinkSegment.from_tf()`／`resample_tf()` own numerical frequency
extension. `cosine_decay` retains the existing extrapolation; `zero_padding`
sets the complex terminated `H_21` strictly to zero only above the measured
input's effective highest frequency. The endpoint sample stays unchanged.
The optional frequency limit is applied earlier at `SparamModel` ingestion, so
it intentionally changes the measured-domain `S_ch` used by package cascade.
The Akinwale case records its raw 100 GHz files and explicit 67 GHz limit in
the channel config; it does not rely on a temporary truncated copy.

The notation above denotes software cascade order and object ownership. It is not a replacement for the specification equations.

## Fixed-policy control

`COMChannelConfig.missing_dc_policy` is the path stage's project-defined fixed policy:

| Value | Intended software behavior |
|---|---|
| `error` | reject a transfer conversion that lacks the required DC sample |
| `hold` | use the project's hold-style DC completion |
| `skrf` | use the scikit-rf-backed DC handling path |

The chosen policy is passed to `S_all.to_LinkSegment(...)`. It is shared by every victim and aggressor path in one config.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- victim channel path is absent;
- a Touchstone file cannot be read or converted with the configured port order/reference impedance;
- channel grids have no valid common alignment domain;
- loaded channel count differs from configured victim plus NEXT plus FEXT count;
- channel and shared RX-package frequency grids differ at path construction;
- a path kind is outside `victim`, `next`, or `fext`;
- the configured TX FFE violates its main-cursor constraint;
- required CTF fields are absent or its pole values are invalid;
- package nested types, dimensions, or values fail their dataclass validation;
- transfer conversion cannot satisfy the selected missing-DC policy;
- the victim time-alignment guard fails immediately after this stage in `_run_once()`.

This stage does not downgrade errors to search rows. The search layer decides whether a raised error is `infeasible`, recorded as `error`, or propagated.

## Downstream consumers

| Consumer | Data read |
|---|---|
| pre-DTE common impairment | victim path plus every aggressor `pulse.ir` |
| per-phase pre-DTE impairment | victim `pulse`, `H_t`, `H_21`, `H_r`, and `H_ctf` through path proxies/fields |
| post-FFE impairment | selected victim `pulse.ir` |
| path reporting | stored `S_tx`, `S_ch`, `S_all`, `H_21`, `H_all`, `X`, `pulse`, and shared responses |
| search | rebuilds this entire stage for each concrete filter candidate |

Reporting reads stored `COMPath` objects. It must not recreate packages, filters, cascades, or pulses from config.

## Validation evidence and tolerance

Dedicated ownership and numerical regression tests cover both channel-ingestion
branches, the six-path order, and stored `S_tx`, `S_ch`, `S_all`, `H_21`,
`H_all`, pulse, and shared-response boundaries. Production 93A/178A golden
tests and a single-candidate production search protect the downstream result.
The exact baseline, tolerances, commands, and results are recorded in
[ARC-178A-004B validation](../../../validation/arc_178a_004b.md).

These tests establish behavior preservation across the ownership migration;
they do not independently certify every equation against the specification.
Case placement and channel ownership follow
[Project structure](../../../architecture/project_structure.md).

## Known limitations and unresolved questions

- The implementation reference annotations for the termination, package, partial-host, and augmented-transfer equations still need a spec-by-spec numerical review.
- `isNext` is accepted by `_build_txpkg()` but does not currently select different construction inside that helper; NEXT behavior differs through `txpkg_next`, `H_ffe_next`, and `A_ne` supplied by the caller.
