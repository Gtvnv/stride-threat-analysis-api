"""Gera images/exemplo-arquitetura.png: diagrama simples de três camadas.

Uso: python tools/gerar_diagrama.py
Requer Pillow (dependência de desenvolvimento).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESTINO = Path(__file__).resolve().parent.parent / "images" / "exemplo-arquitetura.png"

LARGURA, ALTURA = 900, 420
CAIXAS = [
    ("Navegador do usuario", "Camada de apresentacao", (40, 150, 250, 270)),
    ("API Web (HTTPS)", "Camada de aplicacao", (340, 150, 560, 270)),
    ("Banco de dados", "Camada de dados", (650, 150, 860, 270)),
]


def _caixa(draw, fonte, titulo, subtitulo, coords):
    x0, y0, x1, y1 = coords
    draw.rectangle(coords, fill="#e8f0fe", outline="#1a3c6e", width=3)
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2 - 12), titulo, fill="black", font=fonte, anchor="mm")
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2 + 14), subtitulo, fill="#444444", font=fonte, anchor="mm")


def _seta(draw, fonte, inicio, fim, rotulo):
    draw.line([inicio, fim], fill="#1a3c6e", width=3)
    x, y = fim
    draw.polygon([(x, y), (x - 12, y - 7), (x - 12, y + 7)], fill="#1a3c6e")
    draw.text(((inicio[0] + fim[0]) / 2, inicio[1] - 14), rotulo, fill="black", font=fonte, anchor="mm")


def gerar() -> Path:
    imagem = Image.new("RGB", (LARGURA, ALTURA), "white")
    draw = ImageDraw.Draw(imagem)
    fonte = ImageFont.load_default()

    draw.text((LARGURA / 2, 40), "Arquitetura de tres camadas", fill="black", font=fonte, anchor="mm")
    # Fronteira de confiança entre a internet e a rede interna.
    draw.line([(295, 80), (295, 340)], fill="#b00020", width=2)
    draw.text((295, 360), "Fronteira de confianca", fill="#b00020", font=fonte, anchor="mm")

    for titulo, subtitulo, coords in CAIXAS:
        _caixa(draw, fonte, titulo, subtitulo, coords)

    _seta(draw, fonte, (250, 210), (340, 210), "HTTPS")
    _seta(draw, fonte, (560, 210), (650, 210), "SQL")

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(DESTINO, format="PNG")
    return DESTINO


if __name__ == "__main__":
    print(f"Imagem gerada em {gerar()}")
