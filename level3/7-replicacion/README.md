# Replicación — síncrona, asíncrona, por quórum; leader-follower vs multi-leader

## Que es

Replicar es mantener varias copias del mismo dato. Este ejemplo cubre
tres decisiones independientes que hay que tomar al diseñar cualquier
sistema replicado:

1. **¿Cuando confirmarle al cliente que un write tuvo exito?** —
   sincrona vs asincrona.
2. **¿Cuantas replicas tienen que confirmar, y cuantas hay que leer,
   para tener garantias?** — quorum.
3. **¿Cuantos lugares pueden aceptar escrituras?** — leader-follower
   (uno) vs multi-leader (varios).

## 1) Sincrona vs asincrona: latencia contra durabilidad

- **Sincrona**: el leader espera a que los followers confirmen antes
  de avisarle al cliente. Mas lenta, pero un write confirmado
  **nunca** puede perderse: si el leader se cae, el dato ya esta en
  al menos un follower.
- **Asincrona**: el leader confirma de inmediato y replica en
  paralelo. Mas rapida, pero si el leader se cae antes de terminar de
  replicar, un write que el cliente cree exitoso puede **desaparecer
  por completo** — nadie mas lo tenia.

Esto es la misma logica de [failover](../2-failover) aplicada a
datos en vez de a disponibilidad: la asincronia gana velocidad
regalando una ventana de riesgo.

## 2) Quorum: ni "todos" ni "solo uno"

En vez de exigir que TODAS las replicas confirmen (sincrona pura) o
solo el leader (asincrona pura), un sistema de quorum define: un
write se confirma cuando **W** de **N** replicas lo tienen, y una
lectura consulta **R** replicas.

La garantia clave: si **W + R > N**, cualquier quorum de lectura
**tiene que** superponerse con cualquier quorum de escritura — es
matematicamente imposible elegir R replicas de las N sin tocar al
menos una de las W que ya tienen el ultimo dato. Con W+R ≤ N, esa
garantia desaparece, y la probabilidad de leer un valor viejo se
puede calcular exactamente (o medir empiricamente, como hace este
demo).

## 3) Leader-follower vs multi-leader: uno o varios lugares para escribir

- **Leader-follower**: todo write pasa por un unico leader, que le
  asigna un orden real segun cuando lo recibio. No hay ambiguedad
  posible sobre "cual es el ultimo valor" — pero escribir desde lejos
  siempre implica ir hasta ese unico leader, y si es inalcanzable,
  nadie puede escribir en ningun lado.
- **Multi-leader**: cada region tiene su propio leader, que acepta
  escrituras locales de inmediato (mejor latencia, sigue funcionando
  aunque otras regiones esten inalcanzables) y replica de forma
  asincronica. El costo: escrituras concurrentes a la misma clave en
  dos regiones distintas son un **conflicto real** que hay que
  resolver — normalmente con "last write wins" (LWW) por timestamp.

El problema de LWW es que depende de que los relojes de las distintas
regiones esten sincronizados entre si. Si no lo estan (y en la
practica, nunca lo estan perfectamente), LWW puede **invertir el
orden real**: un write que en el mundo real paso DESPUES pierde
contra uno anterior, solo porque el reloj de su region estaba
atrasado.

## Estructura del ejemplo

- `replication.py`: `simulate_writes` (Parte 1),
  `probability_no_overlap` + `empirical_stale_read_rate` (Parte 2),
  `LeaderFollowerCluster` + `MultiLeaderCluster` (Parte 3).
- `demo_replicacion.py`: las tres comparaciones descriptas arriba.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_replicacion.py
```

Salida esperada (resumen):

```
Parte 1: ASINCRONA pierde los writes [5, 6, 7] (confirmados, nunca replicados)
         SINCRONA nunca pierde nada, pero deja [5,6,7,8,9] sin confirmar antes del crash

Parte 2 (N=5 replicas):
  W=3 R=3 (W+R=6>N): 0% de lecturas viejas — garantizado matematicamente
  W=2 R=2 (W+R=4<=N): ~30% de lecturas viejas
  W=1 R=1 (W+R=2<=N): ~80% de lecturas viejas

Parte 3: LWW elige a EU (timestamp 100.0) sobre US (timestamp 99.0, reloj
         atrasado) — pero en el mundo real, US escribio DESPUES.
```

## Puntos clave

- No hay una opcion "correcta" universal: sincrona/quorum
  alto/leader-follower priorizan correctitud sobre latencia;
  asincrona/quorum bajo/multi-leader priorizan latencia y
  disponibilidad sobre la garantia de no perder ni un solo write.
- El quorum es la herramienta para no tener que elegir entre los dos
  extremos: se puede ajustar W y R por sistema (o incluso por
  operacion) segun cuanto importe la consistencia de ESA lectura en
  particular.
- LWW no es "incorrecto" — es una eleccion de diseño consciente que
  cambia perder datos ocasionalmente por evitar coordinacion costosa
  entre regiones. El problema es cuando se usa sin entender que
  depende de sincronizacion de relojes, que nunca es perfecta.
- Multi-leader con LWW resuelve el MISMO tipo de ambiguedad que el
  [fencing](../2-failover) resuelve en split-brain — la diferencia es
  que en split-brain la ambiguedad es un BUG (dos nodos que no
  deberian ser ambos primarios), mientras que en multi-leader es una
  caracteristica de diseño aceptada a cambio de latencia y
  disponibilidad por region.
