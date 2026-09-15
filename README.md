# Sistema de Estacionamiento Vehicular por Horas

Proyecto del Módulo Fullstack — Diplomado en Desarrollo de Software (SIG-116).

Sistema que permite a los clientes reservar un espacio de estacionamiento por adelantado o ingresar sin reserva previa (pagando según el tiempo real de permanencia), y a los administradores gestionar espacios, tarifas, zonas y el estado de ocupación del establecimiento.

## Arquitectura

- **Basada en la estructura:** Cliente-Servidor
- **Basada en el dominio:** Hexagonal (Puertos y Adaptadores)

```
/app
  /domain        → Entidades y lógica pura (Espacio, Tarifa, CalculadoraDeCobro)
  /application    → Casos de uso (ReservarEspacio, RegistrarIngreso, RegistrarSalida)
  /ports          → Interfaces (IReservationRepository, IPaymentGateway, IPlateRecognizer, INotifier)
  /adapters
    /http         → Rutas/controladores Flask (puerto de entrada)
    /db           → Repositorios con SQLAlchemy (adaptador de salida hacia PostgreSQL)
    /payment      → Adaptador de Stripe
    /ocr          → Adaptador de reconocimiento de placas (EasyOCR/OpenCV) — fase 2
```

## Stack técnico

### Backend

- Python 3.13 + Flask (framework web)
- SQLAlchemy (ORM)
- PostgreSQL 18 (base de datos)
- psycopg2-binary (driver de conexión)
- Flask-JWT-Extended (autenticación JWT, expira en 8h)
- bcrypt (hasheo de contraseñas)
- Flask-CORS (peticiones desde el frontend)
- ReportLab (generación de PDFs en memoria — reportes de ingresos, comprobantes)
- EasyOCR + OpenCV (reconocimiento de placas — **fase 2 / opcional**, aislado detrás del puerto `IPlateRecognizer`; la versión inicial usa entrada manual de placa)

### Pagos

- Stripe (SDK oficial de Python) — Checkout + webhooks para confirmar pagos de reserva y cobros por tiempo real

### Frontend

- React + Vite + TypeScript (sin Next.js, sin SSR)
- Tailwind CSS v4 (`@tailwindcss/vite`, directiva `@theme` para tokens de diseño)
- React Router (`react-router-dom`)
- TanStack Query (`@tanstack/react-query`) para fetching/cache contra la API Flask, usando `refetchInterval` para la actualización periódica del dashboard de ocupación (polling, en vez de WebSockets)

## Notas de planificación

- El reconocimiento de placas (EasyOCR/OpenCV) se implementa en una fase posterior; el flujo principal (reserva, ingreso/salida, cálculo de tarifa, pago) debe funcionar primero con entrada manual de placa.
- El dashboard de ocupación en tiempo real se resuelve con polling (`refetchInterval` de TanStack Query) en vez de WebSockets/Flask-SocketIO, para mantener el alcance acotado al tiempo del curso.
