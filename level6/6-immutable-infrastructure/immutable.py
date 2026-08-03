"""Infraestructura inmutable: en vez de modificar un servidor que ya
esta corriendo (entrar por SSH, aplicar un parche, cambiar una
config), se construye una imagen nueva con el cambio adentro y se
REEMPLAZA el servidor entero — nunca se muta uno que ya existe.

La alternativa (infraestructura mutable) acumula "configuration
drift": cada parche puntual, aplicado a mano y a veces solo a algunos
servidores, hace que servidores que empezaron identicos terminen
siendo todos distintos entre si — "servidores copo de nieve", cada
uno con una historia unica y en gran parte indocumentada.
"""
import random


def make_base_config() -> dict:
    return {"setting_a": "default", "setting_b": "default", "setting_c": "default", "setting_d": "default"}


PATCHES = [
    ("fix_a_v1", lambda c: c.update(setting_a="patched_v1")),
    ("fix_a_v2", lambda c: c.update(setting_a="patched_v2")),
    ("fix_b", lambda c: c.update(setting_b="patched")),
    ("hotfix_c", lambda c: c.update(setting_c="hotfixed")),
    ("tweak_d", lambda c: c.update(setting_d="tweaked")),
    ("revert_d", lambda c: c.update(setting_d="default")),
]


def simulate_mutable_drift(n_servers: int, n_maintenance_events: int, rng: random.Random):
    """Cada evento de mantenimiento aplica UN parche a mano, a un
    subconjunto AL AZAR de servidores (el tipico "se aplico donde
    hacia falta en su momento, y despues nadie se acordo de
    completarlo en el resto").
    """
    servers = [make_base_config() for _ in range(n_servers)]

    for _ in range(n_maintenance_events):
        _, patch_fn = rng.choice(PATCHES)
        subset_size = rng.randint(1, max(1, n_servers // 3))
        affected_indices = rng.sample(range(n_servers), k=subset_size)
        for i in affected_indices:
            patch_fn(servers[i])

    unique_configs = {tuple(sorted(s.items())) for s in servers}
    return len(unique_configs), servers


def simulate_immutable_replacement(n_servers: int, n_releases: int):
    """Cada release construye una imagen nueva (con un numero de
    version) y REEMPLAZA a todos los servidores por instancias nuevas
    de esa imagen. Nunca se modifica un servidor existente.
    """
    servers = [0] * n_servers  # todos arrancan en la version de imagen 0
    for release in range(1, n_releases + 1):
        servers = [release] * n_servers  # reemplazo completo, no un parche parcial

    unique_versions = set(servers)
    return len(unique_versions), servers
