# Level 8 — Verificación y operación

Todos los niveles anteriores construyen mecanismos de resiliencia:
timeouts, retries, circuit breakers, redundancia, sagas, consenso,
autoscaling. Este nivel final responde una pregunta distinta: ¿como se
sabe si esos mecanismos realmente funcionan, y como se opera un
sistema cuando, a pesar de todo, algo falla igual?

Las preguntas de este nivel:

- ¿Como se prueba que un mecanismo de recuperacion funciona, en vez de
  asumirlo porque "esta implementado"?
- ¿Cuanto riesgo (downtime, errores) es aceptable, y como se mide
  cuando ese presupuesto se esta agotando?
- ¿Que metricas realmente indican si un sistema esta sano, y por que
  los promedios mienten?
- ¿Que tan rapido puede recuperarse un sistema de perder su sitio
  primario entero, y cuantos datos puede permitirse perder?
- ¿Como se prepara un equipo para operar bajo presion durante un
  incidente, y como se aprende de el sin repetirlo?

Todos los ejemplos son autocontenidos y usan solo la libreria estandar
de Python (no requieren `pip install`).

## Como se relacionan entre si

```
chaos engineering        -> provocar fallas a proposito, de forma controlada,
                             para verificar que la resiliencia es real
slo / error budgets      -> cuanto riesgo es aceptable, y cuando frenar
observabilidad           -> que medir para saber si el sistema esta sano
dr (rto/rpo)             -> que tan rapido y con cuanta perdida de datos se
                             recupera el sistema de perder el sitio primario
runbooks / postmortems   -> como operar bajo presion, y como aprender de
                             lo que igual salio mal
```

Los primeros cuatro son formas de **verificar** la resiliencia: chaos
engineering la ejercita de forma proactiva, los error budgets ponen un
numero al riesgo tolerado, la observabilidad da la señal para saber si
algo anda mal, y el DR mide la peor perdida posible. El ultimo,
runbooks y postmortems, es la disciplina **humana** que conecta todo
lo anterior: que hacer cuando la verificacion revela un problema en
vivo, y como convertir cada incidente real en una mejora concreta al
sistema.

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-chaos-engineering](1-chaos-engineering) | Provocar fallas a proposito, con hipotesis previa y radio de impacto acotado, para verificar la resiliencia en vez de asumirla. |
| 2 | [2-slo-error-budgets](2-slo-error-budgets) | Convertir un SLO en un presupuesto de error concreto, y usar la tasa de consumo (burn rate) para saber cuando actuar. |
| 3 | [3-observabilidad-red-use-traces](3-observabilidad-red-use-traces) | Metricas RED vs USE, y por que un promedio puede ocultar una degradacion severa que un percentil revela. |
| 4 | [4-dr-rto-rpo](4-dr-rto-rpo) | Las cuatro estrategias de disaster recovery y su tradeoff de costo vs velocidad de recuperacion vs datos perdidos; por que hay que probar el restore, no solo tener backups. |
| 5 | [5-runbooks-postmortems](5-runbooks-postmortems) | Runbooks que guian el diagnostico bajo presion, y postmortems sin culpa que convierten un incidente en acciones sistemicas en vez de señalar a una persona. |

## Orden de lectura sugerido

`1 -> 2 -> 3 -> 4 -> 5`.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
