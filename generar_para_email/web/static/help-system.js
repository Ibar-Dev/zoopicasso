/**
 * Help System v1.0 - FASE 2 UX Modular
 * 
 * Sistema de ayuda no-intrusivo con tooltips contextuales.
 * - Permite al usuario hacer hover en "?" para ver qué hace cada elemento
 * - Sin interrupciones (no auto-start)
 * - Tooltips pequeños y elegantes
 * 
 * Uso: 
 *   1. En HTML: <button data-help="Descripción de ayuda">Mi Botón</button>
 *   2. El script automáticamente crea el tooltip
 */

const HelpSystem = {
  _initialized: false,
  _tooltips: new Map(),

  /**
   * Configuración de tooltips por elemento
   * Format: selector -> { text: "...", position: "top|bottom" }
   */
  _config: {
    '#btn-carpeta': {
      text: '📁 Selecciona dónde guardar los Excels de cierre y facturas',
      position: 'bottom'
    },
    '#btn-add': {
      text: '➕ Agrega una línea de producto. Atajo: Alt+A',
      position: 'bottom'
    },
    '#btn-generar': {
      text: '✅ Genera la factura Excel. Atajo: Alt+G',
      position: 'top'
    },
    '#btn-cierre-manana': {
      text: '🌅 Cierre de la mañana (06:00-14:00). Disponible siempre.',
      position: 'top'
    },
    '#btn-cierre-tarde': {
      text: '🌆 Cierre de la tarde (14:00-22:00). Requiere Mañana completada HOY.',
      position: 'top'
    },
    '#btn-cierre-dia-completo': {
      text: '📅 Cierre del día completo (06:00-22:00). Requiere Mañana Y Tarde completadas HOY.',
      position: 'top'
    },
    '.automation-pause-btn': {
      text: '⏸️ Pausa los cierres automáticos (los jobs siguen ejecutándose pero sin hacer acciones).',
      position: 'top'
    },
    '.automation-resume-btn': {
      text: '▶️ Reanuda los cierres automáticos (vuelven a ejecutar sus acciones).',
      position: 'top'
    },
    '#btn-tutorial': {
      text: '📖 Inicia el tutorial completo paso a paso (sin interrupciones)',
      position: 'left'
    }
  },

  /**
   * Inicializa el sistema de ayuda
   */
  init() {
    if (this._initialized) return;
    this._initialized = true;

    // Procesar todos los elementos con data-help o que están en _config
    this._setupTooltipsFromConfig();
    this._setupTooltipsFromDataAttribute();

    console.log('✅ Help System inicializado (FASE 2 UX Modular)');
  },

  /**
   * Configura tooltips desde _config
   */
  _setupTooltipsFromConfig() {
    for (const [selector, config] of Object.entries(this._config)) {
      const elements = document.querySelectorAll(selector);
      elements.forEach(el => {
        this._attachTooltip(el, config.text, config.position);
      });
    }
  },

  /**
   * Configura tooltips desde atributo data-help en HTML
   */
  _setupTooltipsFromDataAttribute() {
    document.querySelectorAll('[data-help]').forEach(el => {
      const text = el.getAttribute('data-help');
      const position = el.getAttribute('data-help-pos') || 'bottom';
      this._attachTooltip(el, text, position);
    });
  },

  /**
   * Adjunta un tooltip a un elemento
   */
  _attachTooltip(element, text, position = 'bottom') {
    // Si el elemento no existe, skip
    if (!element) return;

    // Crear wrapper si es necesario
    let wrapper = element.parentElement;
    if (!wrapper.classList.contains('button-with-help')) {
      // Envolver el elemento
      const newWrapper = document.createElement('span');
      newWrapper.className = 'button-with-help';
      element.parentNode.insertBefore(newWrapper, element);
      newWrapper.appendChild(element);
      wrapper = newWrapper;
    }

    // Crear el tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip-popover';
    tooltip.textContent = text;
    tooltip.setAttribute('data-position', position);
    wrapper.appendChild(tooltip);

    // Event listeners
    element.addEventListener('mouseenter', (e) => {
      this._positionTooltip(tooltip, element, position);
      tooltip.classList.add('visible');
    });

    element.addEventListener('mouseleave', () => {
      tooltip.classList.remove('visible');
    });

    // Guardar referencia
    this._tooltips.set(element, tooltip);
  },

  /**
   * Posiciona el tooltip relativo al elemento
   */
  _positionTooltip(tooltip, element, position) {
    // Forzar visible temporalmente para medir
    tooltip.style.visibility = 'hidden';
    tooltip.classList.add('visible');

    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const gap = 12;

    let top, left;

    if (position === 'top') {
      top = rect.top - tooltipRect.height - gap;
      left = rect.left + rect.width / 2 - tooltipRect.width / 2;
    } else if (position === 'bottom') {
      top = rect.bottom + gap;
      left = rect.left + rect.width / 2 - tooltipRect.width / 2;
    } else if (position === 'left') {
      top = rect.top + rect.height / 2 - tooltipRect.height / 2;
      left = rect.left - tooltipRect.width - gap;
    } else if (position === 'right') {
      top = rect.top + rect.height / 2 - tooltipRect.height / 2;
      left = rect.right + gap;
    }

    // Ajustes para no salirse de la pantalla
    const padding = 8;
    if (left < padding) left = padding;
    if (left + tooltipRect.width > window.innerWidth - padding) {
      left = window.innerWidth - tooltipRect.width - padding;
    }
    if (top < padding) {
      top = position === 'top' ? rect.bottom + gap : padding;
    }

    tooltip.style.position = 'fixed';
    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
    tooltip.style.visibility = 'visible';
  },

  /**
   * Obtener tooltip de un elemento
   */
  getTooltip(element) {
    return this._tooltips.get(element);
  },

  /**
   * Forzar mostrar tooltip (para debugging)
   */
  showTooltip(selector) {
    const element = document.querySelector(selector);
    if (element) {
      const tooltip = this._tooltips.get(element);
      if (tooltip) {
        this._positionTooltip(tooltip, element, tooltip.getAttribute('data-position'));
        tooltip.classList.add('visible');
      }
    }
  },

  /**
   * Ocultar todos los tooltips
   */
  hideAll() {
    this._tooltips.forEach(tooltip => {
      tooltip.classList.remove('visible');
    });
  }
};

// Auto-inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => HelpSystem.init(), 100);
  });
} else {
  setTimeout(() => HelpSystem.init(), 100);
}
