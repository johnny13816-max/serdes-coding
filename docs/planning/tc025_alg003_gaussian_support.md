# TC-025 — ALG-003 Gaussian `pmf_sample` 固定 ±8σ

狀態：**Closed 2026-11-11**

批准：使用者於 2026-11-11 明確核准 TC-025
權威設計：[178A Branch Registry](../models/178A/branch_behavior_registry.md)

## 問題與決策

ALG-003 只選擇 PDF→PMF discretization；Gaussian initial support 是獨立的
固定 ±8σ invariant。原 `gaussian_from_pmf_sample()` 使用
`round(2 * n_sigma * sigma / dx)`，使 reference option 在 178A 的固定
`n_sigma=8` 下建立約 ±16σ support。核准後收斂為
`round(n_sigma * sigma / dx)`，不改 grid-center sampling 或 normalization。

## Scope

```text
cfg.alg.pdf_to_pmf_method
└─ model injectors                         unchanged
   └─ Pmf1D.gaussian()/uniform()           ALG-003 L5 owner set
      └─ gaussian_from_pmf_sample()        ±16σ → fixed ±8σ
```

- 只修改 `src/serdes_coding/utilities/pmf.py` 的 Gaussian sampled-support extent。
- `bin_integral`、uniform construction、ALG-002、ALG-004、NUM-006 與 93A 不變。
- `sicopr_reference_v1` 仍選 `pmf_sample`；只有 Gaussian initial array support
  收斂到已接受的固定 ±8σ boundary。

## Validation

1. constructor isolation：兩種 Gaussian discretization 使用同一 ±8σ x-grid；
2. ALG-003 policy/profile focused tests；
3. Python 3.7 standalone export rebuild／validation；
4. 固定 SiCoPR production golden，沿用既有 final tolerances 與 digests；
5. 不修改 golden 或放寬 tolerance。若數值超出既有 acceptance，停止並重新分類。

## Integration

Protected implementation 已由 isolated commit `e65f644` 整合並推送；Branch
Contract、唯一 Registry、config/stage references 的權威文件更新已由 `c804e3c`
隔離提交。Closure audit 確認 selector、所有 production callers、L5 owner set、
固定 ±8σ invariant 與 validation evidence 一致；closure-state commit 同步目前狀態。
本文件在整輪 branch review 後依 handoff cleanup 決策移除，不作第二份權威設計。

## Validation result

- Project interpreter：`.venv/Scripts/python.exe`；NumPy 2.5.3、SciPy 1.18.1、pytest 9.1.1。
- Focused ALG-003／policy／ownership tests：`47 passed`。
- 初次 focused run：`40 passed / 7 setup errors`；原因是 sandbox 預設 pytest
  Temp 無法建立 numbered directory。改用 `%TEMP%` 專用 `--basetemp` 後完整通過，
  不是算法 failure。
- Python 3.7 standalone export rebuild／validation：passed。
- 固定 SiCoPR production golden：`1 passed`；既有 MSE、COM_DFE、final COM
  tolerances 與三個 frozen intermediate digests 全數通過，未修改 golden。
