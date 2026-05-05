# Manual de usuario — Zoo Picasso · Facturación Web

> Versión actual · última actualización: mayo 2026

---

## Tabla de contenidos

1. [¿Qué hace esta aplicación?](#1-qué-hace-esta-aplicación)
2. [Acceso e inicio de sesión](#2-acceso-e-inicio-de-sesión)
3. [Generar una factura](#3-generar-una-factura)
4. [Métodos de pago](#4-métodos-de-pago)
5. [Impresión de ticket térmico](#5-impresión-de-ticket-térmico)
6. [Seguimiento de ganancias del mes](#6-seguimiento-de-ganancias-del-mes)
7. [Ajuste manual del acumulado](#7-ajuste-manual-del-acumulado)
8. [Cierre mensual](#8-cierre-mensual)
9. [Precios por categoría](#9-precios-por-categoría)
10. [Configurar carpeta de destino](#10-configurar-carpeta-de-destino)
11. [Referencia de atajos de teclado](#11-referencia-de-atajos-de-teclado)
12. [Preguntas frecuentes](#12-preguntas-frecuentes)

---

## 1. ¿Qué hace esta aplicación?

Zoo Picasso Facturación es una aplicación web diseñada para agilizar el proceso de cobro en el negocio. Permite:

- Crear facturas en Excel con los datos del negocio ya rellenados.
- Registrar el método de pago (efectivo, tarjeta o mixto) y calcular el cambio automáticamente.
- Generar e imprimir tickets térmicos.
- Hacer un seguimiento de las ventas y ganancias acumuladas del mes.
- Generar un informe Excel de cierre al terminar cada mes.

---

## 2. Acceso e inicio de sesión

Al abrir la aplicación se muestra la pantalla de inicio de sesión.

1. Introduce el **usuario** y la **contraseña**.
2. Pulsa **Entrar** o la tecla `Enter`.

Si los datos son incorrectos aparece un mensaje de error en rojo. Contacta con el administrador si no recuerdas la contraseña.

Para cerrar sesión pulsa el botón **Salir** en la esquina superior derecha.

---

## 3. Generar una factura

El flujo habitual de cobro consta de tres pasos rápidos:

### Paso 1 — Rellenar los datos del cliente (opcional)

Los campos **Nombre del cliente** y **NIF** son opcionales. Si el cliente no necesita factura nominativa, puedes dejarlos en blanco.

### Paso 2 — Añadir las líneas de la factura

1. Pulsa **+ Añadir línea** (o `Alt`+`A`).
2. Rellena cada línea (en el orden en que aparecen los campos):
   - **Concepto** — descripción del servicio o producto.
   - **Cantidad** — número de unidades.
   - **Precio unitario** — precio por unidad en euros (campo con el símbolo €).
   - **Categoría** — selecciona el tipo de animal o servicio (perro, gato, peluquería, etc.).
3. El **Total** se actualiza automáticamente en tiempo real.
4. Repite el paso si hay más de un servicio en el mismo cobro.

Para eliminar una línea pulsa la **✕** a la derecha de cada fila.

### Paso 3 — Generar

Pulsa **Generar factura** (o `Alt`+`G`).

Se abrirán dos ventanas en secuencia:

1. **Modal de pago** — elige el método y confirma el importe.
2. **Modal de ticket** — decide si imprimir ticket térmico.

Cuando ambos se confirman, la factura en Excel se descarga automáticamente en la carpeta configurada (o en la carpeta de Descargas por defecto).

---

## 4. Métodos de pago

Al pulsar «Generar factura» se abre el modal de pago. Dispones de tres opciones:

### Efectivo

1. Selecciona **Efectivo** (o pulsa `E`).
2. El campo «Monto en efectivo» se rellena solo con el total.
3. Introduce el **efectivo entregado** por el cliente.
4. El cambio a devolver se calcula y muestra automáticamente.
5. Pulsa **Aceptar** o `Enter` para confirmar.

### Tarjeta

1. Selecciona **Tarjeta** (o pulsa `T`).
2. El importe se rellena automáticamente con el total.
3. Pulsa **Aceptar** o `Enter` — no hay cambio.

> Con tarjeta, el flujo más rápido es: abrir modal → pulsar `T` → pulsar `Enter`. Dos teclas.

### Mixto (parte en efectivo, parte en tarjeta)

1. Selecciona **Mixto** (o pulsa `M`).
2. Indica cuánto paga el cliente **en efectivo** y cuánto **en tarjeta**.
3. La suma de ambos debe ser igual al total de la factura.
4. Introduce el efectivo entregado para calcular el cambio.
5. Pulsa **Aceptar** o `Enter`.

Si los importes no cuadran, aparece un mensaje de error en rojo y no se puede confirmar hasta corregirlos.

---

## 5. Impresión de ticket térmico

Tras confirmar el pago aparece el modal de ticket.

| Opción | Acción |
|--------|--------|
| **Sí, imprimir** o `Enter` | Envía el ticket a la impresora térmica conectada |
| **No imprimir** o `N` | Continúa sin imprimir |
| **Cancelar** o `Esc` | Vuelve al modal de pago |

El botón «Sí, imprimir» recibe el foco automáticamente al abrir el modal, por lo que en la mayoría de cobros basta con pulsar `Enter` una sola vez para imprimir.

---

## 6. Seguimiento de ganancias del mes

Debajo de los botones principales se muestran dos contadores actualizados en tiempo real:

| Contador | Significado |
|----------|-------------|
| **Ventas activas del mes** | Número de facturas generadas en el mes actual |
| **Ganancias del mes** | Suma total de todas las facturas del mes (IVA incluido) |

Estos valores se acumulan con cada factura generada y se ponen a cero al hacer el cierre mensual.

---

## 7. Ajuste manual del acumulado

Si necesitas restar una cantidad del acumulado (devolución, corrección, etc.):

1. Introduce el importe a restar en el campo **Ajuste Manual**.
2. Pulsa **Restar** o la tecla `Enter` dentro del campo.

El ajuste queda registrado y el acumulado se actualiza inmediatamente.

---

## 8. Cierre mensual

Al terminar el mes hay que realizar el cierre para reiniciar los contadores y guardar un informe en Excel con el resumen de ventas.

### Configurar la carpeta de destino (solo la primera vez)

1. Pulsa el botón **📁 Cierres** junto al botón «Cerrar mes».
2. Se abre el selector de carpetas del sistema operativo.
3. Elige la carpeta donde quieres guardar los informes mensuales.
4. La carpeta queda recordada para todos los cierres futuros — su nombre aparece en el `tooltip` del botón.

> En Firefox, la selección de carpeta no está disponible. El archivo se descargará automáticamente en la carpeta de Descargas del navegador.

### Realizar el cierre

1. Pulsa **Cerrar mes**.
2. Lee el aviso de confirmación — **esta acción no se puede deshacer**.
3. Pulsa **Sí, Cerrar Mes**.
4. Se genera el informe Excel `cierre_mensual_AAAA_MM.xlsx` y se guarda en la carpeta configurada.
5. Los contadores del mes quedan a cero.

El informe Excel incluye:
- Periodo del cierre.
- Número total de ventas y suma total.
- Desglose por categoría de animal / servicio.

---

## 9. Precios por categoría

En la sección **Ventas del día por categoría** (parte derecha del formulario) puedes ver dos cosas:

- **Total (€)** — acumulado de ventas de esa categoría en el día, actualizado con cada factura.
- **Precio unitario (€)** — precio de referencia configurable para cada categoría.

### Cómo configurar los precios de referencia

1. Introduce el precio unitario deseado en la columna **Precio unitario (€)** de cada categoría.
2. Pulsa **Guardar precios categorías**.
3. Aparece un diálogo de confirmación — pulsa **Aceptar** para guardar.

> Los precios de referencia son solo informativos y se muestran en esta tabla. Al añadir una nueva línea de factura deberás introducir el precio manualmente en el campo correspondiente.

Las categorías disponibles son: Perro, Gato, Conejo, Ave, Peces, Reptiles y Peluquería.

---

## 10. Configurar carpeta de destino

### Carpeta de facturas

Las facturas Excel generadas se guardan en la carpeta que elijas:

1. Pulsa el botón **📁 Carpeta** en la esquina superior derecha.
2. Selecciona la carpeta en el explorador del sistema.
3. Queda recordada para todas las facturas siguientes.

Si no configuras ninguna carpeta, la primera vez que generes una factura se te pedirá que elijas una.

### Carpeta de cierres

Los informes de cierre mensual van a una carpeta separada. Consulta la sección [Cierre mensual](#8-cierre-mensual) para configurarla.

---

## 11. Referencia de atajos de teclado

### Formulario principal

| Tecla | Acción |
|-------|--------|
| `Alt` + `A` | Añadir nueva línea |
| `Alt` + `G` | Generar factura (abre el modal de pago) |

### Modal de pago

| Tecla | Acción |
|-------|--------|
| `E` | Seleccionar **Efectivo** y rellenar el importe automáticamente |
| `T` | Seleccionar **Tarjeta** y rellenar el importe automáticamente |
| `M` | Seleccionar **Mixto** |
| `Enter` | Confirmar el pago |
| `Esc` | Cancelar y volver al formulario |

> Los atajos `E`, `T` y `M` no se activan si el cursor está dentro de un campo de texto, para no interferir al escribir importes.

### Modal de ticket

| Tecla | Acción |
|-------|--------|
| `Enter` | Sí, imprimir |
| `N` | No imprimir |
| `Esc` | Cancelar |

### Flujo más rápido: cobro con tarjeta

```
Alt+G  →  T  →  Enter  →  Enter
```

1. `Alt+G` — abre el modal de pago.
2. `T` — selecciona tarjeta y rellena el total.
3. `Enter` — confirma el pago.
4. `Enter` — imprime el ticket.

Cuatro teclas desde el formulario hasta la factura generada.

---

## 12. Preguntas frecuentes

**¿Puedo generar una factura sin nombre de cliente?**
Sí. Los campos «Nombre» y «NIF» son opcionales. La factura se genera igualmente.

**¿Qué pasa si me equivoco en el importe de efectivo?**
Si el efectivo entregado es menor que el total, la aplicación muestra un error y no permite confirmar. Corrígelo antes de continuar.

**¿Puedo hacer varias facturas seguidas sin recargar?**
Sí. Después de cada factura el formulario se vacía automáticamente y puedes empezar el siguiente cobro de inmediato.

**¿Dónde se guarda la factura Excel?**
En la carpeta que hayas configurado con el botón **📁 Carpeta**. Si no configuraste ninguna, el navegador te pedirá que elijas una la primera vez.

**¿El cierre mensual borra las facturas generadas?**
No borra los archivos Excel. Lo que hace es archivar internamente los registros de ventas y poner los contadores del mes a cero. Los archivos Excel de facturas permanecen en tu carpeta.

**¿Qué navegador debo usar?**
Se recomienda **Google Chrome** o **Microsoft Edge** para tener todas las funciones disponibles, incluida la selección de carpeta de destino. Firefox funciona correctamente pero descarga los archivos en la carpeta de Descargas predeterminada sin permitir elegir carpeta.

**¿Puedo usar la aplicación desde el móvil?**
La aplicación funciona en el navegador del móvil, pero los atajos de teclado no están disponibles en dispositivos táctiles. Se recomienda usarla desde un ordenador de escritorio o portátil.
