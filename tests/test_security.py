from datetime import UTC, datetime, timedelta

from src.security import can_cancel


def test_owner_within_24h():
    now = datetime.now(UTC)
    assert can_cancel("NEW", 1, 1, False, now - timedelta(hours=1), now)


def test_stranger_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 2, False, now, now)


def test_shipped_denied_even_admin():
    now = datetime.now(UTC)
    assert not can_cancel("SHIPPED", 1, 1, True, now, now)


def test_expired_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 1, False, now - timedelta(hours=25), now)


# --- Paso 6: Nuevas pruebas de autorización solicitadas ---
def test_admin_can_cancel_other_user_new_order():
    now = datetime.now(UTC)
    # Admin (user_id=99) cancela pedido de otro usuario (owner_id=1) en estado NEW
    assert (
        can_cancel(
            "NEW",
            owner_id=1,
            user_id=99,
            is_admin=True,
            created_at=now - timedelta(hours=5),
            now=now,
        )
        is True
    )


def test_owner_exact_24h_boundary_denied():
    now = datetime.now(UTC)
    # Propietario intenta cancelar exactamente en el límite de las 24 horas (debe denegarse)
    created_at = now - timedelta(hours=24)
    assert (
        can_cancel("NEW", owner_id=1, user_id=1, is_admin=False, created_at=created_at, now=now)
        is False
    )
