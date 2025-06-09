#!/bin/bash

# Default: debug disabled
DEBUG=0

# Check for --debug flag
for arg in "$@"; do
    if [ "$arg" == "--debug" ]; then
        DEBUG=1
    fi
done

# Debug log function
log() {
    if [ "$DEBUG" -eq 1 ]; then
        echo -e "[DEBUG] $1"
    fi
}

# Target architectures
ARCHES=(arm64 arm)

log "Creating headers directory structure..."
mkdir -p headers/arch

log "Copying include/ directory..."
cp -r include headers/

log "Copying scripts/ directory..."
cp -r scripts headers/

log "Copying Makefile..."
cp Makefile headers/

log "Handling Module.symvers..."
if [ -e Module.symvers ]; then
    log "Found Module.symvers, copying..."
    cp Module.symvers headers/
else
    log "Module.symvers not found, creating empty one..."
    touch headers/Module.symvers
fi

log "Entering headers/ directory..."
cd headers || { echo "[ERROR] Failed to enter headers/"; exit 1; }

for arch in "${ARCHES[@]}"; do
    log "Copying arch/$arch..."
    cp -r ../arch/$arch arch/
done

log "Cleaning up .o and .c files..."
find . -type f -name "*.o" -print -delete
find . -type f -name "*.c" -print -delete

cd ..

if [ -d out ]; then
    log "Found out/ directory, copying additional include/ and scripts/..."
    cp -r out/include headers/
    cp -r out/scripts headers/

    for arch in "${ARCHES[@]}"; do
        log "Copying out/arch/$arch..."
        cp -r out/arch/$arch headers/arch/
    done
else
    log "No out/ directory found. Skipping."
fi

log "All done!"