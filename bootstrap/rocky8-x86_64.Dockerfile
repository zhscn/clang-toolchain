FROM rockylinux:8

ARG CMAKE_VERSION=3.31.10
ARG NINJA_VERSION=1.12.1

SHELL ["/bin/bash", "-lc"]

RUN dnf install -y epel-release && \
    dnf install -y \
      bzip2 \
      ca-certificates \
      curl \
      file \
      git \
      make \
      patch \
      python3 \
      rpm-build \
      rpmdevtools \
      tar \
      unzip \
      which \
      xz \
      zlib-devel \
      gcc-toolset-12-binutils \
      gcc-toolset-12-gcc \
      gcc-toolset-12-gcc-c++

ENV PATH=/opt/rh/gcc-toolset-12/root/usr/bin:$PATH

RUN curl -fsSL -o /tmp/cmake.tgz "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz" && \
    tar -C /opt -xzf /tmp/cmake.tgz && \
    ln -sf "/opt/cmake-${CMAKE_VERSION}-linux-x86_64/bin/cmake" /usr/local/bin/cmake && \
    ln -sf "/opt/cmake-${CMAKE_VERSION}-linux-x86_64/bin/ctest" /usr/local/bin/ctest && \
    ln -sf "/opt/cmake-${CMAKE_VERSION}-linux-x86_64/bin/cpack" /usr/local/bin/cpack && \
    curl -fsSL -o /tmp/ninja.tar.gz "https://github.com/ninja-build/ninja/archive/refs/tags/v${NINJA_VERSION}.tar.gz" && \
    tar -C /tmp -xzf /tmp/ninja.tar.gz && \
    cd "/tmp/ninja-${NINJA_VERSION}" && \
    python3 configure.py --bootstrap && \
    cp ninja /usr/local/bin/ninja && \
    dnf clean all && \
    rm -rf /var/cache/dnf /tmp/cmake.tgz /tmp/ninja.tar.gz "/tmp/ninja-${NINJA_VERSION}"

WORKDIR /work
