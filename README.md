# FortiLink Remoto

Programa de acesso remoto da FortiLink, feito a partir do [RustDesk](https://github.com/rustdesk/rustdesk) (versão 1.5.3).

- **Não é um produto oficial do RustDesk** nem tem ligação com a equipe do RustDesk.
- **Licença:** AGPL-3.0, a mesma do RustDesk. O código-fonte completo é o do RustDesk na versão fixada em
  `.github/workflows/gerar.yml` mais as mudanças deste repositório (`marca/aplicar.py` e `marca/imagens/`).
- **O que muda em relação ao RustDesk:** nome do programa, ícone, logotipo e, quando configurado, o servidor próprio.

## Como é gerado
O GitHub Actions (`Gerar FortiLink Remoto (Windows)`) baixa o código do RustDesk na versão conferida, aplica a marca,
compila o programa de Windows (64 bits) e testa num Windows limpo: instalar, configurar, instalar por cima e desinstalar.

## Nomes
- Nome visível: **FortiLink Remoto**
- Nome interno (serviço do Windows, pasta e link): `FortiLinkRemoto` / `fortilinkremoto://` — nunca muda, para a atualização por cima funcionar.
