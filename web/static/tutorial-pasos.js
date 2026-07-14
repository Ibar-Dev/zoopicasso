window.TUTORIAL_PASOS = [
  {
    element: '#app-card',
    popover: {
      title: '¡Bienvenida a Zoo Picasso!',
      description: 'Esta guía te muestra las funciones principales. Podés navegar con los botones o cerrarla cuando quieras.',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    element: '#cliente_nombre',
    popover: {
      title: 'Datos del cliente',
      description: 'Nombre y NIF del cliente — ambos opcionales. Si los dejás en blanco, la factura se genera sin datos de cliente.',
      side: 'bottom',
    },
  },
  {
    element: '#btn-add',
    popover: {
      title: 'Añadir líneas',
      description: 'Cada línea es un producto o servicio. Usá este botón o el atajo <strong>Ctrl+Shift+A</strong> para añadir una nueva línea.',
      side: 'bottom',
    },
  },
  {
    element: '#lineas',
    popover: {
      title: 'Líneas de factura',
      description: 'Por cada línea: escribí el concepto (o elegí uno sugerido), la cantidad, el precio unitario y la categoría del animal. El total parcial se calcula solo.',
      side: 'bottom',
    },
  },
  {
    element: '#btn-generar',
    popover: {
      title: 'Generar factura',
      description: 'Cuando las líneas estén completas, este botón abre el selector de método de pago (efectivo, tarjeta o mixto) y genera el Excel.',
      side: 'top',
    },
  },
  {
    element: '#acumulado-hoy',
    popover: {
      title: 'Resumen del mes',
      description: 'Acumulado total de ventas del mes en curso. Se actualiza automáticamente con cada factura generada.',
      side: 'left',
    },
  },
  {
    element: '#ajuste',
    popover: {
      title: 'Ajuste manual',
      description: 'Para descontar un importe del total mensual (devoluciones, correcciones): ingresá el monto y pulsá <strong>Restar</strong>.',
      side: 'top',
    },
  },
  {
    element: '#btn-cerrar-mes',
    popover: {
      title: 'Cierre mensual',
      description: 'Al final del mes, este botón genera el Excel con todas las ventas y reinicia los contadores. <strong>Hacerlo una vez por mes.</strong>',
      side: 'top',
    },
  },
  {
    element: '#btn-carpeta-cierres',
    popover: {
      title: 'Carpeta de cierres',
      description: 'Configurá la carpeta donde se guardarán los Excels de cierre mensual. Hacelo antes de tu primer cierre para evitar que el navegador te lo pida en el momento.<br><br><small>Podés volver a ver esta guía en cualquier momento pulsando el botón <strong>?</strong> del encabezado.</small>',
      side: 'top',
    },
  },
];
