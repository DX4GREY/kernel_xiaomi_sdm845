#!/bin/bash
# Auto-generated setup.sh by builder.sh --setup
# Usage: source setup.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo -e "${RED}Error: Script ini harus di-source, bukan dijalankan langsung.${NC}"
    echo -e "Gunakan: ${YELLOW}source ${BASH_SOURCE[0]}${NC}"
    exit 1
fi

TOOLCHAIN_DIR="/home/dx4white/kernel/toolchains/cosmic-clang"
CLANG_PATH="$TOOLCHAIN_DIR/bin"

if [ ! -d "$TOOLCHAIN_DIR" ]; then
    echo -e "${RED}Error: Toolchain tidak ditemukan di $TOOLCHAIN_DIR${NC}"
    return 1
fi

if [ ! -f "$CLANG_PATH/clang" ]; then
    echo -e "${RED}Error: Clang tidak ditemukan di $CLANG_PATH${NC}"
    return 1
fi

if [[ ":$PATH:" != *":$CLANG_PATH:"* ]]; then
    export PATH="$CLANG_PATH:$PATH"
    echo -e "${GREEN}✓ PATH updated (added $CLANG_PATH)${NC}"
fi

export KBUILD_BUILD_USER="${KBUILD_BUILD_USER:-builder}"
export KBUILD_BUILD_HOST="${KBUILD_BUILD_HOST:-dlovely-faz}"
echo -e "${GREEN}✓ Build user/host set to ${KBUILD_BUILD_USER}@${KBUILD_BUILD_HOST}${NC}"

export CROSS_COMPILE="aarch64-linux-gnu-"
echo -e "${GREEN}✓ CROSS_COMPILE set to aarch64-linux-gnu-${NC}"

export CROSS_COMPILE_COMPAT="arm-linux-gnueabi-"
export CROSS_COMPILE_ARM32="arm-linux-gnueabi-"
export CLANG_TRIPLE="aarch64-linux-gnu-"

export CC="clang"
export HOSTCC="clang"
echo -e "${GREEN}✓ CC set to clang, HOSTCC set to clang${NC}"

export ARCH=arm64
echo -e "${GREEN}✓ ARCH set to arm64${NC}"

echo -e "${GREEN}=== Cosmic Clang Toolchain Loaded ===${NC}"
echo -e "Toolchain path: ${YELLOW}$TOOLCHAIN_DIR${NC}"
echo -e "Clang version: ${YELLOW}$($CLANG_PATH/clang --version | head -n1)${NC}"
if command -v aarch64-linux-gnu-ld &>/dev/null; then
    echo -e "Binutils version: ${YELLOW}$(aarch64-linux-gnu-ld --version | head -n1)${NC}"
else
    echo -e "${YELLOW}Warning: aarch64-linux-gnu-ld tidak ditemukan di PATH${NC}"
fi
echo -e "${GREEN}======================================${NC}"
