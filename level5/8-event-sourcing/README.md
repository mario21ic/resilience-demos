# Event sourcing

## Que es

En vez de guardar el estado **actual** de algo y mutarlo en el lugar
(`UPDATE cuenta SET saldo = saldo - 30`), event sourcing guarda la
secuencia completa de **eventos** que llevaron a ese estado
("Deposito de 100", "Deposito de 50", "Retiro de 30") en un log de
solo-agregar. El estado nunca es la fuente de verdad — es una
**proyeccion**: se calcula aplicando los eventos en orden, cada vez
que hace falta.

## Por que esto es resiliencia, no solo una eleccion de modelado

Si el estado derivado se corrompe — un bug, una migracion mal hecha,
alguien que lo pisa a mano — se puede tirar a la basura sin miedo:
alcanza con reproducir el log de eventos desde cero para reconstruirlo
exactamente igual. Lo unico que hay que proteger de verdad es el log
en si; el estado calculado es, por definicion, siempre recuperable
mientras el log este intacto.

## Un beneficio extra: multiples vistas del mismo log

Como el log tiene TODA la informacion (no solo el resultado final),
se pueden construir proyecciones nuevas mas adelante — un reporte, una
metrica, una vista para otro equipo — sin tocar como se registraron
los eventos originales. El diseño no necesito anticipar esa necesidad
de entrada: la informacion ya estaba ahi.

## El costo: reproducir un log grande es cada vez mas caro

La contrapartida es que reconstruir el estado desde el evento 0 se
vuelve mas lento a medida que el log crece. La solucion estandar son
los **snapshots**: guardar el estado proyectado en un punto dado, para
que una reconstruccion futura solo necesite reproducir los eventos
POSTERIORES a ese snapshot, no el historial completo.

## Estructura del ejemplo

- `event_sourcing.py`: `EventLog`, y tres proyecciones distintas sobre
  el mismo log (`project_balance`, `project_transaction_counts`,
  `project_total_deposits`).
- `demo_event_sourcing.py`: tres partes.
  1. El estado cacheado se corrompe; se reconstruye desde el log.
  2. Tres vistas distintas calculadas sobre el mismo log de eventos.
  3. Snapshots: velocidad de reproducir 500.000 eventos completos vs
     solo los ultimos 20.000 desde un snapshot — medido con tiempo
     real, no estimado.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_event_sourcing.py
```

Salida esperada (los tiempos exactos de la Parte 3 pueden variar):

```
Parte 1: saldo cacheado corrupto: -999999.0
         saldo reconstruido desde el log: 120.0

Parte 2: saldo actual: 215.0
         transacciones por tipo: {'Deposited': 3, 'Withdrawn': 2}
         total depositado historicamente: 285.0

Parte 3 (500.000 eventos):
  reproducir todo el log: 28.2ms
  reproducir solo desde el snapshot (evento 480.000): 1.2ms
  -> 23.1x mas rapido
```

## Puntos clave

- El log es append-only: nunca se edita ni se borra un evento — eso es
  lo que garantiza que siempre se pueda volver a un estado anterior o
  reconstruir uno corrompido con confianza.
- Un snapshot es una optimizacion de performance, no una fuente de
  verdad alternativa — si el snapshot mismo se corrompe, todavia se
  puede reconstruir desde el log completo (mas lento, pero posible).
- Esto es la misma idea que
  [checkpointing / durable execution](../5-checkpointing-durable-execution)
  aplicada a datos de negocio en vez de al estado de un workflow —
  ambos reconstruyen el presente reproduciendo un historial, en vez
  de confiar en un valor mutable guardado directamente.
- El costo real de event sourcing no es de performance (los snapshots
  lo resuelven) sino de diseño: requiere pensar el dominio en terminos
  de "que paso" en vez de "como esta ahora", y las proyecciones tienen
  que mantenerse consistentes con el significado real de cada evento
  a medida que el sistema evoluciona.
