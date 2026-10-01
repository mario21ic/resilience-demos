"""DR (Disaster Recovery) con RTO/RPO explicitos.

  - RTO (Recovery Time Objective): cuanto tiempo puede estar el
    sistema caido antes de que este de vuelta.
  - RPO (Recovery Point Objective): cuantos datos se pueden dar el
    lujo de perder, medido en tiempo (desde el ultimo backup o la
    ultima replicacion exitosa).

Cuatro estrategias, de mas barata y lenta a mas cara y rapida:

  - Backup & restore: solo backups periodicos, nada corriendo en el
    sitio de DR. RTO de horas o dias (hay que provisionar todo desde
    cero Y restaurar los datos); RPO igual al intervalo entre backups.
  - Pilot light: el nucleo minimo (tipicamente solo la base de datos,
    replicando) esta siempre corriendo en el sitio de DR; el resto se
    "enciende" durante el desastre. RPO chico (los datos ya estan
    replicando); RTO de decenas de minutos (hay que escalar el resto).
  - Warm standby: una copia completa pero reducida del ambiente
    corriendo todo el tiempo en el sitio de DR. RTO de minutos (solo
    hay que escalar capacidad y redirigir trafico).
  - Hot standby / activo-activo: una copia a escala completa, ya
    recibiendo trafico real o lista para recibirlo al instante. RTO
    casi cero (un cambio de ruteo); RPO casi cero (replicacion
    sincrona o casi). El mismo concepto de
    [static stability](../../level3/10-multi-az), aplicado entre
    regiones en vez de entre zonas de disponibilidad.
"""

DR_STRATEGIES = [
    {"name": "backup & restore", "rto": "horas a dias", "rpo": "horas (desde el ultimo backup)", "costo_relativo": "1x"},
    {"name": "pilot light", "rto": "decenas de minutos", "rpo": "minutos", "costo_relativo": "2-3x"},
    {"name": "warm standby", "rto": "minutos", "rpo": "segundos a minutos", "costo_relativo": "5-10x"},
    {"name": "hot standby / activo-activo", "rto": "segundos", "rpo": "casi cero", "costo_relativo": "~2x (capacidad duplicada)"},
]


def probability_recovery_never_tested(p_bug: float) -> float:
    """Si nunca se probo un restore real, un bug presente en el
    proceso de backup (con probabilidad `p_bug`) sigue sin descubrir
    hasta el desastre real -- momento en el que ya es demasiado
    tarde para arreglarlo."""
    return 1 - p_bug


def probability_recovery_tested(p_bug: float, n_tests_before_disaster: int, detection_prob_per_test: float = 0.9) -> float:
    """Cada restore de prueba tiene una buena probabilidad de detectar
    el bug SI existe. Con suficientes pruebas antes del desastre real,
    la probabilidad de que el bug siga sin descubrir (y por lo tanto
    sin arreglar) cae rapidamente."""
    prob_bug_still_undetected = (1 - detection_prob_per_test) ** n_tests_before_disaster
    prob_still_broken_at_disaster_time = p_bug * prob_bug_still_undetected
    return 1 - prob_still_broken_at_disaster_time
