"""Capa de Aplicación de FitZone.
Casos de uso para Reservaciones y Control de Acceso Físico con Mocks.
"""

from src.fitzone.domain import ClaseProgramada, FitZoneDomainError, Socio


class ReservaAppService:
    """Servicio de aplicación para coordinar el flujo de reservaciones."""

    def __init__(self, notificador=None):
        self.notificador = notificador

    def procesar_reserva(self, socio: Socio, clase: ClaseProgramada) -> str:
        """Ejecuta la reservación y notifica al socio si se dispone de servicio."""
        resultado = clase.reservar(socio)
        if self.notificador:
            self.notificador.enviar_confirmacion(socio.id, clase.id, resultado)
        return resultado

    def procesar_cancelacion(
        self, socio: Socio, clase: ClaseProgramada, horas_anticipacion: float
    ) -> str:
        """Ejecuta la cancelación y notifica eventual promoción."""
        resultado = clase.cancelar_reserva(socio, horas_anticipacion)
        if self.notificador and "CANCELADA_CON_PROMOCION" in resultado:
            promovido_id = int(resultado.split(":")[1])
            self.notificador.notificar_promocion_lista_espera(promovido_id, clase.id)
        return resultado


class ControlAccesoService:
    """Servicio de control de acceso físico a torniquetes inteligentes de FitZone."""

    def __init__(self, hardware_torniquete):
        self.torniquete = hardware_torniquete

    def validar_y_abrir_acceso(self, socio: Socio) -> bool:
        """Comprueba vigencia comercial y envía pulso de apertura al torniquete."""
        try:
            socio.validar_puede_reservar()
        except FitZoneDomainError:
            self.torniquete.bloquear_paso(socio.id)
            raise

        apertura_exitosa = self.torniquete.abrir_puerta(socio.id)
        if not apertura_exitosa:
            raise RuntimeError("Fallo electromecánico al destrabar torniquete")

        return True
