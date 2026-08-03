# Sharding / partitioning — shuffle sharding

## Que es

**Sharding** es repartir tenants/clientes entre varios shards (bases
de datos, colas, workers) para escalar horizontalmente. El problema
del sharding simple — un tenant, un shard — es el **blast radius**:
si un tenant toxico (trafico patologico, una consulta cara, un bug
que satura recursos) degrada su shard, **todos** los demas tenants
que comparten ese mismo shard caen con el, sin haber hecho nada malo.

**Shuffle sharding** (tecnica de AWS, descripta en su post "Shuffle
Sharding: massive and magical fault isolation") ataca esto sin
agregar mas shards fisicos: en vez de asignarle a cada tenant UN
shard, le asigna una **combinacion** de K shards de un pool de N.

## La idea combinatoria

La clave es que la cantidad de combinaciones distintas de tamaño K
entre N shards (`C(N, K)`) crece mucho mas rapido que N. Con solo 8
shards fisicos y combinaciones de 2, ya hay 28 combinaciones posibles;
con 32 shards y combinaciones de 4, casi 36 mil. Cada tenant queda en
un "carril" que comparte, como mucho, una fraccion de sus shards con
cualquier otro tenant — la mayoria no comparte NINGUNO.

Cuando un tenant toxico degrada sus propios K shards, solo los
tenants cuya combinacion es **exactamente igual** a la suya quedan
100% afectados. Los que comparten solo ALGUNOS de esos shards pueden
seguir funcionando via el resto de su propia combinacion — y ahi es
donde el [retry](../../level1/2-retry) cierra el circulo.

## Estructura del ejemplo

- `sharding.py`: `assign_single_shard` / `assign_shuffle_shards`
  (como se reparten los tenants), `blast_radius` (clasifica el
  impacto de una falla), `theoretical_full_overlap_probability`
  (la matematica exacta), `succeeds_with_retry` (el cierre con retry).
- `demo_sharding.py`: cuatro partes.
  1. Sharding simple: cuantifica el blast radius de un shard toxico.
  2. Shuffle sharding: la misma situacion, con combinaciones de
     shards — se mide (y se verifica contra la formula exacta)
     cuanto se reduce el blast radius.
  3. Por que funciona con pocos shards fisicos: la tabla de `C(N, K)`.
  4. El cierre con retry: reintentar contra el resto de la propia
     combinacion recupera a casi todos los "parcialmente afectados".

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_sharding.py
```

Salida esperada (10.000 tenants, 8 shards):

```
Parte 1 (sharding simple): 1257/10000 (12.6%) tenants 100% afectados por 1 shard toxico

Parte 2 (shuffle sharding, K=2 de 8):
  100% afectados (combinacion exacta):  364/10000 (3.6%)
  parcialmente afectados (comparten 1): 4312/10000 (43.1%)
  no afectados:                         5324/10000 (53.2%)

Parte 4 (con retry al resto de la propia combinacion):
  sin retry: 7474/10000 exitosos (74.7%)
  con retry: 9636/10000 exitosos (96.4%)
```

El blast radius total cae de ~12.6% a ~3.6% — sin agregar un solo
shard fisico nuevo, solo cambiando la politica de asignacion — y con
retry, el 96.4% de los tenants nunca nota que hubo un problema.

## Puntos clave

- Shuffle sharding no elimina el blast radius — lo reduce
  drasticamente y lo vuelve **cuantificable**: `C(n_toxico, K) / C(N, K)`
  es la formula exacta de cuantos tenants quedan 100% expuestos.
- El beneficio depende de que el sistema efectivamente intente el
  RESTO de la combinacion de un tenant cuando uno de sus shards falla
  — sin eso, shuffle sharding solo mueve el problema (Parte 4: 74.7%
  vs 96.4% es la diferencia entre tener la propiedad y aprovecharla).
- Cuantos mas shards por tenant (K mayor), mas diluido queda el
  blast radius de una combinacion exacta, pero tambien mas tenants
  quedan "parcialmente" tocados por cualquier falla — el retry es lo
  que hace que ese trade-off valga la pena.
- Esta tecnica es la misma logica que las claves "calientes" de
  [consistent hashing con bounded loads](../4-load-balancing): en vez
  de aceptar que un punto caliente sature un recurso fijo, se cambia
  la ASIGNACION para que el dano de cualquier punto problematico quede
  contenido a una fraccion pequeña y predecible del resto del sistema.
