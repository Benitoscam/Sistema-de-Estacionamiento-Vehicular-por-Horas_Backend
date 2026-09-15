# Sistema de Estacionamiento Vehicular por Horas — Backend

Proyecto del Módulo Fullstack — Diplomado en Desarrollo de Software (SIG-116).

API del sistema de estacionamiento vehicular por horas. Permite reservar un espacio
por adelantado o registrar el ingreso sin reserva previa (cobrando según el tiempo
real de permanencia), y gestionar espacios, tarifas, zonas y el estado de ocupación
del establecimiento.

Este repositorio contiene solo la API. El cliente web que la consume vive en un
repositorio frontend separado (React + Vite + TypeScript).

## Arquitectura

- **Basada en la estructura:** Cliente-Servidor
- **Basada en el dominio:** Hexagonal (Puertos y Adaptadores)

```
app/
  domain/        → Entidades y lógica pura (Espacio, Tarifa, CalculadoraDeCobro)
  application/    → Casos de uso (ReservarEspacio, RegistrarIngreso, RegistrarSalida)
  ports/          → Interfaces (IReservationRepository, IPaymentGateway, IPlateRecognizer, INotifier)
  adapters/
    http/         → Rutas/controladores Flask (puerto de entrada)
    db/           → Repositorios con SQLAlchemy (adaptador de salida hacia PostgreSQL)
    payment/      → Adaptador de Stripe
    ocr/          → Adaptador de reconocimiento de placas (EasyOCR/OpenCV) — fase 2
```

Regla de dependencia: las flechas siempre apuntan hacia el dominio (`ports/`); los
adaptadores implementan las interfaces definidas por el dominio, nunca al revés.

## Stack técnico

- Python 3.13 + Flask (framework web)
- SQLAlchemy (ORM)
- PostgreSQL 18 (base de datos)
- psycopg2-binary (driver de conexión)
- Flask-JWT-Extended (autenticación JWT, expira en 8h)
- bcrypt (hasheo de contraseñas)
- Flask-CORS (peticiones desde el frontend)
- ReportLab (generación de PDFs en memoria — reportes de ingresos, comprobantes)
- EasyOCR + OpenCV (reconocimiento de placas — **fase 2 / opcional**, aislado detrás
  del puerto `IPlateRecognizer`; la versión inicial usa entrada manual de placa)

## Pagos

- Stripe (SDK oficial de Python) — Checkout + webhooks para confirmar pagos de
  reserva y cobros por tiempo real

## Roles

- **Cliente**: busca disponibilidad, reserva, paga.
- **Operador**: registra ingreso/salida sin reserva, cobra.
- **Administrador**: gestiona espacios/tarifas/zonas, ve dashboard y reportes.

## Desarrollo

```bash
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
cp .env.example .env      # completar con las credenciales locales
python run.py
```

## Notas

- El dashboard de ocupación en tiempo real se resuelve mediante un endpoint de
  consulta simple (polling desde el frontend vía `refetchInterval` de TanStack
  Query), no WebSockets — suficiente para el volumen de tráfico del proyecto
  (máximo 20 usuarios en un día ajetreado).
- El reconocimiento de placas (EasyOCR/OpenCV) se implementa en una fase
  posterior; el flujo principal (reserva, ingreso/salida, cálculo de tarifa,
  pago) debe funcionar primero con entrada manual de placa.
