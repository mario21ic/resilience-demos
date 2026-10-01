"""Demo: Runbooks y postmortems sin culpa.

Dos versiones del resumen de causa raiz para EL MISMO incidente: una
con lenguaje que atribuye culpa individual, otra reformulada en
terminos sistemicos. El chequeo mecanico detecta la diferencia.
"""
from blame_checker import check_for_blame_language

BLAMING_VERSION = (
    "El incidente ocurrio porque Marcos olvido actualizar el umbral del circuit "
    "breaker despues del ultimo refactor. Fue un error humano: deberia haber "
    "revisado la configuracion antes de mergear. La negligencia de no verificar "
    "el cambio en un ambiente de staging causo que el circuit breaker nunca "
    "abriera durante la degradacion real, dejando pasar trafico a un backend "
    "que fallaba el 80% de las veces."
)

BLAMELESS_VERSION = (
    "El incidente ocurrio porque el umbral del circuit breaker quedo "
    "desactualizado tras un refactor reciente. El proceso de revision de "
    "cambios en esta configuracion no incluia una validacion automatica contra "
    "los valores esperados, y el ambiente de staging no reproduce las "
    "condiciones de carga necesarias para detectar este tipo de discrepancia "
    "antes de produccion. Como resultado, el circuit breaker nunca abrio "
    "durante la degradacion real, dejando pasar trafico a un backend que "
    "fallaba el 80% de las veces."
)


def print_findings(label: str, text: str):
    print(f"{label}:")
    print(f'  "{text}"\n')
    findings = check_for_blame_language(text)
    if not findings:
        print("  sin lenguaje de culpa individual detectado.\n")
        return
    for f in findings:
        print(f"  encontrado: '{f['match']}'")
        print(f"    sugerencia: {f['suggestion']}")
    print()


def main():
    print_findings("Version CON lenguaje de culpa", BLAMING_VERSION)
    print_findings("Version SIN culpa (sistemica)", BLAMELESS_VERSION)

    print("Ambas versiones describen exactamente el MISMO incidente y llevan a la")
    print("MISMA correccion tecnica (agregar validacion automatica, mejorar staging).")
    print("La diferencia es si el equipo se queda con 'Marcos se equivoco' (que no")
    print("previene nada la proxima vez, con otra persona) o con 'el proceso permitia")
    print("que este tipo de error pasara desapercibido' (que si es accionable).")


if __name__ == "__main__":
    main()
