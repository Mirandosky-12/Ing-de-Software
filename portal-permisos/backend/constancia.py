"""
constancia.py — Constancia de solicitud en PDF, sin dependencias.

El PDF se escribe a mano: una página A4 con las fuentes estándar que trae todo
lector de PDF (Helvetica y Courier) en WinAnsiEncoding, que cubre tildes y
eñes. Así la imagen de la API no crece con una librería de PDF.

La constancia acredita que la solicitud se recibió; no es el permiso.
"""

from __future__ import annotations

import textwrap
from datetime import date, datetime

ANCHO, ALTO = 595, 842                  # A4 en puntos
MARGEN = 56
COL_VALOR = MARGEN + 150                # donde empiezan los valores de cada fila
AZUL = b"0.043 0.310 0.541"             # --brand del portal (#0b4f8a)
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(valor: str) -> str:
    """'2026-10-18' o '2026-10-06T21:04:11+00:00' → '18 de octubre de 2026'."""
    d = (datetime.fromisoformat(valor) if "T" in valor else date.fromisoformat(valor))
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# ------------------------------------------------------------------ dibujo

def _cadena(texto: str) -> bytes:
    """Texto como cadena literal de PDF: escapa \\ ( ) y codifica en WinAnsi."""
    texto = texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return texto.encode("cp1252", errors="replace")


class _Pagina:
    def __init__(self) -> None:
        self.ops: list[bytes] = []
        self.y = ALTO - MARGEN

    def texto(self, t: str, *, fuente: str = "F1", tam: float = 10, x: float = MARGEN,
              color: bytes = b"0 0 0") -> None:
        self.ops.append(b"BT %s rg /%s %.1f Tf %.1f %.1f Td (%s) Tj ET"
                        % (color, fuente.encode(), tam, x, self.y, _cadena(t)))

    def bajar(self, puntos: float) -> None:
        self.y -= puntos

    def raya(self) -> None:
        self.ops.append(b"0.80 G 0.6 w %d %.1f m %d %.1f l S"
                        % (MARGEN, self.y, ANCHO - MARGEN, self.y))

    def franja(self) -> None:
        """La misma franja oficial del portal: azul con filete ámbar."""
        self.ops.append(b"%s rg 0 %d %d 40 re f" % (AZUL, ALTO - 40, ANCHO))
        self.ops.append(b"0.722 0.439 0.110 rg 0 %d %d 3 re f" % (ALTO - 43, ANCHO))
        self.y = ALTO - 26
        self.texto("Municipio de Panamá · Dirección de Permisos y Cumplimiento",
                   fuente="F2", tam=10, color=b"1 1 1")
        self.y = ALTO - 43 - 44

    def seccion(self, titulo: str) -> None:
        self.bajar(10)
        self.texto(titulo.upper(), fuente="F2", tam=9, color=AZUL)
        self.bajar(6)
        self.raya()
        self.bajar(16)

    def fila(self, etiqueta: str, valor: str, *, mono: bool = False) -> None:
        tam = 8 if mono else 10                      # en Courier 8 una huella de 64 cabe en una línea
        ancho = int((ANCHO - MARGEN - COL_VALOR) / (tam * (0.6 if mono else 0.5)))
        lineas = textwrap.wrap(valor, ancho) or ["—"]
        self.texto(etiqueta, fuente="F2", tam=9.5, color=b"0.30 0.34 0.38")
        for i, linea in enumerate(lineas):
            if i:
                self.bajar(13)
            self.texto(linea, fuente="F3" if mono else "F1", tam=tam, x=COL_VALOR)
        self.bajar(17)

    def parrafo(self, t: str, *, tam: float = 8.5) -> None:
        for linea in textwrap.wrap(t, int((ANCHO - 2 * MARGEN) / (tam * 0.5))):
            self.texto(linea, tam=tam, color=b"0.30 0.34 0.38")
            self.bajar(tam * 1.4)


def _documento(contenido: bytes, titulo: str) -> bytes:
    """Arma el archivo: catálogo, página, contenido, tres fuentes, xref y trailer."""
    fuente = (b"<< /Type /Font /Subtype /Type1 /BaseFont /%s "
              b"/Encoding /WinAnsiEncoding >>")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> >>" % (ANCHO, ALTO),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(contenido), contenido),
        fuente % b"Helvetica",
        fuente % b"Helvetica-Bold",
        fuente % b"Courier",
        b"<< /Title (%s) /Producer (Ventanilla Unica Municipal) >>" % _cadena(titulo),
    ]
    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = []
    for i, obj in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % p for p in posiciones)
    salida += (b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
               % (len(objetos) + 1, len(objetos), xref))
    return bytes(salida)


# ------------------------------------------------------------------ constancia

def generar(e: dict, titular: str, sello: dict | None) -> bytes:
    """
    e       el expediente, como lo entrega repositorio.expediente_a_dict
    titular nombre del solicitante
    sello   la entrada «expediente.creado» de la bitácora: n, ts, hash, previo
    """
    p = _Pagina()
    p.franja()
    p.texto("Constancia de solicitud", fuente="F2", tam=20)
    p.bajar(22)
    p.texto(e["codigo"], fuente="F3", tam=12, color=AZUL)
    p.bajar(18)
    p.texto(f"Recibida el {fecha_larga(e['creado'])} · Estado: {e['estado']}", tam=10,
            color=b"0.30 0.34 0.38")
    p.bajar(14)

    p.seccion("Solicitud")
    p.fila("Trámite", e["permiso"])
    p.fila("Titular", f"{titular} ({e['solicitante']})")
    p.fila("Responsable", f"{e['responsable']} · {e['telefono']}")
    p.fila("Tipo de acto", e["tipo_acto"])
    p.fila("Lugar", f"{e['lugar']}, {e['corregimiento']}")
    p.fila("Fecha del acto",
           f"{fecha_larga(e['fecha'])}, de {e['hora_inicio']} a {e['hora_fin']}")
    p.fila("Aforo", f"{e['aforo']:,} personas".replace(",", "."))
    p.fila("Plazo de respuesta", f"{e['plazo_dias']} días hábiles")
    p.fila("Etapa actual", e["etapa"])
    p.fila("Motivo", e["motivo"])

    p.seccion("Documento adjunto")
    p.fila("Huella SHA-256", e["documento_sha256"], mono=True)

    p.seccion("Sello de la bitácora de auditoría")
    if sello:
        hora = datetime.fromisoformat(sello["ts"]).strftime("%H:%M:%S")
        p.fila("Entrada", f"n.º {sello['n']} · {fecha_larga(sello['ts'])}, {hora} UTC")
        p.fila("Huella", sello["hash"], mono=True)
        p.fila("Huella anterior", sello["previo"], mono=True)
    else:
        p.fila("Entrada", "Sin sello registrado")

    p.bajar(8)
    p.parrafo("Esta constancia acredita que la solicitud fue recibida por la Ventanilla "
              "Única Municipal; no es el permiso. La huella del documento identifica el "
              "PDF entregado: cualquier cambio en el archivo produce otra huella. El sello "
              "de la bitácora encadena esta solicitud con las anteriores; su integridad se "
              "comprueba en /api/bitacora/verificar.")
    return _documento(b"\n".join(p.ops), f"Constancia {e['codigo']}")
