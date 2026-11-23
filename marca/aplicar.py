#!/usr/bin/env python3
"""Aplica a marca FortiLink Remoto sobre o código do RustDesk (versão fixa, baixada pelo GitHub Actions).

Uso: python3 marca/aplicar.py <pasta do código do RustDesk>
Cada troca é conferida: se o trecho esperado não existir (versão diferente), o script para com erro.
Servidor e chave pública são opcionais (variáveis FL_SERVIDOR e FL_CHAVE); sem elas, o programa
sai sem servidor gravado e é configurado depois (como o Servidor da interfonia já faz).
"""
import os, re, shutil, sys

NOME_INTERNO = "FortiLinkRemoto"      # sem espaço: vira nome do serviço, da pasta e do link (fortilinkremoto://)
NOME_VISIVEL = "FortiLink Remoto"

raiz = sys.argv[1]
aqui = os.path.dirname(os.path.abspath(__file__))


def trocar(arquivo, antigo, novo, vezes=1):
    caminho = os.path.join(raiz, arquivo)
    with open(caminho, encoding="utf-8") as f:
        texto = f.read()
    n = texto.count(antigo)
    if n != vezes:
        sys.exit(f"ERRO: {arquivo}: esperava {vezes}x '{antigo}', achei {n}x. Versão do RustDesk diferente?")
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(texto.replace(antigo, novo))
    print(f"ok  {arquivo}: '{antigo}' -> '{novo}'")


# 1) nome do programa
cfg = "libs/hbb_common/src/config.rs"
trocar(cfg, 'RwLock::new("RustDesk".to_owned())', f'RwLock::new("{NOME_INTERNO}".to_owned())')

# 2) servidor próprio gravado (opcional)
servidor = os.environ.get("FL_SERVIDOR", "").strip()
chave = os.environ.get("FL_CHAVE", "").strip()
if servidor or chave:
    if not re.fullmatch(r"[A-Za-z0-9.-]{4,120}", servidor):
        sys.exit("ERRO: FL_SERVIDOR inválido")
    if not re.fullmatch(r"[A-Za-z0-9+/=]{40,60}", chave):
        sys.exit("ERRO: FL_CHAVE inválida")
    trocar(cfg, '&["rs-ny.rustdesk.com"]', f'&["{servidor}"]')
    trocar(cfg, 'RS_PUB_KEY: &str = "OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw="', f'RS_PUB_KEY: &str = "{chave}"')
else:
    print("--  sem servidor gravado (FL_SERVIDOR/FL_CHAVE vazios)")

# 3) textos que o Windows mostra (Propriedades do arquivo, Gerenciador de Tarefas)
trocar("Cargo.toml", 'ProductName = "RustDesk"', f'ProductName = "{NOME_VISIVEL}"')
trocar("Cargo.toml", 'FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{NOME_VISIVEL}"')
trocar("libs/portable/Cargo.toml", 'ProductName = "RustDesk"', f'ProductName = "{NOME_VISIVEL}"')
rc = "flutter/windows/runner/Runner.rc"
trocar(rc, 'VALUE "FileDescription", "RustDesk Remote Desktop"', f'VALUE "FileDescription", "{NOME_VISIVEL}"')
trocar(rc, 'VALUE "ProductName", "RustDesk"', f'VALUE "ProductName", "{NOME_VISIVEL}"')

# 4) ícones e logotipo
img = os.path.join(aqui, "imagens")
copias = {
    "icon.ico": ["res/icon.ico", "flutter/windows/runner/resources/app_icon.ico"],
    "tray-icon.ico": ["res/tray-icon.ico"],
    "icon.png": ["res/icon.png", "flutter/assets/icon.png"],
    "logo.png": ["flutter/assets/logo.png"],
    "32x32.png": ["res/32x32.png"],
    "64x64.png": ["res/64x64.png"],
    "128x128.png": ["res/128x128.png"],
    "128x128@2x.png": ["res/128x128@2x.png"],
}
for origem, destinos in copias.items():
    for d in destinos:
        alvo = os.path.join(raiz, d)
        if not os.path.isdir(os.path.dirname(alvo)):
            sys.exit(f"ERRO: pasta de {d} não existe")
        shutil.copyfile(os.path.join(img, origem), alvo)
        print(f"ok  {d}")
print("Marca aplicada.")
