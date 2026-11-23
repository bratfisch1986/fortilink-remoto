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
trocar("libs/portable/Cargo.toml", 'FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{NOME_VISIVEL}"')
rc = "flutter/windows/runner/Runner.rc"
trocar(rc, 'VALUE "FileDescription", "RustDesk Remote Desktop"', f'VALUE "FileDescription", "{NOME_VISIVEL}"')
trocar(rc, 'VALUE "ProductName", "RustDesk"', f'VALUE "ProductName", "{NOME_VISIVEL}"')

# 5) visual FortiLink (opção B: azul-escuro com botões verdes), tema escuro como padrão
cm = "flutter/lib/common.dart"
trocar(cm, "static const Color accent = Color(0xFF0071FF);", "static const Color accent = Color(0xFF8CC63F);")
trocar(cm, "static const Color accent50 = Color(0x770071FF);", "static const Color accent50 = Color(0x778CC63F);")
trocar(cm, "static const Color accent80 = Color(0xAA0071FF);", "static const Color accent80 = Color(0xAA8CC63F);")
trocar(cm, "static const Color button = Color(0xFF2C8CFF);", "static const Color button = Color(0xFF8CC63F);")
trocar(cm, "Color(0xFF18191E)", "Color(0xFF141A4A)", 2)
trocar(cm, "Color(0xFF24252B)", "Color(0xFF1E2664)", 5)
trocar(cm, "hoverColor: Color.fromARGB(255, 45, 46, 53),", "hoverColor: Color.fromARGB(255, 43, 52, 130),")
trocar(cm, """        backgroundColor: MyTheme.accent,
        foregroundColor: Colors.white,""", """        backgroundColor: MyTheme.accent,
        foregroundColor: Color(0xFF0F1E0A),""")
trocar(cm, """      case "dark":
        return ThemeMode.dark;
      default:
        return ThemeMode.system;""", """      case "dark":
        return ThemeMode.dark;
      case "system":
        return ThemeMode.system;
      default:
        return ThemeMode.dark;""")

# 6) exportar / importar a lista de computadores (com as senhas salvas), no menu ao lado de "Conectar"
ffi = "src/flutter_ffi.rs"
trocar(ffi, "pub fn main_uri_prefix_sync() -> SyncReturn<String> {", r"""// FortiLink Remoto: lista de computadores em um arquivo, para levar a outro computador.
pub fn main_fl_export_peers(path: String) -> String {
    use hbb_common::config::{LocalConfig, PeerConfig};
    let mut lista: Vec<serde_json::Value> = Vec::new();
    for (id, _, c) in PeerConfig::peers(None) {
        lista.push(serde_json::json!({
            "id": id,
            "senha": c.password,
            "apelido": c.options.get("alias").cloned().unwrap_or_default(),
            "usuario": c.info.username,
            "computador": c.info.hostname,
            "sistema": c.info.platform,
        }));
    }
    let n = lista.len();
    let doc = serde_json::json!({
        "formato": "fortilink-remoto-lista",
        "versao": 1,
        "favoritos": LocalConfig::get_fav(),
        "computadores": lista,
    });
    match std::fs::write(&path, doc.to_string()) {
        Ok(_) => format!("ok:{}", n),
        Err(e) => format!("erro:{}", e),
    }
}

pub fn main_fl_import_peers(path: String) -> String {
    use hbb_common::config::{LocalConfig, PeerConfig};
    match std::fs::metadata(&path) {
        Ok(m) if m.len() <= 20 * 1024 * 1024 => {}
        Ok(_) => return "erro:arquivo grande demais".to_owned(),
        Err(e) => return format!("erro:{}", e),
    }
    let texto = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) => return format!("erro:{}", e),
    };
    let doc: serde_json::Value = match serde_json::from_str(&texto) {
        Ok(d) => d,
        Err(_) => return "erro:este arquivo não é uma lista do FortiLink Remoto".to_owned(),
    };
    if doc.get("formato").and_then(|v| v.as_str()) != Some("fortilink-remoto-lista") {
        return "erro:este arquivo não é uma lista do FortiLink Remoto".to_owned();
    }
    let texto_de = |v: &serde_json::Value, k: &str| -> String {
        v.get(k)
            .and_then(|x| x.as_str())
            .unwrap_or("")
            .chars()
            .filter(|c| !c.is_control())
            .take(200)
            .collect()
    };
    let id_valido = |id: &str| -> bool {
        !id.is_empty()
            && id.len() <= 100
            && id
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || c == '@' || c == '.' || c == '-' || c == '_' || c == ':')
    };
    let mut n = 0;
    if let Some(lista) = doc.get("computadores").and_then(|v| v.as_array()) {
        for item in lista.iter().take(5000) {
            let id = texto_de(item, "id");
            if !id_valido(&id) {
                continue;
            }
            let mut c = PeerConfig::load(&id);
            if let Some(bytes) = item.get("senha").and_then(|v| v.as_array()) {
                let senha: Vec<u8> = bytes
                    .iter()
                    .take(256)
                    .filter_map(|b| b.as_u64())
                    .map(|b| b as u8)
                    .collect();
                if !senha.is_empty() {
                    c.password = senha;
                }
            }
            let apelido = texto_de(item, "apelido");
            if !apelido.is_empty() {
                c.options.insert("alias".to_owned(), apelido);
            }
            let (usuario, computador, sistema) = (
                texto_de(item, "usuario"),
                texto_de(item, "computador"),
                texto_de(item, "sistema"),
            );
            if !usuario.is_empty() {
                c.info.username = usuario;
            }
            if !computador.is_empty() {
                c.info.hostname = computador;
            }
            if !sistema.is_empty() {
                c.info.platform = sistema;
            }
            c.store(&id);
            n += 1;
        }
    }
    if let Some(favs) = doc.get("favoritos").and_then(|v| v.as_array()) {
        let mut atual = LocalConfig::get_fav();
        for f in favs.iter().take(5000) {
            if let Some(f) = f.as_str() {
                if id_valido(f) && !atual.iter().any(|x| x == f) {
                    atual.push(f.to_owned());
                }
            }
        }
        LocalConfig::set_fav(atual);
    }
    format!("ok:{}", n)
}

pub fn main_uri_prefix_sync() -> SyncReturn<String> {""")

cp = "flutter/lib/desktop/pages/connection_page.dart"
trocar(cp, "import 'package:get/get.dart';", "import 'package:get/get.dart';\nimport 'package:file_picker/file_picker.dart';")
trocar(cp, "  Widget _buildRemoteIDTextField(BuildContext context) {", """  // FortiLink Remoto: levar a lista de computadores para outro computador
  Future<void> _flExportarLista() async {
    String? arq = await FilePicker.platform.saveFile(
      dialogTitle: 'Exportar lista',
      fileName: 'condominios.fortilink',
      allowedExtensions: ['fortilink'],
      type: FileType.custom,
    );
    if (arq == null) return;
    if (!arq.toLowerCase().endsWith('.fortilink')) arq = '$arq.fortilink';
    final res = await bind.mainFlExportPeers(path: arq);
    if (res.startsWith('ok:')) {
      showToast(
          'Lista exportada: ${res.substring(3)} computador(es), com as senhas salvas. Guarde o arquivo com cuidado.',
          timeout: const Duration(seconds: 6));
    } else {
      showToast('Não foi possível exportar: ${res.replaceFirst('erro:', '')}',
          timeout: const Duration(seconds: 6));
    }
  }

  Future<void> _flImportarLista() async {
    final r = await FilePicker.platform.pickFiles(
      dialogTitle: 'Importar lista',
      type: FileType.any,
    );
    final arq = (r == null || r.files.isEmpty) ? null : r.files.first.path;
    if (arq == null) return;
    final res = await bind.mainFlImportPeers(path: arq);
    if (res.startsWith('ok:')) {
      bind.mainLoadRecentPeers();
      bind.mainLoadFavPeers();
      showToast('Lista importada: ${res.substring(3)} computador(es).',
          timeout: const Duration(seconds: 6));
    } else {
      showToast('Não foi possível importar: ${res.replaceFirst('erro:', '')}',
          timeout: const Duration(seconds: 6));
    }
  }

  Widget _buildRemoteIDTextField(BuildContext context) {""")
trocar(cp, """                                        'TCP tunneling',
                                        () => onConnect(isTcpTunneling: true)
                                      ),
""", """                                        'TCP tunneling',
                                        () => onConnect(isTcpTunneling: true)
                                      ),
                                    (
                                      'Exportar lista…',
                                      () {
                                        _flExportarLista();
                                      }
                                    ),
                                    (
                                      'Importar lista…',
                                      () {
                                        _flImportarLista();
                                      }
                                    ),
""")

# 6b) os mesmos comandos pela linha de comando (usados no teste automático)
trocar("src/core_main.rs", """        } else if args[0] == "--get-id" {""", """        } else if args[0] == "--fl-export-peers" && args.len() == 2 {
            println!("{}", crate::flutter_ffi::main_fl_export_peers(args[1].clone()));
            return None;
        } else if args[0] == "--fl-import-peers" && args.len() == 2 {
            println!("{}", crate::flutter_ffi::main_fl_import_peers(args[1].clone()));
            return None;
        } else if args[0] == "--get-id" {""")

# 7) desinstalar apaga também as pastas de dados (instalar por cima continua mantendo)
wr = "src/platform/windows.rs"
trocar(wr, """    run_cmds(get_uninstall(kill_self, true)?, true, "uninstall")""", r"""    let fl_dados = format!(
        "
    if exist \"%APPDATA%\\{n}\" rd /s /q \"%APPDATA%\\{n}\"
    if exist \"%SystemRoot%\\ServiceProfiles\\LocalService\\AppData\\Roaming\\{n}\" rd /s /q \"%SystemRoot%\\ServiceProfiles\\LocalService\\AppData\\Roaming\\{n}\"
    ",
        n = crate::get_app_name()
    );
    run_cmds(
        format!("{}{}", get_uninstall(kill_self, true)?, fl_dados),
        true,
        "uninstall",
    )""")

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
