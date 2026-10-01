"""Un postmortem SIN CULPA busca la causa SISTEMICA de un incidente
(que permitio que un error individual tuviera impacto), no a quien
"cometio" el error. La razon no es cortesia: si la gente teme ser
señalada, deja de contar la version completa de lo que paso — y sin
esa honestidad, el mismo modo de falla vuelve a ocurrir, porque nadie
llego a entenderlo del todo.

Este modulo no reemplaza el criterio humano — es un chequeo mecanico
simple que detecta lenguaje que tipicamente señala culpa individual en
vez de causas sistemicas, para poder revisarlo antes de publicar un
postmortem.
"""
import re

BLAME_PATTERNS = [
    (r"\berror humano\b", "en vez de 'error humano', describir que en el PROCESO permitio que ese error tuviera impacto"),
    (r"\bfalla humana\b", "en vez de 'falla humana', describir la condicion del sistema que hizo posible el error"),
    (r"\bnegligencia\b", "evitar 'negligencia' -- describir la accion concreta y el contexto en el que se tomo"),
    (r"\bculpa de\b", "evitar atribuir 'culpa' a una persona -- describir la causa sistemica"),
    (r"\bdeber[ií]a haber (sabido|revisado|verificado|notado)\b",
     "evitar 'deberia haber sabido/revisado' -- en el momento, con la informacion disponible, la decision pudo parecer razonable"),
    (r"\b(olvid[oó]|no revis[oó]|no verific[oó])\b",
     "evitar atribuir el fallo a que alguien 'olvido' o 'no reviso' -- preguntar por que el sistema permitio que ese paso se saltee sin que nadie lo notara"),
    (r"\bdescuido\b", "evitar 'descuido' -- describir que hizo que ese paso fuera facil de pasar por alto"),
]


def check_for_blame_language(text: str) -> list:
    """Devuelve una lista de coincidencias de lenguaje que atribuye
    culpa individual, cada una con una sugerencia de reformulacion
    sistemica."""
    findings = []
    for pattern, suggestion in BLAME_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({"match": match.group(0), "position": match.start(), "suggestion": suggestion})
    return sorted(findings, key=lambda f: f["position"])
