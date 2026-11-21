#!/usr/bin/env bash
# Extrai o pacote do pendrive no disco do notebook e instala.
# Uso: bash instalar-notebook.sh [pasta-destino]   (padrão: ~/ipeia-academico)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP="$HERE/ipeia-academico.zip"
DEST="${1:-$HOME/ipeia-academico}"

if [ ! -f "$ZIP" ]; then
    echo "ERRO: não achei $ZIP. Rode este script de dentro da pasta IPeia-Academico do pendrive."
    exit 1
fi
if ! command -v unzip &> /dev/null; then
    echo "ERRO: falta o unzip. Instale com: sudo apt install -y unzip"
    exit 1
fi
if [ -e "$DEST" ]; then
    echo "ERRO: $DEST já existe. Para não apagar nada, escolha outra pasta:"
    echo "  bash instalar-notebook.sh /caminho/novo"
    exit 1
fi
case "$(df -T "$(dirname "$DEST")" 2>/dev/null | awk 'NR==2 {print $2}')" in
    exfat|vfat|msdos|fuseblk)
        echo "ERRO: o destino está num disco FAT/exFAT. Use uma pasta do disco do notebook."
        exit 1
        ;;
esac

echo "Extraindo em $DEST ..."
mkdir -p "$DEST"
unzip -q "$ZIP" -d "$DEST"
cd "$DEST"
bash scripts/install-ubuntu.sh
echo ""
echo "Instalado em $DEST. Para rodar: bash $DEST/scripts/rodar-ubuntu.sh"
