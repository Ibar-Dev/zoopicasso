/**
 * Keep-Alive Manager v2.0 (Opción C - Incondicional cada 5 minutos)
 * 
 * Mantiene activo el servidor con pings automáticos cada 5 minutos
 * Solución para prevenir spin-down en Render Free tier
 * 
 * Características:
 * - Ping incondicional cada 5 minutos (no verifica inactividad)
 * - Módulo independiente y reutilizable
 * - Logging en consola para debugging
 * - Endpoint sin autenticación: /api/keep-alive
 * - Confiable y eficiente
 * 
 * Uso:
 *   <script src="/static/keep-alive.js"></script>
 *   <script>KeepAliveManager.start();</script>
 * 
 * O automático si se carga antes de cerrar body:
 *   KeepAliveManager.start();
 */

const KeepAliveManager = {
  // ===== CONFIGURACIÓN =====
  pingInterval: 5 * 60 * 1000,  // 5 minutos (300,000 ms)
  endpoint: '/api/keep-alive',
  
  // ===== ESTADO INTERNO =====
  timer: null,
  pingCount: 0,
  lastPingTime: null,
  failureCount: 0,
  lastError: null,

  /**
   * Inicia el sistema de keep-alive
   * Se ejecuta automáticamente al cargar la página
   */
  start() {
    // Evitar múltiples inicios
    if (this.timer !== null) {
      console.warn('⚠️ Keep-alive ya está activo');
      return;
    }

    // Hacer ping cada 5 minutos, incondicional
    this.timer = setInterval(() => {
      this.sendPing();
    }, this.pingInterval);
    
    // Log inicial
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║ ✅ Keep-alive Manager iniciado (Opción C)                 ║');
    console.log('╠════════════════════════════════════════════════════════════╣');
    console.log('║ Intervalo:    5 minutos (300 segundos)                     ║');
    console.log('║ Endpoint:     /api/keep-alive (GET, sin autenticación)     ║');
    console.log('║ Modo:         Incondicional (siempre, sin condiciones)     ║');
    console.log('║ Objetivo:     Prevenir spin-down de servidor Render Free   ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
  },

  /**
   * Envía un ping al servidor
   * Se ejecuta automáticamente cada 5 minutos
   */
  sendPing() {
    this.pingCount++;
    const timestamp = new Date().toLocaleTimeString('es-ES');
    const isoTime = new Date().toISOString();
    this.lastPingTime = isoTime;
    
    fetch(this.endpoint, { 
      method: 'GET',
      credentials: 'same-origin'
    })
    .then(res => {
      if (res.ok) {
        this.failureCount = 0;  // Reset en caso de éxito
        console.log(`[${timestamp}] ✓ Keep-alive ping #${this.pingCount} (OK)`);
        return res.json();
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    })
    .catch(error => {
      this.failureCount++;
      this.lastError = error.message;
      const level = this.failureCount <= 3 ? '⚠️' : '❌';
      console.warn(`[${timestamp}] ${level} Keep-alive ping #${this.pingCount} falló: ${error.message}`);
      
      // Si falla 5 veces seguidas, log más visible
      if (this.failureCount === 5) {
        console.error('🔴 Keep-alive falló 5 veces consecutivas. Revisar conexión.');
      }
    });
  },

  /**
   * Detiene el sistema de keep-alive
   * Útil para cleanup o debugging
   */
  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
      console.log('⏸️ Keep-alive Manager detenido');
    }
  },

  /**
   * Retorna estado actual del keep-alive
   * Útil para debugging y monitoreo
   * 
   * Uso en consola:
   *   KeepAliveManager.getStatus()
   */
  getStatus() {
    return {
      active: this.timer !== null,
      pingsSent: this.pingCount,
      failureCount: this.failureCount,
      lastError: this.lastError,
      lastPing: this.lastPingTime,
      interval: this.pingInterval,
      intervalSeconds: this.pingInterval / 1000,
      endpoint: this.endpoint,
      uptime: this.calculateUptime()
    };
  },

  /**
   * Calcula el uptime desde que se inició el manager
   */
  calculateUptime() {
    if (this.pingCount === 0) return '0 minutos';
    const totalMinutes = (this.pingCount - 1) * 5;
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    
    if (hours === 0) return `${minutes} minutos`;
    return `${hours}h ${minutes}m`;
  },

  /**
   * Fuerza un ping inmediato (para testing)
   * Uso: KeepAliveManager.forcePing()
   */
  forcePing() {
    console.log('🔄 Forzando ping inmediato...');
    this.sendPing();
  },

  /**
   * Cambia el intervalo de ping (en minutos)
   * Uso: KeepAliveManager.setInterval(3) // Cada 3 minutos
   */
  setInterval(minutes) {
    const newInterval = minutes * 60 * 1000;
    this.pingInterval = newInterval;
    
    // Reiniciar el timer con el nuevo intervalo
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = setInterval(() => {
        this.sendPing();
      }, this.pingInterval);
      
      console.log(`✅ Intervalo de keep-alive actualizado a ${minutes} minutos`);
    }
  },

  /**
   * Retorna información detallada para debugging
   */
  getDebugInfo() {
    return {
      version: '2.0 (Opción C)',
      status: this.getStatus(),
      config: {
        pingInterval: this.pingInterval,
        endpoint: this.endpoint,
        mode: 'Incondicional'
      },
      stats: {
        totalPings: this.pingCount,
        failures: this.failureCount,
        successRate: this.pingCount > 0 ? 
          `${Math.round((this.pingCount - this.failureCount) / this.pingCount * 100)}%` : 'N/A'
      }
    };
  }
};

// Exportar para uso en otros módulos (si es necesario)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = KeepAliveManager;
}
