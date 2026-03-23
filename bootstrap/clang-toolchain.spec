%{!?llvm_major: %define llvm_major 21}
%{!?llvm_version: %define llvm_version 21.1.8}
%{!?release: %define release 1%{?dist}}
%{!?install_prefix: %define install_prefix /opt/clang%{llvm_major}}
%{!?bootstrap_prefix: %define bootstrap_prefix /opt/clang-stage0}

# alternatives priority: major version * 100 (e.g. 2100 for clang 21)
%define alternatives_priority %(echo $(( %{llvm_major} * 100 )))

%ifarch x86_64
%define llvm_target X86
%define target_triple x86_64-unknown-linux-gnu
%endif
%ifarch aarch64
%define llvm_target AArch64
%define target_triple aarch64-unknown-linux-gnu
%endif

%define _lto_cflags %{nil}
%global debug_package %{nil}
%global _find_debuginfo_dwz_opts %{nil}
%global __python %{_bindir}/python3


Name:           clang-toolchain-%{llvm_major}
Version:        %{llvm_version}
Release:        %{release}
Summary:        Self-hosted LLVM/Clang %{llvm_major} toolchain
License:        Apache-2.0 WITH LLVM-exception
URL:            https://llvm.org/
Source0:        llvm-project-%{version}.src.tar.xz
ExclusiveArch:  x86_64 aarch64

BuildRequires:  zlib-devel
BuildRequires:  python3

Requires:       glibc
Requires:       libgcc
Requires:       zlib
Requires(post): alternatives
Requires(postun): alternatives

%description
Self-hosted Clang toolchain installed under %{install_prefix}.
The final compiler defaults to libc++, compiler-rt, lld, and libgcc unwinding.
libc++ and libc++abi are shipped as static libraries.

%prep
%setup -q -n llvm-project-%{version}.src

%build
export PATH=%{bootstrap_prefix}/bin:$PATH
export CC=%{bootstrap_prefix}/bin/clang
export CXX=%{bootstrap_prefix}/bin/clang++
export AR=%{bootstrap_prefix}/bin/llvm-ar
export NM=%{bootstrap_prefix}/bin/llvm-nm
export RANLIB=%{bootstrap_prefix}/bin/llvm-ranlib
export LDFLAGS="-Wl,--build-id"

# First pass: LLVM/Clang/LLD plus the libc++ family and the compiler-rt bits
# needed for default rtlib support. Sanitizers are built afterwards so that the
# just-built libc++ is already available.
mkdir -p build && cd build
cmake -G Ninja ../llvm \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=%{install_prefix} \
  -DLLVM_ENABLE_PROJECTS="clang;lld" \
  -DLLVM_ENABLE_RUNTIMES="compiler-rt;libcxx;libcxxabi" \
  -DLLVM_TARGETS_TO_BUILD="%{llvm_target}" \
  -DLLVM_ENABLE_LIBXML2=OFF \
  -DLLVM_ENABLE_ZLIB=ON \
  -DLLVM_ENABLE_ASSERTIONS=OFF \
  -DLLVM_INCLUDE_TESTS=OFF \
  -DLLVM_INCLUDE_EXAMPLES=OFF \
  -DLLVM_INCLUDE_BENCHMARKS=OFF \
  -DLLVM_ENABLE_LLD=ON \
  -DLLVM_STATIC_LINK_CXX_STDLIB=ON \
  -DCLANG_DEFAULT_CXX_STDLIB=libc++ \
  -DCLANG_DEFAULT_RTLIB=compiler-rt \
  -DCLANG_DEFAULT_UNWINDLIB=libgcc \
  -DCLANG_DEFAULT_LINKER=lld \
  -DCOMPILER_RT_BUILD_CRT=ON \
  -DCOMPILER_RT_BUILD_SANITIZERS=OFF \
  -DLIBCXX_ENABLE_SHARED=OFF \
  -DLIBCXX_ENABLE_STATIC=ON \
  -DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON \
  -DLIBCXXABI_ENABLE_SHARED=OFF \
  -DLIBCXXABI_ENABLE_STATIC=ON \
  -DLIBCXXABI_USE_LLVM_UNWINDER=OFF

ninja

# Second pass: standalone compiler-rt sanitizers using the just-built clang
cd ..
mkdir -p build-rt && cd build-rt
cmake -G Ninja ../compiler-rt \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=%{install_prefix} \
  -DCMAKE_C_COMPILER=%{_builddir}/llvm-project-%{version}.src/build/bin/clang \
  -DCMAKE_CXX_COMPILER=%{_builddir}/llvm-project-%{version}.src/build/bin/clang++ \
  -DCMAKE_C_COMPILER_TARGET=%{target_triple} \
  -DCMAKE_CXX_COMPILER_TARGET=%{target_triple} \
  -DCOMPILER_RT_BUILD_BUILTINS=OFF \
  -DCOMPILER_RT_BUILD_CRT=OFF \
  -DCOMPILER_RT_BUILD_SANITIZERS=ON \
  -DCOMPILER_RT_INCLUDE_TESTS=OFF \
  -DLLVM_CONFIG_PATH=%{_builddir}/llvm-project-%{version}.src/build/bin/llvm-config

ninja

%install
cd build
DESTDIR=%{buildroot} ninja install
cd ../build-rt
DESTDIR=%{buildroot} ninja install
cd %{_builddir}/llvm-project-%{version}.src

# Strip debug info from installed binaries and libraries before packaging.
find %{buildroot}%{install_prefix} -type f -executable -exec sh -c '
  for f in "$@"; do
    "%{_builddir}/llvm-project-%{version}.src/build/bin/llvm-strip" --strip-debug "$f" 2>/dev/null || true
  done
' _ {} +
find %{buildroot}%{install_prefix} -type f \
  \( -name "*.a" -o -name "*.o" -o -name "*.so" -o -name "*.so.*" \) \
  -exec sh -c '
    for f in "$@"; do
      "%{_builddir}/llvm-project-%{version}.src/build/bin/llvm-strip" --strip-debug "$f" 2>/dev/null || true
    done
  ' _ {} +

# Make __config_site available on the default include path so that libc++
# headers work without the multiarch-qualified directory.
ln -s %{install_prefix}/include/%{target_triple}/c++/v1/__config_site \
      %{buildroot}%{install_prefix}/include/c++/v1/__config_site

find %{buildroot}%{install_prefix} -type f -executable -exec \
  sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +
find %{buildroot}%{install_prefix} -type f -name '*.py' -exec \
  sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +

mkdir -p %{buildroot}%{install_prefix}/toolchains
cat > %{buildroot}%{install_prefix}/toolchains/clang.cmake <<'EOF'
set(CLANG_PREFIX "%{install_prefix}" CACHE PATH "")
set(CMAKE_C_COMPILER   "${CLANG_PREFIX}/bin/clang" CACHE FILEPATH "")
set(CMAKE_CXX_COMPILER "${CLANG_PREFIX}/bin/clang++" CACHE FILEPATH "")
set(CMAKE_AR           "${CLANG_PREFIX}/bin/llvm-ar" CACHE FILEPATH "")
set(CMAKE_NM           "${CLANG_PREFIX}/bin/llvm-nm" CACHE FILEPATH "")
set(CMAKE_RANLIB       "${CLANG_PREFIX}/bin/llvm-ranlib" CACHE FILEPATH "")
set(CMAKE_PREFIX_PATH  "${CLANG_PREFIX}" CACHE PATH "")
EOF

cat > %{buildroot}%{install_prefix}/enable <<'EOF'
export PATH=%{install_prefix}/bin${PATH:+:$PATH}
export CC=%{install_prefix}/bin/clang
export CXX=%{install_prefix}/bin/clang++
EOF
chmod 0755 %{buildroot}%{install_prefix}/enable

mkdir -p %{buildroot}%{install_prefix}/share/doc/%{name}
cat > %{buildroot}%{install_prefix}/share/doc/%{name}/README.md <<'EOF'
# %{name}

Installed under: %{install_prefix}
LLVM version: %{version}

Defaults:
- C++ standard library: libc++
- Runtime library: compiler-rt
- Unwind library: libgcc
- Linker: lld

Quick start:
    source %{install_prefix}/enable
    clang++ -std=c++20 hello.cpp -o hello

CMake:
    cmake -S . -B build \
      -DCMAKE_TOOLCHAIN_FILE=%{install_prefix}/toolchains/clang.cmake
EOF

%post
alternatives --install %{_bindir}/clang clang %{install_prefix}/bin/clang %{alternatives_priority} \
  --slave %{_bindir}/clang++ clang++ %{install_prefix}/bin/clang++ \
  --slave %{_bindir}/clang-cpp clang-cpp %{install_prefix}/bin/clang-cpp \
  --slave %{_bindir}/clang-cl clang-cl %{install_prefix}/bin/clang-cl \
  --slave %{_bindir}/lld lld %{install_prefix}/bin/lld \
  --slave %{_bindir}/ld.lld ld.lld %{install_prefix}/bin/ld.lld \
  --slave %{_bindir}/llvm-ar llvm-ar %{install_prefix}/bin/llvm-ar \
  --slave %{_bindir}/llvm-nm llvm-nm %{install_prefix}/bin/llvm-nm \
  --slave %{_bindir}/llvm-ranlib llvm-ranlib %{install_prefix}/bin/llvm-ranlib \
  --slave %{_bindir}/llvm-objcopy llvm-objcopy %{install_prefix}/bin/llvm-objcopy \
  --slave %{_bindir}/llvm-objdump llvm-objdump %{install_prefix}/bin/llvm-objdump \
  --slave %{_bindir}/llvm-strip llvm-strip %{install_prefix}/bin/llvm-strip \
  --slave %{_bindir}/llvm-readelf llvm-readelf %{install_prefix}/bin/llvm-readelf \
  --slave %{_bindir}/llvm-readobj llvm-readobj %{install_prefix}/bin/llvm-readobj \
  --slave %{_bindir}/llvm-symbolizer llvm-symbolizer %{install_prefix}/bin/llvm-symbolizer \
  --slave %{_bindir}/llvm-profdata llvm-profdata %{install_prefix}/bin/llvm-profdata \
  --slave %{_bindir}/llvm-cov llvm-cov %{install_prefix}/bin/llvm-cov \
  --slave %{_bindir}/llvm-config llvm-config %{install_prefix}/bin/llvm-config

%postun
if [ $1 -eq 0 ]; then
  alternatives --remove clang %{install_prefix}/bin/clang
fi

%files
%{install_prefix}
