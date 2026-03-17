%{!?llvm_major: %define llvm_major 19}
%{!?llvm_version: %define llvm_version 19.1.7}

%define install_prefix /opt/clang%{llvm_major}
# Use clang22 stage1 as bootstrap compiler
%define stage1_prefix /opt/clang22-stage1
%define debug_package %{nil}

Name:           clang%{llvm_major}-opt
Version:        %{llvm_version}
Release:        1.el8
Summary:        LLVM/Clang %{llvm_major} under /opt — static libc++ with dynamic glibc 2.28
License:        Apache-2.0 WITH LLVM-exception
URL:            https://llvm.org/
Source0:        llvm-project-%{version}.src.tar.xz
ExclusiveArch:  aarch64

BuildRequires:  gcc-toolset-11-gcc-c++
BuildRequires:  zlib-devel
BuildRequires:  libxml2-devel

Requires:       glibc-devel
Requires:       gcc
Requires:       libgcc
Requires:       zlib
Requires:       libxml2

%description
LLVM/Clang %{llvm_major} toolchain installed under %{install_prefix}.
Built with static libc++/libc++abi/libunwind, dynamic glibc 2.28.
Compiled-in defaults: libc++, compiler-rt, lld.

%prep
%setup -q -n llvm-project-%{version}.src

%build
source /opt/rh/gcc-toolset-11/enable
export CC=%{stage1_prefix}/bin/clang
export CXX=%{stage1_prefix}/bin/clang++
export LDFLAGS="-Wl,--build-id"

mkdir -p _build && cd _build
cmake -G Ninja ../llvm \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=%{install_prefix} \
  -DLLVM_ENABLE_PROJECTS="clang;lld" \
  -DLLVM_ENABLE_RUNTIMES="compiler-rt;libcxx;libcxxabi;libunwind" \
  -DLLVM_TARGETS_TO_BUILD="AArch64" \
  -DLLVM_ENABLE_TERMINFO=OFF \
  -DLLVM_ENABLE_ZLIB=ON \
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
  -DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON \
  -DLIBCXXABI_ENABLE_SHARED=OFF \
  -DLIBUNWIND_ENABLE_SHARED=OFF

ninja

# Step 2: Build compiler-rt sanitizers standalone (libc++.a now available)
cd ..
mkdir -p _build-rt && cd _build-rt
cmake -G Ninja ../compiler-rt \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=%{install_prefix}/lib/clang/%{llvm_major} \
  -DCMAKE_C_COMPILER=%{_builddir}/llvm-project-%{version}.src/_build/bin/clang \
  -DCMAKE_CXX_COMPILER=%{_builddir}/llvm-project-%{version}.src/_build/bin/clang++ \
  -DCMAKE_C_COMPILER_TARGET=aarch64-unknown-linux-gnu \
  -DCMAKE_CXX_COMPILER_TARGET=aarch64-unknown-linux-gnu \
  -DCOMPILER_RT_BUILD_BUILTINS=OFF \
  -DCOMPILER_RT_BUILD_CRT=OFF \
  -DCOMPILER_RT_BUILD_SANITIZERS=ON \
  -DCOMPILER_RT_INCLUDE_TESTS=OFF \
  -DLLVM_CONFIG_PATH=%{_builddir}/llvm-project-%{version}.src/_build/bin/llvm-config

ninja

%install
cd _build
DESTDIR=%{buildroot} ninja install
cd ../_build-rt
DESTDIR=%{buildroot} ninja install

# Fix ambiguous python shebangs
find %{buildroot}%{install_prefix} -type f -executable -exec \
  sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +
find %{buildroot}%{install_prefix} -type f -name '*.py' -exec \
  sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +

mkdir -p %{buildroot}%{install_prefix}/toolchains
cat > %{buildroot}%{install_prefix}/toolchains/centos8-clang%{llvm_major}.cmake <<'CMAKE'
set(CLANG_PREFIX "%{install_prefix}" CACHE PATH "")
set(CMAKE_C_COMPILER   "${CLANG_PREFIX}/bin/clang"  CACHE FILEPATH "")
set(CMAKE_CXX_COMPILER "${CLANG_PREFIX}/bin/clang++" CACHE FILEPATH "")
set(CMAKE_PREFIX_PATH "${CLANG_PREFIX}" CACHE PATH "")
CMAKE

%files
%{install_prefix}

%changelog
* Mon Mar 17 2026 Builder <zhangsong325@gmail.com> - 19.1.7-1.el8
- Clang 19 built with clang22 stage1 bootstrap
