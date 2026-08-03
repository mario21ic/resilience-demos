"""Sharding simple vs shuffle sharding.

Sharding: repartir tenants/clientes entre varios shards (bases de
datos, colas, workers) para escalar horizontalmente. El problema del
sharding simple (un tenant -> un shard) es el "blast radius": si un
tenant toxico (uno que manda trafico patologico, o simplemente tiene
mala suerte) degrada SU shard, TODOS los demas tenants que comparten
ese mismo shard se ven afectados con el.

Shuffle sharding (tecnica de AWS, ver "Shuffle Sharding: massive and
magical fault isolation") asigna a cada tenant una COMBINACION de K
shards de un pool de N, en vez de uno solo. La clave es combinatoria:
aunque N sea chico, la cantidad de combinaciones distintas de tamano K
(`C(N, K)`) crece muy rapido — con pocos shards fisicos se consiguen
miles de "carriles" virtuales practicamente aislados entre si. Un
tenant toxico que degrada SUS K shards solo afecta por completo a los
tenants que comparten exactamente esa misma combinacion — una fraccion
mucho mas chica que "todos los que comparten un shard".
"""
import math
import random


def assign_single_shard(n_tenants: int, n_shards: int, rng: random.Random) -> list:
    """Sharding simple: cada tenant a UN shard."""
    return [rng.randrange(n_shards) for _ in range(n_tenants)]


def assign_shuffle_shards(n_tenants: int, n_shards: int, k: int, rng: random.Random) -> list:
    """Shuffle sharding: cada tenant a una combinacion de K shards
    distintos, elegida (pseudo)al azar. En un sistema real esto sale
    de un hash determinista del ID del tenant, no de un rng
    compartido — lo importante para este demo es la DISTRIBUCION
    resultante, no la determinacion por tenant.
    """
    return [tuple(sorted(rng.sample(range(n_shards), k))) for _ in range(n_tenants)]


def blast_radius(combos: list, toxic_shards: set) -> dict:
    """Clasifica cada combinacion segun cuanto se superpone con los
    shards toxicos: totalmente adentro (afectado del todo), parcial
    (comparte alguno pero no todos), o ninguno (no afectado).
    """
    full, partial, none_ = 0, 0, 0
    for combo in combos:
        overlap = len(set(combo) & toxic_shards)
        if overlap == len(combo):
            full += 1
        elif overlap > 0:
            partial += 1
        else:
            none_ += 1
    return {"full": full, "partial": partial, "none": none_}


def theoretical_full_overlap_probability(n_shards: int, k: int, n_toxic: int) -> float:
    """Probabilidad de que la combinacion de un tenant caiga
    COMPLETAMENTE dentro del conjunto de `n_toxic` shards toxicos
    (para el caso de este demo, n_toxic == k: la combinacion del
    propio tenant toxico).
    """
    if k > n_toxic:
        return 0.0
    return math.comb(n_toxic, k) / math.comb(n_shards, k)


def succeeds_with_retry(combo, toxic_shards: set) -> bool:
    """Si CUALQUIERA de los shards asignados al tenant esta sano, un
    cliente que reintenta entre los shards de su propia combinacion
    (ver level1/2-retry) termina teniendo exito.
    """
    return any(shard not in toxic_shards for shard in combo)
