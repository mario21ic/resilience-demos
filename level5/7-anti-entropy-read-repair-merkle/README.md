# Anti-entropy, read repair, Merkle trees

## Que es

Cuando hay varias replicas de un mismo dato (ver
[replicacion](../../level3/7-replicacion)), tarde o temprano divergen:
un write que no llego a todas, una replica que estuvo caida un rato.
Dynamo y sistemas inspirados en el (Cassandra, Riak) usan dos
mecanismos complementarios para reparar esa divergencia, sin depender
de que nunca pase (algo que, a escala, siempre termina pasando).

## Read repair: reparar al pasar

Cuando una lectura toca varias replicas (un quorum) y estas no
coinciden, la lectura misma puede detectar cual version es la mas
nueva, devolverla al cliente, **y de paso** corregir a la replica
atrasada. No hace falta un proceso separado para ESE dato puntual —
se repara como efecto secundario de que alguien lo pidio.

El limite de read repair es justamente ese: solo repara lo que se
**lee**. Un dato que nadie consulta puede quedar divergente para
siempre, sin que nada lo note.

## Anti-entropy: reparar lo que nadie lee

Para los datos "frios", hace falta un proceso de fondo que compare
replicas completas y arregle lo que encuentre distinto — la
**anti-entropy**. El problema es de escala: comparar dos replicas de
millones de claves, clave por clave, para encontrar un puñado de
diferencias, es carisimo.

## Merkle trees: comparar sin leer casi nada

Un arbol de Merkle resuelve ese problema de escala. Cada hoja es el
hash de un rango de claves ("bucket"); cada nodo interno es el hash de
sus hijos, hasta una unica raiz. Comparar dos replicas empieza
comparando **solo las raices**: si coinciden, son identicas (con
altisima probabilidad), fin de la comparacion. Si difieren, se baja
recursivamente solo por las ramas cuyos hashes no coinciden, hasta
aislar los buckets exactos que divergen — el resto del arbol nunca se
toca ni se transfiere.

## Estructura del ejemplo

- `replicas.py`: `Replica` y `quorum_read_with_repair` (Parte 1).
- `merkle.py`: `build_merkle_tree` y `find_diverging_buckets` (Parte 2)
  — el algoritmo de comparacion que solo desciende por las ramas que
  no coinciden.
- `demo_anti_entropy.py`: dos partes.
  1. Una lectura detecta y repara una replica atrasada.
  2. Comparar dos replicas de 1.000.000 de claves (con solo 5
     realmente divergentes) usando un arbol de Merkle vs un escaneo
     lineal completo.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_anti_entropy.py
```

Salida esperada:

```
Parte 1: C esta atrasada (version 1 vs 2). La lectura devuelve el valor
         correcto Y repara a C, todo en la misma operacion.

Parte 2 (1.000.000 de claves, 5 divergentes):
  trabajo total con Merkle: 9,833 comparaciones
  trabajo de un escaneo lineal completo: 1,000,000 comparaciones
  -> 102x menos trabajo para encontrar exactamente las mismas 5 claves.
```

## Puntos clave

- Read repair y anti-entropy no son alternativas — se complementan:
  read repair arregla lo caliente rapido y gratis; anti-entropy
  arregla lo frio, periodicamente, a un costo acotado gracias a
  Merkle trees.
- El tamaño del bucket es un tradeoff: buckets mas chicos aislan la
  divergencia con mas precision (menos comparaciones de clave al
  final) pero el arbol tiene mas niveles y nodos; buckets mas grandes
  son un arbol mas chico pero cada divergencia obliga a revisar mas
  claves de una.
- Esto es la misma logica que
  [reconciliation loops](../6-reconciliation-loops): en vez de tratar
  de que cada escritura sea perfecta, se acepta que va a haber
  divergencia y se invierte en encontrarla y corregirla de forma
  continua — la diferencia es que aca el "estado deseado" es "todas
  las replicas coinciden entre si", no un spec externo.
- Fuera de bases de datos, el mismo principio de Merkle trees es lo
  que usan `rsync`, Git y IPFS para sincronizar o comparar arboles de
  archivos sin transferir todo el contenido cada vez.
