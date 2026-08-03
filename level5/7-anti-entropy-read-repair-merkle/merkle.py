"""Merkle trees: lo que hace posible que la anti-entropy (comparar dos
replicas completas para encontrar y reparar divergencias) escale a
millones de claves sin transferir ni comparar todos los datos.

Cada hoja del arbol es el hash de un "bucket" (un rango de claves). Cada
nodo interno es el hash de sus hijos, hasta llegar a una unica raiz.
Comparar dos replicas empieza por comparar solo sus raices: si
coinciden, son identicas (con altisima probabilidad) y no hace falta
mirar nada mas. Si difieren, se baja recursivamente SOLO por las ramas
cuyos hashes no coinciden, hasta aislar los buckets exactos que
divergen — el resto del arbol nunca se toca.
"""
import hashlib


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_buckets(keys: list, replica: dict, n_buckets: int) -> list:
    bucket_size = max(1, len(keys) // n_buckets)
    return [
        [(k, replica[k]) for k in keys[i:i + bucket_size]]
        for i in range(0, len(keys), bucket_size)
    ]


def build_merkle_tree(buckets: list) -> list:
    """Devuelve los niveles del arbol, de las hojas (`levels[0]`) a la
    raiz (`levels[-1][0]`)."""
    leaves = [_hash("|".join(f"{k}={v}" for k, v in bucket).encode()) for bucket in buckets]
    levels = [leaves]
    current = leaves
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else current[i]
            next_level.append(_hash((left + right).encode()))
        levels.append(next_level)
        current = next_level
    return levels


def find_diverging_buckets(tree_a: list, tree_b: list):
    """Baja por el arbol desde la raiz, comparando hashes, y solo
    desciende por las ramas que no coinciden. Devuelve (indices de
    buckets candidatos a divergir, cantidad de comparaciones de hash
    realizadas).
    """
    n_levels = len(tree_a)
    comparisons = 0
    current_indices = [0]

    for level in range(n_levels - 1, 0, -1):
        next_indices = []
        for idx in current_indices:
            comparisons += 1
            if tree_a[level][idx] != tree_b[level][idx]:
                left = idx * 2
                right = left + 1
                next_indices.append(left)
                if right < len(tree_a[level - 1]):
                    next_indices.append(right)
        current_indices = next_indices
        if not current_indices:
            break

    return current_indices, comparisons
