"""Los pasos de negocio de una saga de "crear pedido": reservar
inventario, cobrar el pago, coordinar el envio. Cada paso tiene una
accion y, salvo el ultimo, una compensacion — la operacion que
deshace su efecto si un paso POSTERIOR de la saga falla.

Este modulo es deliberadamente el mismo para las dos formas de
coordinar la saga (orquestada y coreografiada, ver
`saga_orchestrated.py` y `saga_choreographed.py`): lo que cambia entre
ambas no es QUE hace cada paso, sino QUIEN decide el orden y quien
dispara las compensaciones.
"""


class OrderContext:
    def __init__(self, order_id: str, should_fail_at: str = None):
        self.order_id = order_id
        self.should_fail_at = should_fail_at  # nombre del paso a simular como fallido, o None
        self.log: list = []

    def record(self, message: str):
        self.log.append(message)


def reserve_inventory(ctx: OrderContext):
    if ctx.should_fail_at == "reserve_inventory":
        raise RuntimeError("sin stock suficiente")
    ctx.record("inventario reservado")


def release_inventory(ctx: OrderContext):
    ctx.record("COMPENSACION: inventario liberado")


def charge_payment(ctx: OrderContext):
    if ctx.should_fail_at == "charge_payment":
        raise RuntimeError("tarjeta rechazada")
    ctx.record("pago cobrado")


def refund_payment(ctx: OrderContext):
    ctx.record("COMPENSACION: pago reembolsado")


def arrange_shipping(ctx: OrderContext):
    if ctx.should_fail_at == "arrange_shipping":
        raise RuntimeError("sin transportista disponible")
    ctx.record("envio coordinado")
