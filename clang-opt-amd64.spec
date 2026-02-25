%{!?llvm_major: %define llvm_major 22}
%{!?llvm_version: %define llvm_version 22.1.0}

%define install_prefix /opt/clang%{llvm_major}
%define stage1_prefix /opt/clang%{llvm_major}-stage1

Name:           clang%{llvm_major}-opt
Version:        %{llvm_version}
Release:        1.el7
Summary:        LLVM/Clang %{llvm_major} under /opt — static libc++ with dynamic glibc 2.17
License:        Apache-2.0 WITH LLVM-exception
URL:            https://llvm.org/
Source0:        llvm-project-%{version}.src.tar.xz
ExclusiveArch:  x86_64

# cmake >= 3.20 and ninja required (install via pip)
# Stage1 clang required at %{stage1_prefix} (from Dockerfile.amd64-base)
BuildRequires:  devtoolset-11-gcc-c++
BuildRequires:  zlib-devel
BuildRequires:  libxml2-devel

Requires:       glibc-devel
Requires:       libgcc
Requires:       zlib
Requires:       libxml2

%description
LLVM/Clang %{llvm_major} toolchain installed under %{install_prefix}.
Built with static libc++/libc++abi/libunwind, dynamic glibc 2.17.
Compiled-in defaults: libc++, compiler-rt, lld.

%prep
%setup -q -n llvm-project-%{version}.src

%build
source /opt/rh/devtoolset-11/enable
export CC=%{stage1_prefix}/bin/clang
export CXX=%{stage1_prefix}/bin/clang++

mkdir -p _build && cd _build
cmake -G Ninja ../llvm \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=%{install_prefix} \
  -DLLVM_ENABLE_PROJECTS="clang;lld" \
  -DLLVM_ENABLE_RUNTIMES="compiler-rt;libcxx;libcxxabi;libunwind" \
  -DLLVM_TARGETS_TO_BUILD="X86" \
  -DLLVM_ENABLE_TERMINFO=OFF \
  -DLLVM_ENABLE_ZLIB=ON \
  -DLLVM_INCLUDE_TESTS=OFF \
  -DLLVM_INCLUDE_EXAMPLES=OFF \
  -DLLVM_INCLUDE_BENCHMARKS=OFF \
  -DLLVM_ENABLE_LLD=ON \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--build-id" \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,--build-id" \
  -DLLVM_STATIC_LINK_CXX_STDLIB=ON \
  -DCLANG_DEFAULT_CXX_STDLIB=libc++ \
  -DCLANG_DEFAULT_RTLIB=compiler-rt \
  -DCLANG_DEFAULT_LINKER=lld \
  -DCOMPILER_RT_BUILD_CRT=ON \
  -DLIBCXX_ENABLE_SHARED=OFF \
  -DLIBCXXABI_ENABLE_SHARED=OFF \
  -DLIBUNWIND_ENABLE_SHARED=OFF \
  -DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON

ninja

%install
cd _build
DESTDIR=%{buildroot} ninja install

# Fix ambiguous python shebangs
find %{buildroot}%{install_prefix} -type f -executable -exec \
  sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +
find %{buildroot}%{install_prefix} -type f -name '*.py' -exec \
  sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +

mkdir -p %{buildroot}%{install_prefix}/toolchains
cat > %{buildroot}%{install_prefix}/toolchains/centos7-clang%{llvm_major}.cmake <<'CMAKE'
set(CLANG_PREFIX "%{install_prefix}" CACHE PATH "")
set(CMAKE_C_COMPILER   "${CLANG_PREFIX}/bin/clang"  CACHE FILEPATH "")
set(CMAKE_CXX_COMPILER "${CLANG_PREFIX}/bin/clang++" CACHE FILEPATH "")
set(CMAKE_PREFIX_PATH "${CLANG_PREFIX}" CACHE PATH "")
CMAKE

mkdir -p %{buildroot}%{install_prefix}/share/doc/%{name}
cat > %{buildroot}%{install_prefix}/share/doc/%{name}/README.md <<EOF
# %{name}

Installed under: %{install_prefix}
LLVM version: %{version}

Compiled-in defaults: libc++, compiler-rt, lld.
libunwind is available but not the default unwinder.
Only static libraries (.a) are shipped — no extra flags needed.

## Quick usage
    export PATH=%{install_prefix}/bin:\$PATH
    clang++ -std=c++20 hello.cpp -o hello

## CMake toolchain
    cmake -S . -B build \\
      -DCMAKE_TOOLCHAIN_FILE=%{install_prefix}/toolchains/centos7-clang%{llvm_major}.cmake
EOF

%files
%{install_prefix}

%changelog
* Wed Feb 25 2026 Builder <zhangsong325@gmail.com> - 22.1.0-1.el7
- Update to LLVM 22.1.0

* Fri Feb 13 2026 Builder <zhangsong325@gmail.com> - 21.1.8-1.el7
- Initial RPM build with static libc++ toolchain
