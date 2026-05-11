#!/usr/bin/env python3

import os
import shutil
import argparse
import subprocess
from pathlib import Path
import sys

# Pola file yang tidak diperlukan (akan dihapus)
patterns = [
    "*.c", "*.o", "*.cmd", "*.d", ".*.cmd",
    "*.S", "*.s", "*.lds", "*.a", "*.ko", "*.mod", "*.mod.c",
    "*.lst", ".*.o.cmd", ".*.mod.cmd", "*.o.d", "*.orig", "*.rej",
    "*.tab.c", "*.lex.c", "*.output", "*.symtypes", "*.order"
]

def log(msg, debug):
    if debug:
        print(f"[DEBUG] {msg}")

def prune_all(root, debug):
    """Hapus semua file yang tidak diperlukan untuk build modul"""
    for pattern in patterns:
        for file in root.rglob(pattern):
            if file.is_file():
                try:
                    file.unlink()
                    log(f"Deleted {file}", debug)
                except Exception as e:
                    log(f"Error deleting {file}: {e}", debug)
    # Hapus direktori kosong (dari bawah ke atas)
    for d in sorted(root.rglob("*"), key=lambda p: str(p), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            try:
                d.rmdir()
                log(f"Removed empty directory {d}", debug)
            except Exception as e:
                log(f"Error removing {d}: {e}", debug)

def safe_copy(src, dst, debug):
    """Salin file atau direktori dengan aman"""
    src_path = Path(src)
    dst_path = Path(dst)
    if not src_path.exists():
        log(f"Source {src} does not exist, skipping...", debug)
        return
    if src_path.is_dir():
        dst_path.mkdir(parents=True, exist_ok=True)
        for item in src_path.iterdir():
            target = dst_path / item.name
            if item.is_dir():
                safe_copy(item, target, debug)
            else:
                shutil.copy2(item, target)
    else:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)

def is_kernel_prepared(outputd=""):
    """Cek apakah kernel sudah dipersiapkan (make modules_prepare)"""
    must_exist = [
        f"./{outputd}/include/generated/autoconf.h",
        f"./{outputd}/include/config",
        f"./{outputd}/scripts",  # out/scripts mungkin ada, tapi kita tidak akan gunakan
    ]
    for item in must_exist:
        if not Path(item).exists():
            print(f"[ERROR] Missing required file: {item}")
            return False
    return True

def copy_arch_selective(arch, src_root, out_root, dst_root, debug):
    """
    Salin hanya bagian minimal dari arsitektur:
    - include/ (wajib)
    - Makefile, Kconfig, Kbuild
    - kernel/module.lds (jika ada)
    - out/arch/... (hasil generate seperti asm-offsets.h)
    """
    src_arch = src_root / "arch" / arch
    dst_arch = dst_root / "arch" / arch
    if not src_arch.exists():
        log(f"Arch {arch} not found in source, skipping", debug)
        return

    dst_arch.mkdir(parents=True, exist_ok=True)

    # File penting di root arch
    for file in ["Makefile", "Kconfig", "Kbuild"]:
        src_file = src_arch / file
        if src_file.exists():
            safe_copy(src_file, dst_arch / file, debug)

    # Salin include/ dari arch (header spesifik arsitektur)
    src_inc = src_arch / "include"
    if src_inc.exists():
        safe_copy(src_inc, dst_arch / "include", debug)

    # Salin module.lds jika ada (biasanya di arch/*/kernel/)
    lds = src_arch / "kernel" / "module.lds"
    if lds.exists():
        safe_copy(lds, dst_arch / "kernel" / "module.lds", debug)

    # Salin hasil generate dari out/arch (misal asm-offsets.h)
    out_arch = out_root / "arch" / arch
    if out_arch.exists():
        out_inc = out_arch / "include"
        if out_inc.exists():
            safe_copy(out_inc, dst_arch / "include", debug)
        out_make = out_arch / "Makefile"
        if out_make.exists():
            safe_copy(out_make, dst_arch / "Makefile", debug)

def build_scripts_basic_for_arch(arch, src_root, out_dir, debug):
    """Bangun scripts_basic untuk arsitektur tertentu."""
    log(f"Building scripts_basic for architecture: {arch}...", debug)
    try:
        subprocess.run(["make", f"ARCH={arch}", f"O={out_dir}", "scripts_basic"], check=True, cwd=src_root)
        log(f"Successfully built scripts_basic for {arch}", debug)
    except subprocess.CalledProcessError as e:
        log(f"Failed to build scripts_basic for {arch}: {e}", debug)
        return False
    return True

def setup_headers(debug, outk, arches):
    """Mempersiapkan direktori linux-headers minimal untuk build modul eksternal"""
    if not is_kernel_prepared(outk):
        print("[ERROR] Kernel source is not prepared. Run 'make modules_prepare' first.")
        return False

    HLOC = Path("linux-headers")
    out_dir = Path(outk)  # Use the --outk argument for output directory
    src_root = Path(".")  # current directory sebagai source root

    log(f"Creating {HLOC} directory structure...", debug)
    HLOC.mkdir(exist_ok=True)

    # 1. Salin file penting di level atas
    top_files = ["Makefile", "Kconfig", "Kbuild", "Module.symvers"]
    for fname in top_files:
        src = src_root / fname
        dst = HLOC / fname
        if src.exists():
            safe_copy(src, dst, debug)
        elif fname == "Module.symvers":
            # cari di out/ jika ada
            out_sym = out_dir / "Module.symvers"
            if out_sym.exists():
                safe_copy(out_sym, dst, debug)
            else:
                dst.touch()
                log("Created empty Module.symvers", debug)

    # 2. Salin scripts dari source, PASTIKAN binary untuk HOST (bukan target)
    # Jalankan 'make scripts_basic' untuk setiap arsitektur yang dipilih
    scripts_src = src_root / "scripts"
    for arch in arches:
        if not build_scripts_basic_for_arch(arch, src_root, out_dir, debug):
            print(f"[WARNING] Skipping further steps for architecture: {arch}")
            continue

    fixdep_path = Path(out_dir) / "scripts" / "basic" / "fixdep"
    if not fixdep_path.exists():
        log("fixdep not found after building scripts_basic. Exiting...", debug)
        sys.exit(1)

    # Salin seluruh scripts (termasuk basic/fixdep yang sudah host)
    safe_copy(scripts_src, HLOC / "scripts", debug)

    # 3. Salin include: prioritas dari out (generated headers)
    if (out_dir / "include").exists():
        safe_copy(out_dir / "include", HLOC / "include", debug)
    else:
        safe_copy(src_root / "include", HLOC / "include", debug)

    # 4. Salin arch secara selektif
    (HLOC / "arch").mkdir(exist_ok=True)
    for arch in arches:
        copy_arch_selective(arch, src_root, out_dir, HLOC, debug)
        if arch == "arm64":
            # Buat symlink aarch64 -> arm64 untuk kompatibilitas
            link = HLOC / "arch" / "aarch64"
            if not link.exists():
                try:
                    link.symlink_to("arm64")
                    log("Created symlink aarch64 -> arm64", debug)
                except Exception as e:
                    log(f"Failed to create symlink: {e}", debug)

    # 5. Bersihkan file yang tidak diperlukan
    log("Pruning unnecessary files...", debug)
    prune_all(HLOC, debug)

    # Validasi akhir
    if not validate_headers(HLOC, debug):
        print("[ERROR] Validation failed. linux-headers is incomplete.")
        return False

    log("Headers preparation completed.", debug)
    return True

def validate_headers(HLOC, debug):
    """Validasi bahwa semua file penting ada di linux-headers."""
    required_files = [
        HLOC / "Makefile",
        HLOC / "Kconfig",
        HLOC / "Kbuild",
        HLOC / "Module.symvers",
        HLOC / "include",
        HLOC / "arch",
    ]
    missing_files = [str(f) for f in required_files if not f.exists()]
    if missing_files:
        log(f"[ERROR] Missing required files: {', '.join(missing_files)}", debug)
        return False
    log("[INFO] All required files are present in linux-headers.", debug)
    return True

def get_kernel_version(outk, debug):
    """Mendapatkan versi kernel dari Makefile dan .config"""
    makefile = Path("Makefile")
    config = Path(outk) / ".config"

    version = patchlevel = sublevel = extraversion = localversion = ""
    if makefile.exists():
        for line in makefile.read_text().splitlines():
            if line.startswith("VERSION ="):
                version = line.split("=")[1].strip()
            elif line.startswith("PATCHLEVEL ="):
                patchlevel = line.split("=")[1].strip()
            elif line.startswith("SUBLEVEL ="):
                sublevel = line.split("=")[1].strip()
            elif line.startswith("EXTRAVERSION ="):
                extraversion = line.split("=")[1].strip()
    if config.exists():
        for line in config.read_text().splitlines():
            if line.startswith("CONFIG_LOCALVERSION="):
                localversion = line.split("=")[1].strip().strip('"')
    full_version = f"{version}.{patchlevel}.{sublevel}{extraversion}{localversion}"
    log(f"Detected kernel version: {full_version}", debug)
    return full_version

def build_deb(debug, outk, arch="arm64"):
    """Bangun paket DEB dari headers yang sudah disiapkan"""
    version = get_kernel_version(outk, debug)
    if shutil.which("dpkg-deb") is None:
        print("[ERROR] dpkg-deb is not available. Please install it to build the DEB package.")
        return

    HLOC = Path("linux-headers")
    DEB_ROOT = Path("deb_pkg")
    DEBIAN = DEB_ROOT / "DEBIAN"
    INSTALL_PATH = DEB_ROOT / f"usr/src/linux-headers-{version}"

    log("Setting up DEB structure...", debug)
    if DEB_ROOT.exists():
        shutil.rmtree(DEB_ROOT)

    DEBIAN.mkdir(parents=True, exist_ok=True)
    INSTALL_PATH.parent.mkdir(parents=True, exist_ok=True)

    log("Copying headers into package...", debug)
    shutil.copytree(HLOC, INSTALL_PATH, symlinks=True)

    # File control
    control_content = f"""Package: linux-headers-{version}
Version: {version}
Section: kernel
Priority: optional
Architecture: {arch}
Maintainer: DX4GREY <dxablack@gmail.com>
Description: Minimal Linux kernel headers for external module building
 This package provides a minimal set of kernel headers optimized for size,
 containing only files necessary to build external kernel modules.
"""
    (DEBIAN / "control").write_text(control_content)

    # postinst script untuk membuat symlink /lib/modules
    postinst_content = f"""#!/bin/sh
set -e
mkdir -p /lib/modules/{version}
ln -sf /usr/src/linux-headers-{version} /lib/modules/{version}/build
"""
    postinst_path = DEBIAN / "postinst"
    postinst_path.write_text(postinst_content)
    postinst_path.chmod(0o755)

    # Bangun .deb
    deb_name = f"linux-headers-{version}_{arch}.deb"
    log(f"Building {deb_name}...", debug)
    os.system(f"dpkg-deb --build {DEB_ROOT} {deb_name}")

    print(f"[INFO] DEB package created: {deb_name}")

def get_available_architectures(src_root):
    """Dapatkan daftar arsitektur yang tersedia dari direktori arch."""
    arch_dir = src_root / "arch"
    if not arch_dir.exists():
        print("[ERROR] Directory 'arch/' not found.")
        sys.exit(1)
    return [d.name for d in arch_dir.iterdir() if d.is_dir()]

def main():
    parser = argparse.ArgumentParser(description="Prepare minimal kernel headers for external module building.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--outk", type=Path, default="out", help="Kernel out directory (default: out)")
    parser.add_argument("--build-deb", action="store_true", help="Build a DEB package after preparing headers")
    parser.add_argument("--arch", type=str, help="Target architecture for DEB package")
    args = parser.parse_args()

    src_root = Path(".")
    available_arches = get_available_architectures(src_root)

    if args.arch:
        if args.arch not in available_arches:
            print(f"[ERROR] Invalid architecture '{args.arch}'. Available options: {', '.join(available_arches)}")
            sys.exit(1)
        arches = [args.arch]
    else:
        print("[INFO] No architecture specified. Defaulting to all available architectures.")
        arches = available_arches

    log(f"Processing architectures: {', '.join(arches)}", args.debug)

    if setup_headers(args.debug, args.outk, arches):
        if args.build_deb:
            build_deb(args.debug, args.outk, args.arch or "arm64")
        log("All done!", args.debug)
    else:
        print("[ERROR] Header preparation failed. Exiting.")
        exit(1)

if __name__ == "__main__":
    main()