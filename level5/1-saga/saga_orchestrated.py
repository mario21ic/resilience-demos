"""Saga orquestada: un unico coordinador conoce TODOS los pasos, en
orden, y sus compensaciones. Si un paso falla, el orquestador mismo
dispara las compensaciones de los pasos ya completados, en orden
inverso.

Toda la logica del flujo (que pasa despues de que, que se deshace si
algo falla) vive en UN solo lugar — facil de leer de punta a punta,
pero el orquestador tiene que conocer a todos los servicios.
"""
from services import (
    OrderContext,
    arrange_shipping,
    charge_payment,
    reserve_inventory,
    release_inventory,
    refund_payment,
)

STEPS = [
    (reserve_inventory, release_inventory),
    (charge_payment, refund_payment),
    (arrange_shipping, None),
]


class SagaFailed(Exception):
    pass


def run_orchestrated_saga(ctx: OrderContext):
    completed_compensations = []

    for action, compensation in STEPS:
        try:
            action(ctx)
        except Exception as exc:
            ctx.record(f"FALLO en {action.__name__}: {exc}")
            for comp in reversed(completed_compensations):
                comp(ctx)
            raise SagaFailed(f"saga revertida tras fallar en {action.__name__}") from exc
        else:
            if compensation is not None:
                completed_compensations.append(compensation)

    ctx.record("saga completada con exito")
