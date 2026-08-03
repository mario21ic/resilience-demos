"""Demo: Migraciones expand/contract.

Un rolling deploy de 10 instancias, reemplazando codigo viejo (usa la
columna `email`) por codigo nuevo (usa `email_address`) de a poco.

  Naive: la migracion hace `drop email; add email_address` en un solo
         paso destructivo, a mitad del rollout.
  Expand/contract: se agrega `email_address` DESDE EL PRINCIPIO (sin
         borrar `email`), y recien se borra `email` al final, cuando
         el 100% del codigo ya paso a usar el campo nuevo.
"""
from migrations import simulate_rollout

N_INSTANCES = 10
N_TICKS = 20


def naive_migration(schema, new_code_count, n_instances):
    schema.drop("email")
    schema.add("email_address")


def expand_migration(schema, new_code_count, n_instances):
    schema.add("email_address")  # EXPAND: agrega sin borrar


def contract_migration(schema, new_code_count, n_instances):
    if new_code_count == n_instances:  # CONTRACT: solo si ya se migro el 100%
        schema.drop("email")


def main():
    print("Rolling deploy de 10 instancias: codigo viejo usa 'email', codigo nuevo")
    print("usa 'email_address'. Cada instancia hace un request por tick.\n")

    failures_naive, total_naive = simulate_rollout(N_INSTANCES, N_TICKS, {10: naive_migration})
    failures_ec, total_ec = simulate_rollout(
        N_INSTANCES, N_TICKS, {0: expand_migration, 18: contract_migration}
    )

    print(f"  naive (drop+add en un solo paso, a mitad del rollout):")
    print(f"    requests fallidos: {failures_naive}/{total_naive}")
    print(f"  expand/contract (agrega al principio, borra recien al final):")
    print(f"    requests fallidos: {failures_ec}/{total_ec}")

    print(f"\n  con el enfoque naive, el {failures_naive / total_naive:.0%} de los requests")
    print("  fallan justo durante el rollout — exactamente el peor momento, porque es")
    print("  cuando mas variedad de versiones de codigo hay corriendo a la vez.")
    print("  Con expand/contract, CERO requests fallan en todo el proceso: siempre")
    print("  existe la columna que cada version de codigo necesita, sin importar")
    print("  en que punto del rollout este.")


if __name__ == "__main__":
    main()
