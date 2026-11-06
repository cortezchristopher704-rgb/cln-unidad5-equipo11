# Unidad 5 · Componentes de Lógica de Negocio · Equipo 11 (FitZone)

Este proyecto demuestra, con **pruebas automáticas**, que las reglas de negocio funcionan.
Incluye el ejemplo de pedidos del laboratorio y las reglas reales de la empresa **FitZone** (gimnasio) del PIA.

- **41 pruebas** en total (20 de FitZone), todas en verde.
- **Cobertura 100 %** (el mínimo exigido es 80 %), con reporte HTML en `htmlcov/index.html`.
- **Integración continua** en GitHub Actions: https://github.com/cortezchristopher704-rgb/cln-unidad5-equipo11

## 1. Requisitos

- Python 3.11 o superior.
- No se necesita internet ni base de datos externa para correr las pruebas.

## 2. Instalación

En Windows (PowerShell), dentro de la carpeta del proyecto:

```
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En Linux o macOS:

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 3. Comandos

| Qué quieres hacer | Comando |
|---|---|
| Correr todas las pruebas | `python -m pytest -v` |
| Correr solo las de FitZone | `python -m pytest tests/test_fitzone.py -v` |
| Medir cobertura (mínimo 80 %) y generar el reporte HTML | `python -m pytest -v --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80` |
| Revisar el estilo del código | `python -m ruff check src tests` |

Después de medir la cobertura, abre `htmlcov/index.html` en el navegador.

## 4. Estructura y arquitectura

```
src/
├── domain.py            Reglas del pedido (descuento VIP, no confirmar dos veces, total válido, deuda)
├── application.py       Caso de uso "checkout": recibe una pasarela de pago
├── repository.py        Guardado en base de datos con SQLAlchemy (SQLite)
├── security.py          Política de quién puede cancelar un pedido
└── fitzone/
    ├── domain.py        Reglas de FitZone: aforo, faltas y cancelaciones
    ├── application.py   Casos de uso que reciben el torniquete y el notificador
    └── repository.py    Guardado de clases y socios con SQLAlchemy
tests/                   Pruebas de dominio, persistencia, seguridad, mocks y FitZone
.github/workflows/ci.yml Pipeline de GitHub Actions (ruff, pytest con cobertura y compileall)
matriz_casos_fitzone.csv Matriz de 11 casos de prueba del PIA
htmlcov/                 Reporte HTML de cobertura
```

El código se separa en capas para poder probarlo por partes:

1. **Dominio:** las reglas del negocio. No usa base de datos, red ni servicios externos, por eso sus pruebas son rápidas.
2. **Aplicación:** coordina los pasos. Recibe sus dependencias (la pasarela de pago, el torniquete, el notificador), así que en las pruebas se reemplazan por **Mocks** y nunca se cobra dinero ni se activa hardware real.
3. **Persistencia:** guarda en SQLite. En las pruebas la base es **en memoria**: se crea y se borra en cada ejecución.
4. **Seguridad:** decide quién puede cancelar un pedido y cuándo.

## 5. Reglas de negocio probadas

**Pedidos (ejemplo del laboratorio)**

- Un cliente VIP recibe 15 % de descuento (un pedido de $200 se cobra en $170).
- No se confirma un pedido con total cero o negativo, con cliente con deuda, ni dos veces el mismo pedido.
- Un pedido ya enviado (SHIPPED) no se puede cancelar; el administrador puede cancelar pedidos nuevos de otros usuarios; el dueño solo dentro de las primeras 24 horas (a las 24 horas exactas ya no).

**FitZone (PIA)**

- **Regla 1, aforo:** una clase tiene cupo máximo; solo reservan socios con membresía activa y sin reserva duplicada; si se llena, pasa a lista de espera (máximo 5 personas).
- **Regla 2, faltas:** cada no-show suma una falta; con 3 faltas consecutivas el socio queda bloqueado 14 días; asistir reinicia el contador.
- **Regla 3, cancelaciones:** con 2 horas o más de anticipación se cancela sin penalización (a las 2.0 horas exactas todavía cuenta como a tiempo); con menos de 2 horas es cancelación tardía: se libera el lugar y se suma una falta. Al liberarse un lugar, pasa el primero de la lista de espera.

## 6. Avisos importantes

- Los **pagos y el torniquete son simulados** (Mocks): nunca se cobra dinero real.
- La base de datos de las pruebas es **temporal** (SQLite en memoria).
- Una prueba falla a propósito en el ciclo TDD (rojo) y hubo una ejecución roja a propósito en GitHub; ambas se corrigieron.
- El ejemplo de pedidos **confirma el pedido antes de cobrar**: es un riesgo conocido, documentado en el reporte con su propuesta de mejora.
- Los mensajes de error del ejemplo de pedidos están en inglés porque vienen del proyecto base del profesor; los de FitZone están en español.
- La cancelación tardía **no cobra multa**: solo suma una falta.
- FitZone guarda en la base únicamente la cantidad de reservas, no la lista de socios ni la lista de espera.
- Al correr toda la suite aparecen 3 avisos (warnings) por conexiones SQLite sin cerrar en las pruebas; no son fallos.
- 100 % de cobertura no significa cero errores: indica qué líneas se ejecutaron.
- El pipeline marca el commit en rojo y avisa, pero no impide el push por sí solo; para bloquearlo haría falta activar *branch protection* en GitHub.
