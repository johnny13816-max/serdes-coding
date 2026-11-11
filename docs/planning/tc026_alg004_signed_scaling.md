# TC-026 — ALG-004 signed scalar-PMF scaling

狀態：**Closed 2026-11-11**

批准：使用者於 2026-11-11 明確核准 ALG-004 change contract

權威設計：[178A Branch Registry](../models/178A/branch_behavior_registry.md)

## Contract

- L5 `Pmf1D.scale_x()` 保持 sole semantic owner，public signature 不變。
- `mass_deposit` 縮放 probability mass，並委派 ALG-002 `linear/nearest` placement。
- `interpolate_ordinates` 以 `abs(scale)` 建立 reference interpolation grid；
  `+a`／`-a` 的 `dx/st_idx/x/support` 相同，負值只反轉 PMF ordinates。
- `scale=0` 保持零點單一 mass；正 scale 數值結果必須不變。
- Stage 7 `_build_scaled_total_pdf_added_noise()` 與 `calculate_der_mlsd()` 是 direct
  injectors。`fir_filter()` 固定 `mass_deposit`，不接收 ALG-004 selector。

## Exclusions

不修改 ALG-002、`_project_to_grid()`、FIR、ALG-003、PMF grid／retained mass、
config schema/default、reference profile、93A、MLSD equations、golden 或 tolerance。

## Validation

- Signed asymmetric PMF：`negative.x == positive.x`、
  `negative.pmf == positive.pmf[::-1]`。
- Positive、zero、method/projection isolation 與 Stage 7 MLSD consumer focused tests。
- Python 3.7 standalone export rebuild／validation。
- 固定 SiCoPR production golden 一次；沿用既有 MSE、COM_DFE、final COM 與
  intermediate digest acceptance，不修改 golden。

## Current evidence

- Project interpreter：`.venv/Scripts/python.exe`；NumPy 2.5.3、SciPy 1.18.1、pytest 9.1.1。
- Focused PMF／MLSD／profile tests：`49 passed, 2 subtests passed`。
- Python 3.7 standalone export validation：passed。
- Fixed SiCoPR golden：`1 passed`；既有 MSE、COM_DFE、final COM tolerances 與
  三個 frozen intermediate digests 全數通過，未修改 golden。
- Isolated integration：implementation／test／export／technical docs commit
  `114e7bf` 已推送至 `origin/main`。
