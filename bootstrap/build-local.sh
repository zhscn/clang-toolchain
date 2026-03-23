#!/bin/bash
set -euo pipefail

LLVM_VERSION="${LLVM_VERSION:-21.1.8}"
LLVM_MAJOR="${LLVM_MAJOR:-21}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ARCH="$(uname -m)"

case "$ARCH" in
  x86_64)  DOCKERFILE="rocky8-x86_64.Dockerfile"; LLVM_TARGET="X86" ;;
  aarch64|arm64) DOCKERFILE="rocky8-aarch64.Dockerfile"; LLVM_TARGET="AArch64" ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

echo "==> Building for $ARCH (LLVM $LLVM_VERSION)"

# Download LLVM source if not present
if [[ ! -f "$ROOT_DIR/llvm-project.tar.xz" ]]; then
  echo "==> Downloading LLVM source..."
  curl -fsSL -o "$ROOT_DIR/llvm-project.tar.xz" \
    "https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VERSION}/llvm-project-${LLVM_VERSION}.src.tar.xz"
fi

echo "==> Building Docker image..."
docker build -t clang-bootstrap -f "$SCRIPT_DIR/$DOCKERFILE" "$ROOT_DIR"

VOLUME="clang-bootstrap-stage0"

echo "==> Building stage0 (GCC bootstrap)..."
docker volume create "$VOLUME" >/dev/null
docker run --network host --rm \
  -v "$ROOT_DIR:/work" \
  -v "$VOLUME:/opt/clang-stage0" \
  -e LLVM_VERSION="$LLVM_VERSION" \
  -e LLVM_MAJOR="$LLVM_MAJOR" \
  -e LLVM_TARGET="$LLVM_TARGET" \
  clang-bootstrap bash -lc '
    set -euo pipefail
    INSTALL_PREFIX=/opt/clang-stage0

    # Skip if stage0 already built
    if [[ -x ${INSTALL_PREFIX}/bin/clang ]]; then
      echo "stage0 already present, skipping"
      exit 0
    fi

    tar -xf /work/llvm-project.tar.xz -C /tmp
    cd /tmp/llvm-project-${LLVM_VERSION}.src

    mkdir -p build-stage0 && cd build-stage0
    cmake -G Ninja ../llvm \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX} \
      -DLLVM_ENABLE_PROJECTS="clang;lld" \
      -DLLVM_TARGETS_TO_BUILD="${LLVM_TARGET}" \
      -DLLVM_ENABLE_ZLIB=ON \
      -DLLVM_ENABLE_ASSERTIONS=OFF \
      -DLLVM_INCLUDE_TESTS=OFF \
      -DLLVM_INCLUDE_EXAMPLES=OFF \
      -DLLVM_INCLUDE_BENCHMARKS=OFF

    ninja
    ninja install
  '

echo "==> Building RPM (stage1)..."
docker run --network host --rm \
  -v "$ROOT_DIR:/work" \
  -v "$VOLUME:/opt/clang-stage0" \
  -e LLVM_VERSION="$LLVM_VERSION" \
  -e LLVM_MAJOR="$LLVM_MAJOR" \
  clang-bootstrap bash -lc '
    set -euo pipefail
    mkdir -p /work/out

    rpmdev-setuptree
    cp /work/llvm-project.tar.xz ~/rpmbuild/SOURCES/llvm-project-${LLVM_VERSION}.src.tar.xz
    cp /work/bootstrap/clang-toolchain.spec ~/rpmbuild/SPECS/

    rpmbuild -bb ~/rpmbuild/SPECS/clang-toolchain.spec \
      --define "llvm_major ${LLVM_MAJOR}" \
      --define "llvm_version ${LLVM_VERSION}"

    cp ~/rpmbuild/RPMS/*/*.rpm /work/out/
  '

echo "==> Done. RPMs in out/"
echo "    (stage0 cached in Docker volume '$VOLUME' — run 'docker volume rm $VOLUME' to clean up)"
ls -lh "$ROOT_DIR/out/"*.rpm
