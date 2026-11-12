# The lab's dev container: containerlab's Docker-in-Docker image plus the checker's Python venv.
# The venv is built here, in the image, so it's ready from the first second.
FROM ghcr.io/srl-labs/containerlab/devcontainer-dind-slim:0.82.0

USER vscode
ENV VENV=/home/vscode/.venvs/lab
ENV PATH=/home/vscode/.venvs/lab/bin:$PATH
COPY --chown=vscode:vscode requirements.txt /tmp/lab/
# .ok records which requirements were installed (the same hash `make setup` checks), so the first start
# doesn't reinstall them.
RUN uv venv -q --python 3.13 "$VENV" \
 && uv pip install -q --python "$VENV/bin/python" -r /tmp/lab/requirements.txt \
 && cd /tmp/lab && python3 -c "import hashlib,sys; print(hashlib.sha256(b''.join(open(f,'rb').read() for f in sys.argv[1:])).hexdigest()[:16])" requirements.txt > "$VENV/.ok"

# code-server reads its own settings, not devcontainer.json's.
COPY --chown=vscode:vscode .devcontainer/code-server-settings.json /home/vscode/.local/share/code-server/User/settings.json

USER root
# Caddy puts the lab app and its VS Code tab (code-server) behind one port: see .devcontainer/lab-ui/.
ARG TARGETARCH
ARG CADDY=2.10.2
RUN case "$TARGETARCH" in \
      amd64) sum=747df7ee74de188485157a383633a1a963fd9233b71fbb4a69ddcbcc589ce4e2cc82dacf5dbbe136cb51d17e14c59daeb5d9bc92487610b0f3b93680b2646546 ;; \
      arm64) sum=6ce061a690312ab38367df3c5d5f89a2e4a263e7300d300d87356211bb81e79b15933e6d6203e03fbf26f15cc0311f264805f336147dbdd24938d84b57a4421c ;; \
      *) echo "no Caddy for $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && curl -fsSL -o /tmp/caddy.tgz "https://github.com/caddyserver/caddy/releases/download/v${CADDY}/caddy_${CADDY}_linux_${TARGETARCH}.tar.gz" \
 && echo "$sum  /tmp/caddy.tgz" | sha512sum -c - \
 && tar xzf /tmp/caddy.tgz -C /usr/local/bin caddy && rm /tmp/caddy.tgz && caddy version
# cloudflared: when the lab is opened from the site ("Open lab"), the lab app reaches you through a Cloudflare
# tunnel instead of Codespaces' port forwarding, which only exists while the GitHub editor is open.
ARG CLOUDFLARED=2026.10.7
RUN case "$TARGETARCH" in \
      amd64) sum=1f99fb518b83dec2ba8d870a7cc991d82a77e6196295a3d2754ba17ab9f91872 ;; \
      arm64) sum=3df43aedc9ff291d1735b5cb576cb97e0b157488796db2e32b28aecabb445775 ;; \
      *) echo "no cloudflared for $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && curl -fsSL -o /usr/local/bin/cloudflared "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED}/cloudflared-linux-${TARGETARCH}" \
 && echo "$sum  /usr/local/bin/cloudflared" | sha256sum -c - \
 && chmod 755 /usr/local/bin/cloudflared && cloudflared --version
# ttyd: the lab app's web terminals. Click a device on the Topology tab and its shell opens in a tab.
ARG TTYD=1.7.7
RUN case "$TARGETARCH" in \
      amd64) arch=x86_64 sum=8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55 ;; \
      arm64) arch=aarch64 sum=b38acadd89d1d396a0f5649aa52c539edbad07f4bc7348b27b4f4b7219dd4165 ;; \
      *) echo "no ttyd for $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && curl -fsSL -o /usr/local/bin/ttyd "https://github.com/tsl0922/ttyd/releases/download/${TTYD}/ttyd.${arch}" \
 && echo "$sum  /usr/local/bin/ttyd" | sha256sum -c - \
 && chmod 755 /usr/local/bin/ttyd && ttyd --version
USER vscode
