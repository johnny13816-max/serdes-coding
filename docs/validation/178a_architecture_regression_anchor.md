# 178A architecture regression anchor

本基準保護 `sicopr_akinwale_vendorx_22db` 的 178A production path，供架構搬移使用。
它不是新的 reference calibration，也不授權修改模型公式。

## Execution boundary

- case: `cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx`
- profile: `sicopr_reference_v1`
- target: `full`
- production entry: `COM(cfg)._run_once(run_cfg=..., progress=False)`
- source revision: `5d1380b`

## Locked results

| Quantity | Expected |
|---|---:|
| phase `pos` | 5 |
| cursor `ts` | 38149 |
| MSE | 0.0061912610245255335 |
| RX FFE length | 87 |
| first DFE tap | 0.8420106292760028 |
| `h_dsamp` length | 10626 |
| `R_n` length | 4096 |
| `A_s` | 0.31666666666666665 V |
| `A_ni` | 0.2656833333333335 V |
| COM_DFE | 1.5247607834259893 dB |
| delta_COM | 1.3711379014472564 dB |
| COM_MLSD | 2.895898684873246 dB |

`tests/test_com_model_178A_golden.py` additionally locks quantized stage-vector
digests for RX FFE, `h_dsamp`, and `R_n`. Pure architecture relocation must
preserve these values. A deliberate numerical change requires its own approved
Core Model Change Contract and updated acceptance evidence.

## Dependency ratchet

`tests/test_com_model_178A_dependency_ratchet.py` records the temporary direct
178A-to-93A dependency surface. New cross-version dependencies are forbidden.
Each ownership-migration batch must reduce this allowlist until it becomes empty.
