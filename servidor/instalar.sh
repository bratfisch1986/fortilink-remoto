#!/usr/bin/env bash
# FortiLink Remoto - servidor de acesso próprio (número/encontro e repasse), separado de tudo no VPS.
# Não encosta na interfonia nem no CondiNota: usuário, pastas, portas e serviços próprios.
#   portas: TCP 21125-21127 e UDP 21126   (a interfonia continua em 21115-21117)
#   pastas: /opt/fortilink-remoto-servidor (programas) e /var/lib/fortilink-remoto-servidor (chave)
# Pode rodar de novo quantas vezes quiser: só atualiza o que mudou e mantém a chave.
set -euo pipefail
VER=1.1.16
SHA=0565c41affe6c3f409b0bddfaf5a24ccbf3f64f5f8e3fec250b69a0d5f6bdbcf
ENDERECO=remoto.fortilinkseg.com.br
DIR=/opt/fortilink-remoto-servidor
DADOS=/var/lib/fortilink-remoto-servidor
USR=fortilink-remoto
[ "$(id -u)" = 0 ] || { echo "Rode como root (no terminal do VPS na Hostinger)."; exit 1; }
[ "$(uname -m)" = x86_64 ] || { echo "Processador não suportado."; exit 1; }

if [ ! -x "$DIR/hbbs" ] || [ "$(cat "$DIR/.versao" 2>/dev/null || true)" != "$VER" ]; then
  T=$(mktemp -d)
  curl -fsSL --max-time 180 -o "$T/a.zip" "https://github.com/rustdesk/rustdesk-server/releases/download/$VER/rustdesk-server-linux-amd64.zip"
  echo "$SHA  $T/a.zip" | sha256sum -c --quiet - || { rm -rf "$T"; echo "ERRO: arquivo baixado não confere (SHA-256). Nada foi instalado."; exit 1; }
  python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$T/a.zip" "$T/x"
  HS=$(find "$T/x" -type f -name hbbs | head -1); HR=$(find "$T/x" -type f -name hbbr | head -1)
  [ -n "$HS" ] && [ -n "$HR" ] || { rm -rf "$T"; echo "ERRO: pacote sem os programas."; exit 1; }
  mkdir -p "$DIR"; install -m 755 "$HS" "$DIR/hbbs"; install -m 755 "$HR" "$DIR/hbbr"; echo "$VER" > "$DIR/.versao"; rm -rf "$T"
fi
id "$USR" >/dev/null 2>&1 || useradd --system --home "$DADOS" --shell /usr/sbin/nologin "$USR"
mkdir -p "$DADOS"; chown "$USR:$USR" "$DADOS"; chmod 755 "$DADOS"

for P in id repasse; do
  if [ $P = id ]; then CMD="$DIR/hbbs -p 21126 -r $ENDERECO:21127 -k _"; DESC="numero e encontro"; else CMD="$DIR/hbbr -p 21127 -k _"; DESC="repasse"; fi
  cat > /etc/systemd/system/fortilink-remoto-$P.service <<UNI
[Unit]
Description=FortiLink Remoto - servidor de acesso ($DESC)
After=network-online.target
Wants=network-online.target

[Service]
User=$USR
Group=$USR
WorkingDirectory=$DADOS
ExecStart=$CMD
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DADOS
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
MemoryMax=200M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
UNI
done
systemctl daemon-reload
systemctl enable -q fortilink-remoto-id fortilink-remoto-repasse
systemctl restart fortilink-remoto-id fortilink-remoto-repasse
for _ in $(seq 1 15); do [ -s "$DADOS/id_ed25519.pub" ] && break; sleep 1; done
systemctl is-active -q fortilink-remoto-id && systemctl is-active -q fortilink-remoto-repasse || { journalctl -u fortilink-remoto-id -u fortilink-remoto-repasse -n 20 --no-pager; echo "ERRO: o servidor não iniciou."; exit 1; }
[ -s "$DADOS/id_ed25519.pub" ] || { echo "ERRO: a chave não foi criada."; exit 1; }
chmod 644 "$DADOS/id_ed25519.pub"; chmod 600 "$DADOS/id_ed25519"
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw allow 21125:21127/tcp >/dev/null; ufw allow 21126/udp >/dev/null; fi
echo
echo "OK: FortiLink Remoto - servidor de acesso rodando (TCP 21125-21127, UDP 21126)."
echo "Interfonia continua em 21115-21117, sem alteração."
echo "CHAVE PÚBLICA (pode copiar e mandar ao Claude, não é segredo):"
cat "$DADOS/id_ed25519.pub"; echo
