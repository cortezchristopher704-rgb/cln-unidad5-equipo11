"""Suite de Pruebas Automatizadas para FitZone (PIA Equipo 11).
Cubre los 9 casos de la matriz de dominio, persistencia transaccional y mocks de servicios externos.
"""

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from src.fitzone.application import ControlAccesoService, ReservaAppService
from src.fitzone.domain import (
    CancelacionTardiaError,
    ClaseProgramada,
    ClaseSinCupoError,
    MembresiaInactivaError,
    ReservaDuplicadaError,
    Socio,
    SocioBloqueadoError,
)
from src.fitzone.repository import (
    SqlFitZoneRepository,
    make_fitzone_engine,
)

# ==============================================================================
# REGLA 1: Control de Aforo y Reservación de Clase
# ==============================================================================


def test_cp_fz_01_reserva_exitosa_con_cupo_disponible():
    """CP-FZ-01 (Éxito): Socio con membresía activa reserva clase con cupos disponibles."""
    socio = Socio(id=101, nombre="Carlos Mendoza", membresia_activa=True)
    clase = ClaseProgramada(id=1, disciplina="CrossFit", capacidad_maxima=20)

    resultado = clase.reservar(socio)

    assert resultado == "CONFIRMADA"
    assert socio.id in clase.reservas
    assert clase.cupos_disponibles == 19


def test_cp_fz_02_reserva_rechazada_membresia_inactiva():
    """CP-FZ-02 (Error): Socio con membresía inactiva intenta reservar."""
    socio = Socio(id=102, nombre="Valeria Rios", membresia_activa=False)
    clase = ClaseProgramada(id=1, disciplina="Spinning", capacidad_maxima=15)

    with pytest.raises(MembresiaInactivaError, match="Membresía inactiva o vencida"):
        clase.reservar(socio)

    assert socio.id not in clase.reservas
    assert clase.cupos_disponibles == 15


def test_cp_fz_03_reserva_limite_aforo_y_derivacion_lista_espera():
    """CP-FZ-03 (Límite): Reserva del último cupo libre y desvío del siguiente a lista de espera."""
    s1 = Socio(id=201, nombre="Socio Uno")
    s2 = Socio(id=202, nombre="Socio Dos")
    s3 = Socio(id=203, nombre="Socio Tres")

    clase = ClaseProgramada(id=2, disciplina="Box", capacidad_maxima=2)

    assert clase.reservar(s1) == "CONFIRMADA"
    assert clase.cupos_disponibles == 1

    # Límite exacto de capacidad
    assert clase.reservar(s2) == "CONFIRMADA"
    assert clase.cupos_disponibles == 0

    # Excedente inmediato se deriva a lista de espera
    assert clase.reservar(s3) == "LISTA_ESPERA"
    assert s3.id in clase.lista_espera
    assert s3.id not in clase.reservas


def test_fz_reserva_duplicada_rechazada():
    """Validación adicional: un socio no puede reservar dos veces la misma clase."""
    s = Socio(id=205, nombre="Socio Duplicado")
    clase = ClaseProgramada(id=3, disciplina="Yoga", capacidad_maxima=10)
    clase.reservar(s)

    with pytest.raises(ReservaDuplicadaError):
        clase.reservar(s)


def test_fz_saturacion_total_clase_y_espera():
    """Validación adicional: rechazo cuando clase y lista de espera están llenas."""
    clase = ClaseProgramada(id=4, disciplina="Pilates", capacidad_maxima=1, max_lista_espera=1)
    s1 = Socio(id=301, nombre="Socio 1")
    s2 = Socio(id=302, nombre="Socio 2")
    s3 = Socio(id=303, nombre="Socio 3")

    clase.reservar(s1)  # Confirma
    clase.reservar(s2)  # Lista de espera (llena)
    with pytest.raises(ClaseSinCupoError):
        clase.reservar(s3)


# ==============================================================================
# REGLA 2: Política de Inasistencias (No-Shows) y Sanciones
# ==============================================================================


def test_cp_fz_04_asistencia_restablece_faltas():
    """CP-FZ-04 (Éxito): Socio con 1 falta asiste a clase y resetea su contador."""
    socio = Socio(id=103, nombre="Laura Garza", no_shows_consecutivos=1)

    socio.registrar_asistencia()

    assert socio.no_shows_consecutivos == 0
    assert socio.bloqueado is False


def test_cp_fz_05_socio_bloqueado_no_puede_reservar():
    """CP-FZ-05 (Error): Socio bloqueado por sanción intenta reservar clase."""
    socio = Socio(
        id=104, nombre="Mario Cantú", bloqueado=True, dias_sancion=14, no_shows_consecutivos=3
    )
    clase = ClaseProgramada(id=1, disciplina="Zumba", capacidad_maxima=25)

    with pytest.raises(SocioBloqueadoError, match="Socio suspendido por inasistencias"):
        clase.reservar(socio)


def test_cp_fz_06_limite_tercer_no_show_activa_bloqueo_automatico():
    """CP-FZ-06 (Límite): Acumulación del 3er no-show consecutivo activa sanción automática."""
    socio = Socio(id=105, nombre="Andrea Treviño", no_shows_consecutivos=2)

    # Ocurre la 3ra inasistencia consecutiva (límite de tolerancia)
    socio.registrar_no_show()

    assert socio.no_shows_consecutivos == 3
    assert socio.bloqueado is True
    assert socio.dias_sancion == 14

    # Desbloqueo administrativo
    socio.desbloquear()
    assert socio.bloqueado is False
    assert socio.dias_sancion == 0


# ==============================================================================
# REGLA 3: Política de Cancelación y Promoción de Lista de Espera
# ==============================================================================


def test_cp_fz_07_cancelacion_a_tiempo_sin_lista_espera():
    """CP-FZ-07 (Éxito): Cancelación con 3h de anticipación (>= 2h) sin penalización."""
    socio = Socio(id=106, nombre="Raúl Cavazos")
    clase = ClaseProgramada(id=5, disciplina="HIIT", capacidad_maxima=10)
    clase.reservar(socio)
    assert clase.cupos_disponibles == 9

    resultado = clase.cancelar_reserva(socio, horas_anticipacion=3.0)

    assert resultado == "CANCELADA_EXITOSA"
    assert socio.id not in clase.reservas
    assert clase.cupos_disponibles == 10
    assert socio.no_shows_consecutivos == 0


def test_cp_fz_08_cancelacion_tardia_aplica_sancion():
    """CP-FZ-08 (Error): Cancelación con 1h de anticipación (< 2h) penaliza al socio."""
    socio = Socio(id=107, nombre="Daniela Morales", no_shows_consecutivos=0)
    clase = ClaseProgramada(id=6, disciplina="Spinning", capacidad_maxima=15)
    clase.reservar(socio)

    with pytest.raises(CancelacionTardiaError, match="Cancelación fuera de la ventana permitida"):
        clase.cancelar_reserva(socio, horas_anticipacion=1.0)

    # El lugar fue liberado pero se sancionó con no-show
    assert socio.id not in clase.reservas
    assert socio.no_shows_consecutivos == 1


def test_cp_fz_09_cancelacion_limite_exacto_2h_y_promocion_lista_espera():
    """CP-FZ-09 (Límite): Cancelación en el límite exacto (2.0h) promueve de lista de espera."""
    s1 = Socio(id=401, nombre="Titular Reserva")
    s2 = Socio(id=402, nombre="En Espera")

    clase = ClaseProgramada(id=7, disciplina="Natación", capacidad_maxima=1)
    clase.reservar(s1)  # Toma el único cupo
    clase.reservar(s2)  # Pasa a lista de espera

    assert s2.id in clase.lista_espera

    # Cancelación en el límite exacto de 2.0 horas (permitida sin falta)
    resultado = clase.cancelar_reserva(s1, horas_anticipacion=2.0)

    assert resultado == f"CANCELADA_CON_PROMOCION:{s2.id}"
    assert s1.id not in clase.reservas
    assert s1.no_shows_consecutivos == 0
    assert s2.id in clase.reservas
    assert len(clase.lista_espera) == 0


def test_fz_cancelar_reserva_inexistente():
    """Validación adicional: error al cancelar clase donde no se tiene reserva."""
    socio = Socio(id=500, nombre="Sin Reserva")
    clase = ClaseProgramada(id=8, disciplina="Yoga", capacidad_maxima=10)

    with pytest.raises(ValueError, match="El socio no tiene reserva confirmada"):
        clase.cancelar_reserva(socio, horas_anticipacion=5.0)


# ==============================================================================
# INTEGRACIÓN: Persistencia con SQLAlchemy y Transacciones (Commit / Rollback)
# ==============================================================================


def test_fitzone_repository_commit():
    """CP-FZ-10a: Guardado y consulta persistente de socio y clase con commit."""
    engine = make_fitzone_engine()
    socio = Socio(id=701, nombre="Esteban Reyna", membresia_activa=True)
    clase = ClaseProgramada(id=10, disciplina="TRX", capacidad_maxima=15)
    clase.reservar(socio)

    with Session(engine) as session:
        repo = SqlFitZoneRepository(session)
        repo.save_socio(socio)
        repo.save_clase(clase)
        session.commit()

        # Recuperar desde la base de datos
        recuperado = repo.get_socio(701)
        assert recuperado is not None
        assert recuperado.id == 701
        assert recuperado.nombre == "Esteban Reyna"
        assert recuperado.membresia_activa is True

        clase_row = repo.get_clase_row(10)
        assert clase_row is not None
        assert clase_row.disciplina == "TRX"
        assert clase_row.reservas_count == 1


def test_fitzone_repository_rollback():
    """CP-FZ-10b: Reversión atómica de cambios no confirmados (rollback)."""
    engine = make_fitzone_engine()
    socio = Socio(id=702, nombre="Socio Cancelado", membresia_activa=True)

    with Session(engine) as session:
        repo = SqlFitZoneRepository(session)
        repo.save_socio(socio)
        session.rollback()

        # Al hacer rollback, no debe existir en la base
        assert repo.get_socio(702) is None


def test_fitzone_repository_update_existing_rows():
    """CP-FZ-10c: Actualización de registros existentes en SQLite."""
    engine = make_fitzone_engine()
    socio = Socio(id=703, nombre="Socio Original", no_shows_consecutivos=0)
    clase = ClaseProgramada(id=11, disciplina="Pilates", capacidad_maxima=5)

    with Session(engine) as session:
        repo = SqlFitZoneRepository(session)
        repo.save_socio(socio)
        repo.save_clase(clase)
        session.commit()

        # Modificar objetos y volver a guardar para probar rama de update
        socio.no_shows_consecutivos = 2
        clase.disciplina = "Pilates Avanzado"
        repo.save_socio(socio)
        repo.save_clase(clase)
        session.commit()

        actualizado_socio = repo.get_socio(703)
        assert actualizado_socio.no_shows_consecutivos == 2
        actualizado_clase = repo.get_clase_row(11)
        assert actualizado_clase.disciplina == "Pilates Avanzado"


# ==============================================================================
# SERVICIOS EXTERNOS CON MOCK: Control de Acceso y Notificador
# ==============================================================================


def test_fitzone_mock_torniquete_acceso_permitido():
    """CP-FZ-11a: Socio con membresía activa destraba torniquete simulado con Mock."""
    torniquete_mock = Mock()
    torniquete_mock.abrir_puerta.return_value = True

    servicio = ControlAccesoService(torniquete_mock)
    socio = Socio(id=801, nombre="Diana Lozano", membresia_activa=True)

    assert servicio.validar_y_abrir_acceso(socio) is True
    torniquete_mock.abrir_puerta.assert_called_once_with(801)


def test_fitzone_mock_torniquete_fallo_hardware():
    """CP-FZ-11b: Falla electromecánica del torniquete lanza RuntimeError."""
    torniquete_mock = Mock()
    torniquete_mock.abrir_puerta.return_value = False

    servicio = ControlAccesoService(torniquete_mock)
    socio = Socio(id=802, nombre="Javier Soto", membresia_activa=True)

    with pytest.raises(RuntimeError, match="Fallo electromecánico"):
        servicio.validar_y_abrir_acceso(socio)


def test_fitzone_mock_torniquete_acceso_denegado_socio_bloqueado():
    """CP-FZ-11c: Socio bloqueado activa bloqueo de paso en torniquete."""
    torniquete_mock = Mock()
    servicio = ControlAccesoService(torniquete_mock)
    socio = Socio(id=803, nombre="Socio Sancionado", bloqueado=True, dias_sancion=14)

    with pytest.raises(SocioBloqueadoError):
        servicio.validar_y_abrir_acceso(socio)

    torniquete_mock.bloquear_paso.assert_called_once_with(803)
    torniquete_mock.abrir_puerta.assert_not_called()


def test_fitzone_reserva_app_service_notificador_mock():
    """CP-FZ-12a: Servicio de aplicación invoca notificaciones de confirmación."""
    notificador_mock = Mock()
    app_service = ReservaAppService(notificador_mock)

    s1 = Socio(id=901, nombre="Socio Notificado")
    clase = ClaseProgramada(id=20, disciplina="CrossFit", capacidad_maxima=10)

    resultado = app_service.procesar_reserva(s1, clase)
    assert resultado == "CONFIRMADA"
    notificador_mock.enviar_confirmacion.assert_called_once_with(901, 20, "CONFIRMADA")


def test_fitzone_reserva_app_service_cancelacion_notificador_mock():
    """CP-FZ-12b: Servicio de aplicación notifica promoción al cancelar con lista de espera."""
    notificador_mock = Mock()
    app_service = ReservaAppService(notificador_mock)

    s1 = Socio(id=910, nombre="Socio Cancela")
    s2 = Socio(id=911, nombre="Socio Espera")
    clase = ClaseProgramada(id=21, disciplina="Spinning", capacidad_maxima=1)

    clase.reservar(s1)
    clase.reservar(s2)

    resultado = app_service.procesar_cancelacion(s1, clase, horas_anticipacion=3.0)
    assert resultado == f"CANCELADA_CON_PROMOCION:{s2.id}"
    notificador_mock.notificar_promocion_lista_espera.assert_called_once_with(911, 21)
