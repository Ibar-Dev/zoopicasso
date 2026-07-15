/**
 * Sistema Modular de Atajos de Teclado
 * 
 * Módulos:
 * 1. KeyNormalizer - Normaliza combinaciones de teclas
 * 2. ShortcutsRegistry - Definición centralizada de atajos
 * 3. ActionExecutor - Vinculación de acciones a funciones
 * 4. KeyboardDetector - Captura eventos y ejecuta acciones
 * 5. ConflictValidator - Valida y previene conflictos
 */

// ===== MÓDULO 1: KeyNormalizer =====
const KeyNormalizer = {
  /**
   * Normaliza un evento de teclado a una combinación legible
   * @param {KeyboardEvent} event
    * @returns {string} e.g., "Alt+A", "Ctrl+Alt+K", "Enter"
   */
  normalize(event) {
    const modifiers = [
      event.ctrlKey ? 'Ctrl' : '',
      event.altKey ? 'Alt' : '',
      event.shiftKey ? 'Shift' : '',
      event.metaKey ? 'Cmd' : ''
    ].filter(Boolean);

    // Teclas especiales que siempre se normalizan
    const specialKeyMap = {
      'Enter': 'Enter',
      'Escape': 'Escape',
      'Tab': 'Tab',
      ' ': 'Space',
      'ArrowUp': 'ArrowUp',
      'ArrowDown': 'ArrowDown',
      'ArrowLeft': 'ArrowLeft',
      'ArrowRight': 'ArrowRight',
      'Backspace': 'Backspace',
      'Delete': 'Delete'
    };

    const key = specialKeyMap[event.key] || event.key.toUpperCase();
    const combo = modifiers.length ? `${modifiers.join('+')}+${key}` : key;
    
    return combo;
  },

  /**
   * Normaliza una cadena de combinación para comparación
    * @param {string} combo e.g., "Alt+A", "e", "Ctrl+Alt+K"
   * @returns {string} versión normalizada
   */
  normalizeString(combo) {
    return combo
      .split('+')
      .map(part => {
        const trimmed = part.trim();
        if (['Ctrl', 'Alt', 'Shift', 'Cmd', 'Meta'].includes(trimmed)) {
          return trimmed;
        }
        return trimmed.toUpperCase();
      })
      .join('+');
  }
};

// ===== MÓDULO 2: ShortcutsRegistry =====
const ShortcutsRegistry = {
  /**
   * Configuración centralizada de atajos por contexto
   * Contextos: 'form', 'paymentModal', 'ticketModal', 'closureModal', 'searchPanel'
   */
  config: {
    'form': {
      'Ctrl+Alt+A': 'addLine',
      'Ctrl+Alt+D': 'deleteLine',
      'Ctrl+Alt+G': 'generateInvoice'
    },
    'paymentModal': {
      'E': 'selectEffectivo',
      'T': 'selectTarjeta',
      'M': 'selectMixto',
      'Enter': 'confirmPayment',
      'Escape': 'cancelPayment'
    },
    'ticketModal': {
      'Enter': 'printTicket',
      'N': 'skipPrinting',
      'Escape': 'cancelTicket'
    },
    'closureModal': {
      'Enter': 'confirmClosure',
      'Escape': 'cancelClosure'
    }
  },

  /**
   * Obtiene la acción para una combinación en un contexto
   * @param {string} context - contexto actual
   * @param {string} combo - combinación normalizada
   * @returns {string|null} nombre de acción o null
   */
  getAction(context, combo) {
    const contextShortcuts = this.config[context];
    if (!contextShortcuts) return null;
    
    // Búsqueda exacta (sensible a mayúsculas en algunos casos)
    return contextShortcuts[combo] || null;
  },

  /**
   * Obtiene todos los atajos de un contexto
   * @param {string} context
   * @returns {object} shortcuts del contexto
   */
  getContextShortcuts(context) {
    return this.config[context] || {};
  },

  /**
   * Lista todos los atajos registrados (para debugging)
   * @returns {object} estructura completa
   */
  listAll() {
    return this.config;
  }
};

// ===== MÓDULO 3: ActionExecutor =====
const ActionExecutor = {
  /**
   * Mapeo de nombres de acción a funciones concretas
   * Se define externamente pero aquí están las que se auto-vinculan
   */
  handlers: {},

  /**
   * Registra un handler para una acción
   * @param {string} actionName
   * @param {function} handler
   */
  register(actionName, handler) {
    if (typeof handler !== 'function') {
      console.warn(`Handler para '${actionName}' no es una función`);
      return;
    }
    this.handlers[actionName] = handler;
  },

  /**
   * Registra múltiples handlers
   * @param {object} handlersMap { 'actionName': function, ... }
   */
  registerMultiple(handlersMap) {
    for (const [action, handler] of Object.entries(handlersMap)) {
      this.register(action, handler);
    }
  },

  /**
   * Ejecuta una acción
   * @param {string} actionName
   * @returns {any} resultado de la ejecución
   */
  execute(actionName) {
    const handler = this.handlers[actionName];
    if (!handler) {
      console.warn(`No hay handler registrado para acción: '${actionName}'`);
      return null;
    }
    try {
      return handler();
    } catch (error) {
      console.error(`Error ejecutando acción '${actionName}':`, error);
      return null;
    }
  },

  /**
   * Lista todos los handlers registrados
   */
  listAll() {
    return Object.keys(this.handlers);
  }
};

// ===== MÓDULO 4: KeyboardDetector =====
const KeyboardDetector = {
  isActive: true,
  currentContext: 'form',

  /**
   * Contextos detectables automáticamente basados en elementos visibles
   */
  contextDetectors: {
    'paymentModal': () => {
      const modal = document.getElementById('pago-modal');
      return modal && !modal.hidden && modal.classList.contains('active');
    },
    'ticketModal': () => {
      const modal = document.getElementById('ticket-modal');
      return modal && !modal.hidden && modal.classList.contains('active');
    },
    'closureModal': () => {
      const modal = document.getElementById('modal-cierre');
      return modal && modal.style.display !== 'none' && modal.style.display !== '';
    },
    'searchPanel': () => {
      const panel = document.getElementById('panel-historial');
      return panel && !panel.hidden;
    }
  },

  /**
   * Detecta el contexto actual
   */
  detectContext() {
    for (const [context, detector] of Object.entries(this.contextDetectors)) {
      if (detector()) {
        this.currentContext = context;
        return context;
      }
    }
    this.currentContext = 'form';
    return 'form';
  },

  /**
   * Inicializa el detector
   */
  init() {
    document.addEventListener('keydown', (event) => {
      this.handleKeydown(event);
    });
  },

  /**
   * Manejador principal de keydown
   */
  handleKeydown(event) {
    if (!this.isActive) return;

    const context = this.detectContext();
    const combo = KeyNormalizer.normalize(event);
    const action = ShortcutsRegistry.getAction(context, combo);

    if (action) {
      event.preventDefault();
      ActionExecutor.execute(action);
    }
  },

  /**
   * Pausa el detector
   */
  pause() {
    this.isActive = false;
  },

  /**
   * Reanuda el detector
   */
  resume() {
    this.isActive = true;
  },

  /**
   * Obtiene contexto actual
   */
  getContext() {
    return this.currentContext;
  },

  /**
   * Debug: obtiene el atajo para una acción en un contexto
   */
  getShortcutFor(actionName, context = null) {
    const ctx = context || this.currentContext;
    const shortcuts = ShortcutsRegistry.getContextShortcuts(ctx);
    for (const [combo, action] of Object.entries(shortcuts)) {
      if (action === actionName) return combo;
    }
    return null;
  }
};

// ===== MÓDULO 5: ConflictValidator =====
const ConflictValidator = {
  /**
   * Valida la configuración de atajos
   * @param {object} config - ShortcutsRegistry.config
   * @returns {object} { valid: boolean, warnings: [], errors: [] }
   */
  validate(config) {
    const result = {
      valid: true,
      warnings: [],
      errors: []
    };

    const globalShortcuts = new Map(); // { 'combo': ['context1', 'context2'] }

    // Primer pase: recolectar todos los atajos
    for (const [context, shortcuts] of Object.entries(config)) {
      for (const [combo, action] of Object.entries(shortcuts)) {
        const normalized = KeyNormalizer.normalizeString(combo);

        if (!globalShortcuts.has(normalized)) {
          globalShortcuts.set(normalized, []);
        }
        globalShortcuts.get(normalized).push(context);
      }
    }

    // Segundo pase: detectar problemas
    for (const [combo, contexts] of globalShortcuts) {
      // Detectar duplicados dentro del MISMO contexto
      const contextCounts = {};
      for (const ctx of contexts) {
        contextCounts[ctx] = (contextCounts[ctx] || 0) + 1;
      }

      for (const [ctx, count] of Object.entries(contextCounts)) {
        if (count > 1) {
          result.errors.push(
            `❌ Duplicado: "${combo}" aparece ${count} veces en contexto "${ctx}"`
          );
          result.valid = false;
        }
      }

      // Advertencia: mismo atajo en múltiples contextos (podría ser intencional)
      if (contexts.length > 1 && new Set(contexts).size > 1) {
        result.warnings.push(
          `⚠️ "${combo}" está en múltiples contextos: [${contexts.join(', ')}] - ¿es intencional?`
        );
      }
    }

    return result;
  },

  /**
   * Valida y reporta
   */
  validateAndReport(config) {
    const result = this.validate(config);

    if (result.errors.length) {
      console.error('❌ ERRORES DE ATAJOS:');
      result.errors.forEach(err => console.error(err));
    }

    if (result.warnings.length) {
      console.warn('⚠️ ADVERTENCIAS DE ATAJOS:');
      result.warnings.forEach(warn => console.warn(warn));
    }

    if (!result.valid) {
      throw new Error('Conflictos críticos en configuración de atajos');
    }

    console.log('✅ Configuración de atajos válida');
    return result;
  }
};

// ===== API PÚBLICA =====
const KeyboardSystem = {
  /**
   * Inicializa el sistema completo
   * @param {object} config - ShortcutsRegistry.config personalizada (opcional)
   * @param {object} handlers - ActionExecutor.handlers personalizados (opcional)
   */
  init(config = null, handlers = null) {
    // Validar configuración
    const configToUse = config || ShortcutsRegistry.config;
    ConflictValidator.validateAndReport(configToUse);

    // Registrar handlers
    if (handlers) {
      ActionExecutor.registerMultiple(handlers);
    }

    // Iniciar detector
    KeyboardDetector.init();

    console.log('✅ Sistema de atajos inicializado');
    console.log('📋 Atajos disponibles:', ShortcutsRegistry.listAll());
    console.log('📝 Handlers registrados:', ActionExecutor.listAll());
  },

  /**
   * Pausa temporalmente
   */
  pause: () => KeyboardDetector.pause(),

  /**
   * Reanuda
   */
  resume: () => KeyboardDetector.resume(),

  /**
   * Obtiene contexto actual
   */
  getContext: () => KeyboardDetector.getContext(),

  /**
   * Debug: lista todos los atajos
   */
  listShortcuts: () => ShortcutsRegistry.listAll(),

  /**
   * Debug: lista todos los handlers
   */
  listHandlers: () => ActionExecutor.listAll(),

  /**
   * Debug: obtiene atajo para una acción
   */
  getShortcutFor: (action, context = null) => 
    KeyboardDetector.getShortcutFor(action, context)
};

// Exportar si está en módulo, sino espera a que se inicialice
if (typeof module !== 'undefined' && module.exports) {
  module.exports = KeyboardSystem;
}
