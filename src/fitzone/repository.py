"""Capa de Persistencia e Infraestructura de FitZone.
Modelos relacionales con SQLAlchemy y Repositorios para Socios y Clases.
"""

from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from src.fitzone.domain import ClaseProgramada, Socio


class BaseFitZone(DeclarativeBase):
    pass


class SocioRow(BaseFitZone):
    __tablename__ = "fitzone_socios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    membresia_activa = Column(Boolean, nullable=False, default=True)
    no_shows_consecutivos = Column(Integer, nullable=False, default=0)
    bloqueado = Column(Boolean, nullable=False, default=False)
    dias_sancion = Column(Integer, nullable=False, default=0)


class ClaseRow(BaseFitZone):
    __tablename__ = "fitzone_clases"

    id = Column(Integer, primary_key=True)
    disciplina = Column(String, nullable=False)
    capacidad_maxima = Column(Integer, nullable=False)
    reservas_count = Column(Integer, nullable=False, default=0)


class SqlFitZoneRepository:
    """Repositorio SQL para transacciones de negocio de FitZone."""

    def __init__(self, session: Session):
        self.session = session

    def save_socio(self, socio: Socio) -> None:
        row = self.session.get(SocioRow, socio.id)
        if row:
            row.nombre = socio.nombre
            row.membresia_activa = socio.membresia_activa
            row.no_shows_consecutivos = socio.no_shows_consecutivos
            row.bloqueado = socio.bloqueado
            row.dias_sancion = socio.dias_sancion
        else:
            self.session.add(
                SocioRow(
                    id=socio.id,
                    nombre=socio.nombre,
                    membresia_activa=socio.membresia_activa,
                    no_shows_consecutivos=socio.no_shows_consecutivos,
                    bloqueado=socio.bloqueado,
                    dias_sancion=socio.dias_sancion,
                )
            )

    def get_socio(self, socio_id: int) -> Socio | None:
        row = self.session.get(SocioRow, socio_id)
        if not row:
            return None
        return Socio(
            id=row.id,
            nombre=row.nombre,
            membresia_activa=row.membresia_activa,
            no_shows_consecutivos=row.no_shows_consecutivos,
            bloqueado=row.bloqueado,
            dias_sancion=row.dias_sancion,
        )

    def save_clase(self, clase: ClaseProgramada) -> None:
        row = self.session.get(ClaseRow, clase.id)
        if row:
            row.disciplina = clase.disciplina
            row.capacidad_maxima = clase.capacidad_maxima
            row.reservas_count = len(clase.reservas)
        else:
            self.session.add(
                ClaseRow(
                    id=clase.id,
                    disciplina=clase.disciplina,
                    capacidad_maxima=clase.capacidad_maxima,
                    reservas_count=len(clase.reservas),
                )
            )

    def get_clase_row(self, clase_id: int) -> ClaseRow | None:
        return self.session.get(ClaseRow, clase_id)


def make_fitzone_engine(url="sqlite+pysqlite:///:memory:"):
    engine = create_engine(url)
    BaseFitZone.metadata.create_all(engine)
    return engine
