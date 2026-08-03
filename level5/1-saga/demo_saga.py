"""Demo: Saga — orquestada vs coreografiada.

Una saga de "crear pedido" con tres pasos (reservar inventario, cobrar
el pago, coordinar el envio), cada uno con su compensacion. Se corren
tres escenarios — exito, falla en el pago, falla en el envio — bajo
las dos formas de coordinar la saga, para mostrar que ambas llegan al
MISMO resultado final, pero con la logica de compensacion organizada
de forma muy distinta.
"""
from saga_choreographed import run_choreographed_saga
from saga_orchestrated import SagaFailed, run_orchestrated_saga
from services import OrderContext

SCENARIOS = [
    ("exito", None),
    ("falla en el pago", "charge_payment"),
    ("falla en el envio", "arrange_shipping"),
]


def run_and_print(label: str, run_fn, should_fail_at: str):
    ctx = OrderContext(order_id="ORD-1", should_fail_at=should_fail_at)
    try:
        run_fn(ctx)
    except SagaFailed as exc:
        ctx.record(f"saga terminada con error: {exc}")
    print(f"  {label}:")
    for line in ctx.log:
        print(f"    - {line}")


def main():
    print("=" * 70)
    print("SAGA ORQUESTADA (un coordinador central conoce todo el flujo)")
    print("=" * 70)
    for label, fail_at in SCENARIOS:
        run_and_print(label, run_orchestrated_saga, fail_at)
        print()

    print("=" * 70)
    print("SAGA COREOGRAFIADA (cada servicio reacciona a eventos, sin coordinador)")
    print("=" * 70)
    for label, fail_at in SCENARIOS:
        run_and_print(label, run_choreographed_saga, fail_at)
        print()

    print("Ambas formas llegan al mismo resultado final en cada escenario. La")
    print("diferencia esta en DONDE vive la logica de 'que se deshace si esto falla':")
    print("en la orquestada, en un unico lugar (la lista STEPS); en la coreografiada,")
    print("repartida en varios handlers registrados por separado en distintos servicios.")


if __name__ == "__main__":
    main()
