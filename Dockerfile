# syntax=docker/dockerfile:1.6
#
# Build Clang 21 RPM on CentOS 7 via rpmbuild.
# All build logic lives in clang21-opt.spec.
#
# Requires base image built from Dockerfile.base:
#   docker build -t clang21-base -f Dockerfile.base .
#
# Usage:
#   docker build -t clang21-rpm .
#   docker run --rm -v "$PWD/out:/out" clang21-rpm \
#     bash -c 'cp /root/rpmbuild/{SRPMS,RPMS/x86_64}/*.rpm /out/'

ARG BASE_IMAGE=clang21-base
ARG LLVM_SRC=llvm-project-21.1.8.src.tar.xz

FROM ${BASE_IMAGE}

RUN sed -i \
      -e 's|^mirrorlist=|#mirrorlist=|g' \
      -e 's|^baseurl=http://vault.centos.org|baseurl=http://archive.kernel.org/centos-vault|g' \
      /etc/yum.repos.d/CentOS-*.repo && \
    yum -y --disablerepo='epel*' install rpm-build rpmdevtools curl && \
    yum clean all

# Install binary cmake/ninja (pip wrappers break under rpmbuild)
ARG CMAKE_VERSION=3.28.0
ARG NINJA_VERSION=1.12.1
RUN curl -fSL https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz \
      | tar xz --strip-components=1 -C /usr/local && \
    curl -fSL -o /tmp/ninja.zip https://github.com/ninja-build/ninja/releases/download/v${NINJA_VERSION}/ninja-linux.zip && \
    python3 -c "import zipfile; zipfile.ZipFile('/tmp/ninja.zip').extractall('/usr/local/bin')" && \
    chmod +x /usr/local/bin/ninja && rm /tmp/ninja.zip

RUN rpmdev-setuptree

ARG LLVM_SRC
COPY ${LLVM_SRC} /root/rpmbuild/SOURCES/
COPY clang21-opt.spec /root/rpmbuild/SPECS/

WORKDIR /root/rpmbuild
RUN rpmbuild -ba SPECS/clang21-opt.spec

CMD ["bash", "-c", "ls -lh SRPMS/*.rpm RPMS/x86_64/*.rpm"]
