#!/usr/bin/env python3

import os
import shutil
import argparse
from pathlib import Path

patterns = ["*.c", "*.o", "*.cmd", "*.d", ".*.cmd"]

def log(msg, debug):
	if debug:
		print(f"[DEBUG] {msg}")

def clean_headers(path, patterns, debug):
	for pattern in patterns:
		for file in path.rglob(pattern):
			try:
				file.unlink()
			except Exception as e:
				log(f"Error delete {file}: {e}", debug)

def is_kernel_prepared(outputd=""):
	must_exist = [
		f"./{outputd}/include/generated/autoconf.h",
		f"./{outputd}/include/config",
		f"./{outputd}/scripts",
	]
	for item in must_exist:
		if not Path(item).exists():
			return False
	return True
	
def safe_copy(src, dst, debug):
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
		
def setup_headers(debug, outk):
	if not is_kernel_prepared(outk):
		print("[ERROR] Kernel source is not prepared. Run 'make modules_prepare' first.")
		return
		
	HLOC = Path("linux-headers")
	ARCHES = ["arm64", "arm"]

	log(f"Creating {HLOC} directory structure...", debug)
	(HLOC / "arch").mkdir(parents=True, exist_ok=True)

	# Copy essential files
	log("Copying include...", debug)
	safe_copy("include", HLOC / "include", debug)
	log("Copying scripts...", debug)
	safe_copy("scripts", HLOC / "scripts", debug)
	log("Copying Makefile...", debug)
	safe_copy("Makefile", HLOC / "Makefile", debug)

	# Handle Module.symvers
	mod_sym = Path("Module.symvers")
	target_sym = HLOC / "Module.symvers"
	if mod_sym.exists():
		log("Found Module.symvers, copying...", debug)
		shutil.copy2(mod_sym, target_sym)
	else:
		log("Module.symvers not found, creating empty one...", debug)
		target_sym.touch()

	# Copy arch
	for arch in ARCHES:
		src_arch = Path("arch") / arch
		dst_arch = HLOC / "arch" / arch
		safe_copy(src_arch, dst_arch, debug)
		if arch == "arm64":
			log(f"Creating symlink aarch64 -> {arch}", debug)
			try:
				os.symlink(arch, HLOC / "arch" / "aarch64")
			except FileExistsError:
				pass

	# Handle out directory
	out_dir = Path("out")
	if out_dir.exists():
		log("Found out/ directory, copying additional includes and scripts...", debug)
		log("Copying out include...", debug)
		safe_copy(out_dir / "include", HLOC / "include", debug)
		log("Copying out scripts...", debug)
		safe_copy(out_dir / "scripts", HLOC / "scripts", debug)
		for arch in ARCHES:
			log(f"Copying out {arch}...", debug)
			safe_copy(out_dir / "arch" / arch, HLOC / "arch" / arch, debug)
	else:
		log("No out/ directory found. Skipping.", debug)
	
	# Delete all .c files
	log("Cleaning up junk files...", debug)
	clean_headers(HLOC.resolve(), patterns, debug)
	
	log("All done!", debug)

def main():
	parser = argparse.ArgumentParser(description="Prepare minimal kernel headers for external module building.")
	parser.add_argument("--debug", action="store_true", help="Enable debug logging")
	parser.add_argument("--outk", type=Path, default="out", help="Kernel out directory (default: out)")
	args = parser.parse_args()
	setup_headers(args.debug, args.outk)

if __name__ == "__main__":
	main()