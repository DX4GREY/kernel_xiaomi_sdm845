#!/bin/bash

# Default: debug disabled
DEBUG=0
HLOC=linux-headers

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

log "Creating $HLOC directory structure..."
mkdir -p $HLOC/arch

log "Copying include/ directory..."
cp -r include $HLOC/

log "Copying scripts/ directory..."
cp -r scripts $HLOC/

log "Copying Makefile..."
cp Makefile $HLOC/

log "Handling Module.symvers..."
if [ -e Module.symvers ]; then
    log "Found Module.symvers, copying..."
    cp Module.symvers $HLOC/
else
    log "Module.symvers not found, creating empty one..."
    touch $HLOC/Module.symvers
fi

log "Entering $HLOC/ directory..."
cd $HLOC || { echo "[ERROR] Failed to enter $HLOC/"; exit 1; }

for arch in "${ARCHES[@]}"; do
    log "Copying arch/$arch..."
    cp -r ../arch/$arch arch/
done

log "Cleaning up files..."
find . -type f -name "*.c" -delete

cd ..

if [ -d out ]; then
    log "Found out/ directory, copying additional include/ and scripts/..."
    cp -r out/include $HLOC/
    cp -r out/scripts $HLOC/

    for arch in "${ARCHES[@]}"; do
        log "Copying out/arch/$arch..."
        cp -r out/arch/$arch $HLOC/arch/
    done
else
    log "No out/ directory found. Skipping."
fi

log "All done!"