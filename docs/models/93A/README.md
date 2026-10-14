# IEEE 802.3 93A model documentation

The 93A configuration contract is documented in [config_tree.md](config_tree.md). Stage and call documentation will be added as their version-specific contracts are reviewed.

TX FFE 的 `num_pre` 是 tap 陣列中 main cursor 的位置；`tx_ffe_93A()` 依 Eq. 93A-21 使用 `n = idx - num_pre` 建立頻域相位，使 main-only tap 的 transfer function 為 1。此共用建構函式亦供 178A path 使用。
