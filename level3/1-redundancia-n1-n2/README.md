# Redundancia N+1 / N+2 — activo-activo vs activo-pasivo

## Que es

Este es el primer ejemplo de **level3**, donde los patrones ya no se
tratan de una llamada ([level1](../../level1)) ni de proteger
capacidad compartida dentro de un proceso
([level2](../../level2)) — se tratan de como esta **fisicamente
organizada** la redundancia entre varias instancias/replicas de un
mismo servicio.

Hay dos preguntas independientes, y este ejemplo las separa a
proposito:

1. **¿Cuanta capacidad de sobra tengo?** — redundancia **N+1** / **N+2**.
2. **¿Como esta organizada esa capacidad de sobra?** — topologia
   **activo-activo** / **activo-pasivo**.

Son ejes ortogonales: se puede tener activo-activo con N+1 o con N+2,
y lo mismo para activo-pasivo. Este demo simula las cuatro
combinaciones contra la misma secuencia de fallas.

## N+1 vs N+2: cuanta capacidad de sobra

`N` es la cantidad de unidades que hacen falta para cubrir la demanda
normal. `N+1` agrega una unidad de mas: tolera **una** falla
simultanea sin perder capacidad. `N+2` agrega dos: tolera **dos**.

La palabra clave es *simultanea*. N+1 no es "puedo perder una
instancia en toda la vida del sistema" — es "puedo perder una
instancia a la vez sin degradarme". Si falla una segunda antes de que
la primera se recupere (una falla real mientras la otra sigue en
mantenimiento, por ejemplo), N+1 ya no alcanza.

## Activo-activo vs activo-pasivo: como se organiza esa capacidad

- **Activo-activo**: todas las instancias sirven trafico todo el
  tiempo, cada una por debajo de su 100% para dejar margen. Cuando
  una falla, las demas absorben su parte de inmediato — no hay tiempo
  de reaccion, solo una redistribucion de carga. El riesgo es
  puramente de **capacidad**: si las que quedan no alcanzan para la
  demanda total, se pierde exactamente el excedente.

- **Activo-pasivo**: una instancia sirve el 100% del trafico; el
  resto son *standbys* de guardia, sin servir nada, hasta que un
  **failover** (deteccion + promocion) los activa. Mientras el
  failover esta en curso, el servicio esta **caido del todo** — no
  hay degradacion parcial como en activo-activo, porque el standby
  todavia no esta sirviendo nada. El riesgo es de **tiempo**: cuanto
  tarda el failover en completarse.

## Estructura del ejemplo

- `topology.py`: `simulate_active_active` (capacidad total = suma de
  instancias sanas, perdida proporcional al excedente) y
  `simulate_active_passive` (capacidad binaria: 100% o 0%, con un
  `failover_delay` de caida total tras cada falla, y caida permanente
  si se agotan los spares).
- `demo_redundancia.py`: simula 2 fallas consecutivas (t=5 y t=15)
  sobre las 4 combinaciones y compara cuanto trafico se pierde en
  cada una.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_redundancia.py
```

Salida esperada (demanda constante = 300 req/tick, 25 ticks):

```
ACTIVO-ACTIVO
N+1 (4 instancias): t=15 dropped=100/300 (2da falla ya no alcanza)  -> total perdido: 1000
N+2 (5 instancias): nunca dropped                                   -> total perdido: 0

ACTIVO-PASIVO
N+1 (1 activo + 1 standby): 2da falla -> SIN spares, caida permanente -> total perdido: 4200
N+2 (1 activo + 2 standby): 2da falla -> failover de nuevo, se recupera -> total perdido: 2400
```

Cuatro resultados muy distintos para la misma secuencia de fallas:
activo-activo N+2 no pierde nada; activo-activo N+1 pierde solo el
excedente de la segunda falla (1000, concentrado en el tramo en que
la capacidad no alcanza); activo-pasivo N+2 pierde mucho mas (2400)
porque CADA failover implica una caida total de varios ticks;
activo-pasivo N+1 pierde el doble que N+2 (4200) porque la segunda
falla lo deja **caido para siempre**, sin mas spares para promover.

## Puntos clave

- Activo-activo con suficiente margen (N+2, N+3...) es la opcion mas
  resiliente ante fallas simultaneas, porque nunca hay una ventana de
  caida total — pero cuesta correr TODAS las instancias con carga
  real todo el tiempo, y requiere que el balanceador pueda redistribuir
  trafico al instante.
- Activo-pasivo es mas simple de razonar (siempre hay un "dueño" claro
  del trafico) y suele costar menos si los standbys pueden ser mas
  baratos, pero cada failover cuesta una ventana de caida total —
  ese costo no desaparece nunca, ni siquiera con N+3.
- N+1 vs N+2 no es una eleccion universal: depende de cuan probable es
  una segunda falla simultanea (¿instancias correlacionadas en el
  mismo rack, misma zona de disponibilidad?) y cuanto tiempo se tarda
  en reemplazar una instancia caida — cuanto mas lento el reemplazo,
  mas vale la pena N+2.
- Estos numeros son la base para dimensionar SLOs realistas: "toleramos
  una falla sin degradacion" es una promesa de N+1; prometer eso con
  activo-pasivo requiere ademas comprometerse con un failover-delay
  maximo, que es otro numero que hay que medir y no asumir.
