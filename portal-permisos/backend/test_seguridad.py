"""Pruebas de seguridad.py: contraseñas, tokens y clave de cifrado."""

import pytest
from cryptography.fernet import Fernet

import seguridad


def test_la_clave_se_verifica_y_una_equivocada_no():
    guardada = seguridad.cifrar_clave("clave-de-prueba")
    assert seguridad.verificar_clave("clave-de-prueba", guardada)
    assert not seguridad.verificar_clave("otra-clave", guardada)


def test_la_clave_guardada_lleva_algoritmo_iteraciones_y_sal_propia():
    a = seguridad.cifrar_clave("igual")
    b = seguridad.cifrar_clave("igual")
    assert a.startswith(f"pbkdf2_sha256${seguridad.ITERACIONES}$")
    assert a != b                                    # sal distinta en cada cuenta
    assert "igual" not in a


@pytest.mark.parametrize("guardada", ["", "texto-plano", "md5$1$a$b", "pbkdf2_sha256$x$a$b"])
def test_una_clave_guardada_malformada_no_da_acceso(guardada):
    assert seguridad.verificar_clave("lo-que-sea", guardada) is False


def test_el_token_no_se_parece_a_su_huella():
    token, huella = seguridad.nuevo_token()
    assert len(huella) == 64 and token not in huella
    assert seguridad.huella_token(token) == huella


def test_el_cifrado_de_columnas_ida_y_vuelta():
    columna = seguridad.Cifrado()
    cifrado = columna.process_bind_param("8-912-345", None)
    assert cifrado != "8-912-345" and "912" not in cifrado
    assert columna.process_result_value(cifrado, None) == "8-912-345"
    assert columna.process_bind_param(None, None) is None


def test_sin_clave_de_cifrado_no_se_arranca(monkeypatch):
    monkeypatch.delenv("CLAVE_CIFRADO", raising=False)
    monkeypatch.delenv("CLAVE_CIFRADO_FILE", raising=False)
    seguridad._fernet.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="CLAVE_CIFRADO"):
            seguridad.comprobar_clave()
    finally:
        monkeypatch.undo()
        seguridad._fernet.cache_clear()


def test_la_clave_de_cifrado_se_puede_leer_de_un_archivo(tmp_path, monkeypatch):
    archivo = tmp_path / "clave.txt"
    archivo.write_text(Fernet.generate_key().decode() + "\n", encoding="utf-8")
    monkeypatch.setenv("CLAVE_CIFRADO_FILE", str(archivo))
    seguridad._fernet.cache_clear()
    try:
        seguridad.comprobar_clave()
    finally:
        monkeypatch.undo()
        seguridad._fernet.cache_clear()
