# Network Doodles lab · Networking 101, part 2: hands on
# Guide: https://networkdoodles.com/labs/networking-101-lab/
#
# Tasks are numbered chapter.task, so T=2.1 is chapter 2, task 1. CH=<n> means a whole chapter.
.DEFAULT_GOAL := help
# The dev container keeps its venv outside the repo (VENV is set there); locally it is .venv.
VENV ?= .venv
PY := $(VENV)/bin/python
TOPO := lab/topology.clab.yml
BOLT := ghcr.io/dkhenderson2/capeos-bolt:0.11.0
HOST := nd-host:1
NODES := laptop printer broken-pc web dns sw1 r1 r2
T ?=
CH ?=
H ?=

help: ## show this help
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

REQS := requirements.txt
REQ_HASH = $(shell python3 -c "import hashlib,sys; print(hashlib.sha256(b''.join(open(f,'rb').read() for f in sys.argv[1:])).hexdigest()[:16])" $(REQS))

setup: ## create the Python venv the checker uses
	@if [ "$$(cat $(VENV)/.ok 2>/dev/null)" = "$(REQ_HASH)" ] && [ -x $(PY) ]; then exit 0; fi; \
	echo "installing the checker's Python packages into $(VENV)"; \
	if command -v uv >/dev/null; then \
	  uv venv -q --allow-existing --python 3.13 $(VENV) && uv pip install -q --python $(PY) -r $(REQS); \
	else \
	  python3 -m venv $(VENV) && $(PY) -m pip install -q -r $(REQS); \
	fi && echo "$(REQ_HASH)" > $(VENV)/.ok

# The dev container's own Docker engine starts alongside the container, so the first commands can beat it.
docker-ready:
	@for i in $$(seq 1 60); do docker info >/dev/null 2>&1 && exit 0; [ $$i = 1 ] && echo "  waiting for Docker to start ..."; sleep 2; done; \
	echo "Docker isn't answering. In the dev container it starts on its own; on a laptop, start Docker Desktop."; exit 1

images: docker-ready ## pull the switch image and build the hosts' image (the dev container does this once)
	@docker image inspect $(BOLT) >/dev/null 2>&1 || docker pull -q $(BOLT)
	@docker build -q -t $(HOST) lab/host >/dev/null && echo "  built $(HOST), the lab's hosts"

up: setup docker-ready ## start the network: a switch, two routers and five hosts (about a minute)
	@command -v containerlab >/dev/null || (echo "containerlab isn't installed: it comes with the dev container"; exit 2)
	@# The hosts' image builds in seconds from cache, and picks up any change to lab/host/.
	@$(MAKE) -s images
	containerlab deploy -t $(TOPO) --reconfigure
	@$(PY) lab/wait.py

down: ## remove the network
	containerlab destroy -t $(TOPO) --cleanup

reset: ## everything back to how it started (your answers files are untouched)
	$(MAKE) up

shell: ## log in to a host, the switch or a router:  make shell H=laptop
	@case " $(NODES) " in *" $(H) "*) ;; *) echo "usage: make shell H=<name>   one of: $(NODES)"; exit 2;; esac
	@case "$(H)" in sw1|r1|r2) docker exec -it $(H) capeos-cli;; *) docker exec -it -w /root $(H) bash;; esac

status: ## what's running, and where to start  (WAIT=1 waits for the network)
	@$(PY) lab/status.py $(if $(WAIT),--wait)

check: ## verify a task, a chapter or everything:  make check T=1.1 · CH=1 · (nothing)
	@$(PY) checks/check.py $(if $(T),$(T),$(if $(CH),ch$(CH),all))

solve: ## stuck, or skipped a task? do it for you, and fill in its answers:  make solve T=1.2
	@test -n "$(T)" || (echo "usage: make solve T=<chapter.task>, e.g. T=1.2"; exit 2)
	@$(PY) lab/solve.py solve $(T)

break: ## set up a task's problem on purpose:  make break T=3.1
	@test -n "$(T)" || (echo "usage: make break T=3.1"; exit 2)
	@$(PY) lab/solve.py break $(T)

.PHONY: help setup docker-ready images up down reset shell status check solve break
