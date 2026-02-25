LLVM_VERSION   ?= 22.1.0
LLVM_MAJOR     := $(firstword $(subst ., ,$(LLVM_VERSION)))
LLVM_SRC       := llvm-project-$(LLVM_VERSION).src.tar.xz
LLVM_URL       := https://github.com/llvm/llvm-project/releases/download/llvmorg-$(LLVM_VERSION)/$(LLVM_SRC)

UNAME_ARCH     := $(shell uname -m)
ifeq ($(UNAME_ARCH),x86_64)
  ARCH         ?= amd64
else ifeq ($(UNAME_ARCH),aarch64)
  ARCH         ?= aarch64
else
  ARCH         ?= $(UNAME_ARCH)
endif

OUTDIR         ?= out

ifeq ($(ARCH),amd64)
  RPM_ARCH     := x86_64
else ifeq ($(ARCH),aarch64)
  RPM_ARCH     := aarch64
else
  $(error Unsupported ARCH=$(ARCH). Expected amd64 or aarch64)
endif

DOCKERFILE_BASE       := Dockerfile.$(ARCH)-base
DOCKERFILE_RPM        := Dockerfile.$(ARCH)
BASE_IMAGE            ?= clang$(LLVM_MAJOR)-$(ARCH)-base
RPM_IMAGE             ?= clang$(LLVM_MAJOR)-$(ARCH)-rpm

.PHONY: all base rpm extract clean

all: extract

$(LLVM_SRC):
	curl -fSL -o $@ $(LLVM_URL)

base: $(LLVM_SRC)
	docker build -t $(BASE_IMAGE) -f $(DOCKERFILE_BASE) \
	  --build-arg LLVM_MAJOR=$(LLVM_MAJOR) \
	  --build-arg LLVM_SRC=$(LLVM_SRC) \
	  .

rpm: base
	docker build -t $(RPM_IMAGE) -f $(DOCKERFILE_RPM) \
	  --build-arg BASE_IMAGE=$(BASE_IMAGE) \
	  --build-arg LLVM_MAJOR=$(LLVM_MAJOR) \
	  --build-arg LLVM_VERSION=$(LLVM_VERSION) \
	  --build-arg LLVM_SRC=$(LLVM_SRC) \
	  .

extract: rpm
	mkdir -p $(OUTDIR)
	docker run --rm -v "$(CURDIR)/$(OUTDIR):/out" $(RPM_IMAGE) \
	  bash -c 'cp /root/rpmbuild/SRPMS/*.rpm /root/rpmbuild/RPMS/$(RPM_ARCH)/*.rpm /out/'
	@echo "RPMs in $(OUTDIR)/:"
	@ls -lh $(OUTDIR)/*.rpm

clean:
	rm -rf $(OUTDIR)
	-docker rmi $(RPM_IMAGE) $(BASE_IMAGE)
