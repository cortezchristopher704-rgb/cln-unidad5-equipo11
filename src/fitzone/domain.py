"""Dominio de FitZone - Reglas de Negocio del Sistema de Gimnasio.
Entidades, Invariantes y Excepciones de Dominio (PIA Equipo 11).
"""

from dataclasses import dataclass, field


class FitZoneDomainError(Exception):
    """Excepción base del dominio FitZone."""


class MembresiaInactivaError(FitZoneDomainError):
    """El socio no cuenta con una membresía activa o vigente."""


class SocioBloqueadoError(FitZoneDomainError):
    """El socio se encuentra sancionado por exceso de inasistencias (no-shows)."""


class ClaseSinCupoError(FitZoneDomainError):
    """La clase y su lista de espera han alcanzado el aforo máximo."""


class ReservaDuplicadaError(FitZoneDomainError):
    """El socio ya cuenta con reserva activa o turno en lista de espera."""


class CancelacionTardiaError(FitZoneDomainError):
    """La cancelación se solicitó con menos de 2 horas de anticipación."""


@dataclass
class Socio:
    """Entidad Socio de FitZone."""

    id: int
    nombre: str
    membresia_activa: bool = True
    no_shows_consecutivos: int = 0
    bloqueado: bool = False
    dias_sancion: int = 0

    def validar_puede_reservar(self) -> None:
        """Verifica que el socio cumpla las condiciones comerciales para reservar."""
        if not self.membresia_activa:
            raise MembresiaInactivaError("Membresía inactiva o vencida")
        if self.bloqueado:
            raise SocioBloqueadoError(
                f"Socio suspendido por inasistencias ({self.dias_sancion} días de sanción)"
            )

    def registrar_no_show(self) -> None:
        """Registra una inasistencia y aplica bloqueo automático al 3er no-show."""
        self.no_shows_consecutivos += 1
        if self.no_shows_consecutivos >= 3:
            self.bloqueado = True
            self.dias_sancion = 14

    def registrar_asistencia(self) -> None:
        """Restablece el contador de faltas consecutivas al asistir a clase."""
        self.no_shows_consecutivos = 0

    def desbloquear(self) -> None:
        """Levanta la sanción administrativa del socio."""
        self.bloqueado = False
        self.dias_sancion = 0
        self.no_shows_consecutivos = 0


@dataclass
class ClaseProgramada:
    """Aggregate Root de una Clase Programada en FitZone."""

    id: int
    disciplina: str
    capacidad_maxima: int
    reservas: list[int] = field(default_factory=list)
    lista_espera: list[int] = field(default_factory=list)
    max_lista_espera: int = 5

    @property
    def cupos_disponibles(self) -> int:
        """Calcula los cupos libres restantes en la clase."""
        return max(0, self.capacidad_maxima - len(self.reservas))

    def reservar(self, socio: Socio) -> str:
        """Aplica la regla de reservación según capacidad y estado del socio."""
        socio.validar_puede_reservar()

        if socio.id in self.reservas or socio.id in self.lista_espera:
            raise ReservaDuplicadaError("El socio ya cuenta con un turno registrado en la clase")

        if len(self.reservas) < self.capacidad_maxima:
            self.reservas.append(socio.id)
            return "CONFIRMADA"

        if len(self.lista_espera) < self.max_lista_espera:
            self.lista_espera.append(socio.id)
            return "LISTA_ESPERA"

        raise ClaseSinCupoError("Clase y lista de espera saturadas")

    def cancelar_reserva(self, socio: Socio, horas_anticipacion: float) -> str:
        """Cancela la reserva evaluando la ventana mínima de 2 horas."""
        if socio.id not in self.reservas:
            raise ValueError("El socio no tiene reserva confirmada en esta clase")

        self.reservas.remove(socio.id)

        # Regla: Cancelación tardía (< 2 horas)
        if horas_anticipacion < 2.0:
            socio.registrar_no_show()
            self._promover_lista_espera()
            raise CancelacionTardiaError(
                "Cancelación fuera de la ventana permitida (< 2h). Se registra inasistencia."
            )

        # Regla: Cancelación a tiempo (>= 2 horas)
        promovido = self._promover_lista_espera()
        if promovido is not None:
            return f"CANCELADA_CON_PROMOCION:{promovido}"
        return "CANCELADA_EXITOSA"

    def _promover_lista_espera(self) -> int | None:
        """Promueve al primer socio de la lista de espera al cupo liberado."""
        if self.lista_espera:
            promovido_id = self.lista_espera.pop(0)
            self.reservas.append(promovido_id)
            return promovido_id
        return None
