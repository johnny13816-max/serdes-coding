# C2M 802.3dj 4p13p0 150mm Case

This case uses the project-owned COM workbook format:

```text
config.xlsx
channels/
```

Source config reference:

```text
IEEE802_3dj_COM_Adhoc/config_templates/C2M/200G/config_com-4p13p0_802p3dj_d2p3_200G_C2M_TP0_TP2_Egress_26_01_27.xlsx
```

Channel set:

- `victim_thru.s4p`
- `next_1.s4p` ... `next_6.s4p`
- `fext_1.s4p` ... `fext_5.s4p`

Port order:

- IEEE/COM workbook `Port Order = [1 3 2 4]` in MATLAB 1-based indexing.
- Project workbook uses Python 0-based indexing: `0,2,1,3`.

Notes:

- One case folder must contain exactly the channel set used by that case.
- The same C2M config values are currently reused across the 50mm, 150mm, 250mm, and 500mm channel cases.

