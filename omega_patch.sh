#!/bin/bash

# Konfigurasi Path
WLAN_PATH="drivers/staging/qcacld-3.0"
HDD_MAIN="$WLAN_PATH/core/hdd/src/wlan_hdd_main.c"
HDD_TXRX="$WLAN_PATH/core/hdd/src/wlan_hdd_tx_rx.c"
HDD_MON="$WLAN_PATH/core/hdd/src/wlan_hdd_monitor.c"
HDD_CFG="$WLAN_PATH/core/hdd/src/wlan_hdd_cfg80211.c"
LIM_SME="$WLAN_PATH/core/mac/src/pe/lim/lim_process_sme_req_utils.c"
REG_FILE="$WLAN_PATH/core/hdd/src/wlan_hdd_regulatory.c"

echo "[*] Memulai Patching Skala Penuh untuk WCN3990 (SDM845)..."

# 1. Bypass Policy Engine (PE) - Mengatasi log "Target channel same"
if [ -f "$LIM_SME" ]; then
    echo "[+] Patching LIM Policy Engine (lim_process_sme_req_utils.c)..."
    # Menyisipkan bypass di awal fungsi agar tidak stuck di pengecekan channel
    sed -i '/lim_process_sme_channel_change_request/!b;n;a \    return eSIR_SUCCESS;' "$LIM_SME"
fi

# 2. Bypass TX Allowed Check - Membuka gerbang transmisi
if [ -f "$HDD_TXRX" ]; then
    echo "[+] Patching TX Gatekeeper (wlan_hdd_tx_rx.c)..."
    # Memaksa hdd_is_tx_allowed mengembalikan true untuk monitor mode
    sed -i '/if (adapter->device_mode == QDF_MONITOR_MODE)/!b;n;c\		return true;' "$HDD_TXRX"
fi

# 3. Registrasi Handler Injeksi Mentah (Raw TX)
if [ -f "$HDD_MAIN" ]; then
    echo "[+] Patching Driver Ops (wlan_hdd_main.c)..."
    # Menambahkan support monitor ke interface list
    sed -i '/BIT(NL80211_IFTYPE_P2P_DEVICE)/a \		BIT(NL80211_IFTYPE_MONITOR) |' "$HDD_MAIN"
    # Menghubungkan stack transmisi ke handler hardware
    sed -i '/static const struct net_device_ops wlan_mon_drv_ops = {/,/};/ s/};/	.ndo_start_xmit = hdd_hard_start_xmit,\n};/' "$HDD_MAIN"
fi

# 4. Aktifkan Mode Monitor di CFG80211
if [ -f "$HDD_CFG" ]; then
    echo "[+] Patching CFG80211 Gateway (wlan_hdd_cfg80211.c)..."
    sed -i '/case NL80211_IFTYPE_P2P_DEVICE:/i \	case NL80211_IFTYPE_MONITOR:' "$HDD_CFG"
fi

# 5. Unlocking 5GHz & DFS (Bypass Regulatory)
if [ -f "$REG_FILE" ]; then
    echo "[+] Patching Regulatory (wlan_hdd_regulatory.c)..."
    sed -i 's/IEEE80211_CHAN_NO_IR/0/g' "$REG_FILE"
fi

# 6. Force Flags di Kbuild
KBUILD="$WLAN_PATH/Kbuild"
if [ -f "$KBUILD" ]; then
    echo "[+] Injecting High-Level Flags ke Kbuild..."
    echo "ccflags-y += -DCONFIG_WLAN_MONITOR_MODE_ENABLE" >> "$KBUILD"
    echo "ccflags-y += -DCONFIG_WLAN_TX_MON_ENABLE" >> "$KBUILD"
    echo "ccflags-y += -DQCA_MONITOR_ADDR_BASED_FILTER" >> "$KBUILD"
    echo "ccflags-y += -DFEATURE_WLAN_MONITOR_MODE_MAX_LINE_RATE" >> "$KBUILD"
fi

echo "---"
echo "[OK] Patch berhasil diaplikasikan ke source."
echo "[!] JANGAN LUPA: Pastikan CONFIG_WLAN_TX_MON_ENABLE=y ada di defconfig lo!"
echo "[!] Jika kompilasi error di LIM_SME, periksa tipe data eSIR_SUCCESS di source lo."
