# Reference Cases

## debug_case_93a_style

位置：
- `templates/com_v1_params_template.xlsx`

用途：
- 用來快速跑通目前 93A-style COM pipeline。
- 用來 debug path build、DFE、impairment、PMF、plot/export flow。

不可用途：
- 不可視為正式 IEEE 93A validation case。
- 不可用來宣稱與 IEEE COM、MATLAB COM、或量測結果 correlation。

來源與目前設定：
- Channel / legacy config family 來自 PyChOpMarg IEEE 802.3dj example2。
- 原始 reference family 是 802.3dj/178A-style context，不是正式 93A validation baseline。
- 目前 template 將 `fb` 固定成 `53.125e9 Hz`，讓它比較接近 93A-style debug condition。
- 目前 template 同步使用 `per_ui=64`、`N_b=12`、`fr=0.58*fb`、`f_LF=0.0125*fb`。

已知限制：
- Channel S4P 量測頻寬、package/filter/noise/jitter/search 設定尚未逐項對照正式 93A reference table。
- 這個 case 的主要價值是軟體流程 sanity check，不是規格數值驗證。

