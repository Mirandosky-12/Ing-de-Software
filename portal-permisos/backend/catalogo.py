"""
catalogo.py — Los 35 trámites de la Dirección de Permisos y Cumplimiento.

Fuente: https://permisosycumplimiento.mupa.gob.pa/tramites-y-permisos/
Es la misma lista que CATALOGO en index.html; migrar.py la carga en la tabla
`permisos`. Si cambia un trámite, se cambia aquí y se vuelve a correr migrar.py.
"""

DOCS = {
    "nota":   "Nota de solicitud dirigida al Alcalde de Panamá",
    "ced":    "Copia de cédula o pasaporte del solicitante",
    "aviso":  "Aviso de Operación vigente",
    "paz":    "Paz y Salvo Municipal",
    "rp":     "Certificado del Registro Público (personas jurídicas)",
    "poliza": "Póliza de responsabilidad civil",
    "bomb":   "Visto bueno del Cuerpo de Bomberos de Panamá",
    "plano":  "Plano de ubicación o croquis del sitio",
    "idoneo": "Idoneidad del personal técnico responsable",
    "minsa":  "Registro sanitario del MINSA",
    "ficha":  "Ficha técnica de los productos a utilizar",
    "ipf":    "Informe Previo Favorable vigente",
    "ruta":   "Ruta y horario detallado del recorrido",
    "veh":    "Registro vehicular y revisado vigente",
    "seg":    "Plan de seguridad y evacuación",
    "ambos":  "Nota de no objeción del corregimiento",
}


def _r(*claves: str) -> list[str]:
    """Traduce claves de DOCS a texto; lo que no es clave se deja tal cual."""
    return [DOCS.get(c, c) for c in claves]


ESP = "Espectáculos y eventos públicos"
PUB = "Publicidad y uso de espacio público"
SON = "Sonido y unidades móviles"
NOC = "Permisos nocturnos"
TAL = "Talleres"
SAL = "Salud y saneamiento ambiental"
COM = "Comercio y actividades especiales"
INF = "Informes previos"

# (id, nombre, categoría, días hábiles, aforo (mín, máx) o None, requisitos)
PERMISOS = [
    ("ESP-500-", "Espectáculo Público — menos de 500 personas", ESP, 15, (1, 499),
     _r("nota", "ced", "aviso", "paz", "poliza", "bomb")),
    ("ESP-4000", "Espectáculo Público — menos de 4,000 personas", ESP, 20, (500, 3999),
     _r("nota", "ced", "aviso", "paz", "poliza", "bomb", "seg", "plano")),
    ("ESP-500+", "Espectáculo Público — más de 500 personas", ESP, 25, (500, 60000),
     _r("nota", "ced", "aviso", "paz", "poliza", "bomb", "seg", "plano", "rp")),
    ("FEST", "Festividad", ESP, 15, None,
     _r("nota", "ced", "ambos", "poliza", "bomb")),
    ("BANDAS", "Práctica de Bandas Independientes", ESP, 10, None,
     _r("nota", "ced", "ambos", "ruta")),
    ("PASEO", "Paseo o Excursiones", ESP, 10, None,
     _r("nota", "ced", "ruta", "veh", "poliza")),
    ("CHIVA", "Chiva Parrandera", ESP, 15, None,
     _r("nota", "ced", "veh", "poliza", "ruta", "aviso")),
    ("INVIT", "Invitación de la Alcaldía de Panamá", ESP, 8, None,
     _r("nota", "ced")),

    ("PUB-TEMP", "Instalación de Publicidad Eventual o Temporal", PUB, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano", "ipf")),
    ("BANDEROLA", "Instalación de Banderolas Móviles", PUB, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano")),
    ("ESP-EST", "Uso de Espacio Público para Estacionamiento", PUB, 15, None,
     _r("nota", "ced", "aviso", "paz", "plano", "poliza")),
    ("ACERA", "Uso Temporal de Aceras", PUB, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano")),
    ("CASCO", "Uso Temporal de Espacio Público — Casco Antiguo", PUB, 20, None,
     _r("nota", "ced", "aviso", "paz", "plano", "poliza",
        "Visto bueno de la Oficina del Casco Antiguo")),

    ("SON-TEMP", "Servicio de Unidad Móvil de Sonido u Audio — Temporal", SON, 10, None,
     _r("nota", "ced", "veh", "ruta")),
    ("SON-PERM", "Servicio de Unidad Móvil de Sonido u Audio", SON, 15, None,
     _r("nota", "ced", "aviso", "paz", "veh", "ruta")),

    ("NOC-A", "Permiso Nocturno Categoría A", NOC, 25, None,
     _r("nota", "ced", "aviso", "paz", "rp", "bomb", "ipf", "plano")),
    ("NOC-A-REN", "Renovación de Permiso Nocturno Categoría A", NOC, 15, None,
     _r("nota", "ced", "paz", "Permiso nocturno del período anterior", "bomb")),
    ("NOC-B", "Permiso Nocturno Categoría B", NOC, 20, None,
     _r("nota", "ced", "aviso", "paz", "bomb", "ipf")),
    ("NOC-C", "Permiso Nocturno Categoría C", NOC, 20, None,
     _r("nota", "ced", "aviso", "paz", "bomb", "ipf")),
    ("NOC-D", "Permiso Nocturno Categoría D", NOC, 20, None,
     _r("nota", "ced", "aviso", "paz", "bomb", "ipf")),

    ("TAL-INST", "Instalación y Operación de Taller", TAL, 25, None,
     _r("nota", "ced", "aviso", "paz", "ipf", "plano", "bomb")),
    ("TAL-HOR", "Extensión de Horario para Taller", TAL, 12, None,
     _r("nota", "ced", "aviso", "paz", "Permiso de operación del taller")),
    ("TAL-MOV", "Operación de Taller Móvil", TAL, 15, None,
     _r("nota", "ced", "aviso", "veh", "idoneo")),
    ("TAL-COMB", "Taller — Extensión de Horario y Taller Móvil", TAL, 18, None,
     _r("nota", "ced", "aviso", "paz", "veh", "idoneo")),

    ("DESINF", "Permiso de Desinfección", SAL, 15, None,
     _r("nota", "ced", "aviso", "minsa", "idoneo", "ficha")),
    ("DESINF-A", "Actualización de Desinfección", SAL, 10, None,
     _r("nota", "ced", "minsa", "ficha")),
    ("GICP", "Gestión Integral de Control de Plagas", SAL, 20, None,
     _r("nota", "ced", "aviso", "minsa", "idoneo", "ficha", "paz")),
    ("GICP-REN", "Renovación de Gestión Integral de Control de Plagas", SAL, 12, None,
     _r("nota", "ced", "paz", "minsa", "Permiso GICP del período anterior")),
    ("GICP-ACT", "Actualización de Gestión Integral de Control de Plagas", SAL, 10, None,
     _r("nota", "ced", "minsa", "ficha", "idoneo")),

    ("GANADO", "Guía de Traslado de Ganado", COM, 5, None,
     _r("nota", "ced", "Certificado de salud animal del MIDA", "veh", "ruta")),
    ("GRUAS", "Inscripción de Grúas y Almacenamiento", COM, 20, None,
     _r("nota", "ced", "aviso", "paz", "rp", "veh", "poliza")),
    ("NAVIDAD", "Venta de Árboles de Navidad", COM, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano", "Permiso fitosanitario del MIDA")),
    ("FERRETE", "Ferrete", COM, 8, None,
     _r("nota", "ced", "aviso", "paz")),

    ("IPF", "Informe Previo Favorable", INF, 20, None,
     _r("nota", "ced", "rp", "plano", "Certificación de uso de suelo", "bomb")),
    ("IPF-ACT", "Actualización de Informe Previo Favorable", INF, 12, None,
     _r("nota", "ced", "ipf", "plano")),
]
