# COM Case Input Contract

## 目錄責任

- `templates/`：只放空白或半空白的 Excel template，不作為正式 run input。
- `cases/<case_id>/config.xlsx`：該 case 的固定參數、search 參數、channel 路徑。
- `cases/<case_id>/channels/`：該 case 對應的一組 victim/NEXT/FEXT S4P files。

## Case Contract

一個 case folder 對應一組完整 channel set：

```text
cases/<case_id>/
  config.xlsx
  channels/
    victim_thru.s4p
    next_1.s4p
    ...
    fext_1.s4p
    ...
```

`config.xlsx` 的 `channels` sheet 使用相對於該 workbook 的路徑，例如：

```text
channels/victim_thru.s4p
channels/next_1.s4p
channels/fext_1.s4p
```

## Current C2M Cases

目前已建立四組 802.3dj C2M debug/reference cases：

```text
cases/c2m_8023dj_4p13p0_50mm/config.xlsx
cases/c2m_8023dj_4p13p0_150mm/config.xlsx
cases/c2m_8023dj_4p13p0_250mm/config.xlsx
cases/c2m_8023dj_4p13p0_500mm/config.xlsx
```

每組 case 目前連結：

- 1 條 victim THRU
- 6 條 NEXT
- 5 條 FEXT

## Source

Config 參考：

```text
IEEE802_3dj_COM_Adhoc/config_templates/C2M/200G/config_com-4p13p0_802p3dj_d2p3_200G_C2M_TP0_TP2_Egress_26_01_27.xlsx
```

Channel raw data 來源：

```text
serdes-coding/reference_data/COM_channel_data/C2M/mellitz_3dj_02_2409
```

注意：C2M workbook 的 `Port Order = [1 3 2 4]` 是 MATLAB 1-based 表示法；本專案 config 使用 Python 0-based，因此寫成 `0,2,1,3`。
