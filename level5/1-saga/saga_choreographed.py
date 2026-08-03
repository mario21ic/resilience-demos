"""Saga coreografiada: no hay coordinador central. Cada servicio
reacciona a los eventos que le interesan y publica los suyos propios
— el flujo completo (incluidas las compensaciones) es la SUMA de
todas esas suscripciones repartidas, no algo escrito en un solo lugar.

Notar que la logica de compensacion queda dispersa: quien reacciona a
"PaymentFailed" y quien reacciona a "ShippingFailed" son handlers
distintos, registrados por separado — no hay un unico lugar donde se
pueda leer "asi se deshace esta saga".
"""
from event_bus import EventBus
from services import (
    OrderContext,
    arrange_shipping,
    charge_payment,
    reserve_inventory,
    release_inventory,
    refund_payment,
)


def build_choreographed_bus() -> EventBus:
    bus = EventBus()

    def on_order_created(ctx: OrderContext):
        try:
            reserve_inventory(ctx)
            bus.publish("InventoryReserved", ctx)
        except Exception as exc:
            ctx.record(f"FALLO en reserve_inventory: {exc}")
            bus.publish("InventoryReservationFailed", ctx)

    def on_inventory_reserved(ctx: OrderContext):
        try:
            charge_payment(ctx)
            bus.publish("PaymentCharged", ctx)
        except Exception as exc:
            ctx.record(f"FALLO en charge_payment: {exc}")
            bus.publish("PaymentFailed", ctx)

    def on_payment_charged(ctx: OrderContext):
        try:
            arrange_shipping(ctx)
            bus.publish("ShippingArranged", ctx)
        except Exception as exc:
            ctx.record(f"FALLO en arrange_shipping: {exc}")
            bus.publish("ShippingFailed", ctx)

    # --- compensaciones: cada servicio escucha el evento de falla que le importa ---

    def on_payment_failed(ctx: OrderContext):
        bus.publish("InventoryReleaseRequested", ctx)

    def on_shipping_failed(ctx: OrderContext):
        refund_payment(ctx)
        bus.publish("PaymentRefunded", ctx)

    def on_payment_refunded(ctx: OrderContext):
        bus.publish("InventoryReleaseRequested", ctx)

    def on_inventory_release_requested(ctx: OrderContext):
        release_inventory(ctx)

    bus.subscribe("OrderCreated", on_order_created)
    bus.subscribe("InventoryReserved", on_inventory_reserved)
    bus.subscribe("PaymentCharged", on_payment_charged)
    bus.subscribe("PaymentFailed", on_payment_failed)
    bus.subscribe("ShippingFailed", on_shipping_failed)
    bus.subscribe("PaymentRefunded", on_payment_refunded)
    bus.subscribe("InventoryReleaseRequested", on_inventory_release_requested)

    return bus


def run_choreographed_saga(ctx: OrderContext):
    bus = build_choreographed_bus()
    bus.publish("OrderCreated", ctx)
