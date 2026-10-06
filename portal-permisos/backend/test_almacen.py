"""Pruebas de almacen.py: dónde y cómo se guardan los PDF."""

import hashlib

import pytest

import almacen

PDF = b"%PDF-1.4\n%%EOF\n"
SHA = hashlib.sha256(PDF).hexdigest()


def test_el_pdf_se_guarda_con_el_nombre_de_su_huella():
    ruta = almacen.guardar(SHA, PDF)
    assert ruta == f"{SHA[:2]}/{SHA}.pdf"
    assert almacen.leer(ruta) == PDF


def test_guardar_dos_veces_no_deja_temporales_ni_duplicados():
    almacen.guardar(SHA, PDF)
    almacen.guardar(SHA, PDF)
    archivos = [p.name for p in (almacen.raiz() / SHA[:2]).iterdir()]
    assert archivos == [f"{SHA}.pdf"]


@pytest.mark.parametrize("huella", ["../../etc/passwd", "A" * 64, "a" * 63, "", "a" * 64 + "/x"])
def test_una_huella_inventada_no_puede_elegir_la_ruta(huella):
    with pytest.raises(ValueError):
        almacen.guardar(huella, PDF)
