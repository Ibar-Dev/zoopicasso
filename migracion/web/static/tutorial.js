class TutorialManager {
  constructor() {
    this._KEY = 'tutorial_zoo_picasso';
    this._VERSION = '1.0';
    this._d = null;
    this._terminado = false;
  }

  _leer() {
    try {
      return JSON.parse(localStorage.getItem(this._KEY) || '{}');
    } catch {
      return {};
    }
  }

  _guardar(estado) {
    try {
      localStorage.setItem(this._KEY, JSON.stringify({ estado, version: this._VERSION }));
    } catch {}
  }

  checkAutoStart() {
    const { estado, version } = this._leer();
    // No iniciar si hay un modal abierto
    if (document.querySelector('.modal-backdrop.active')) return;
    // No iniciar si ya fue completado o descartado en esta versión
    const yaVisto = (estado === 'completado' || estado === 'descartado') && version === this._VERSION;
    if (yaVisto) return;
    setTimeout(() => this.start(), 600);
  }

  start(desde = 0) {
    if (typeof window.driver === 'undefined') return;
    const pasos = window.TUTORIAL_PASOS;
    if (!pasos || !pasos.length) return;

    this._terminado = false;
    const self = this;

    // Marcar el último paso con hook de "finalizado"
    const pasosConHook = pasos.map((p, i) => {
      if (i < pasos.length - 1) return p;
      return {
        ...p,
        popover: {
          ...p.popover,
          onNextClick: () => {
            self._terminado = true;
            self._d.destroy();
          },
        },
      };
    });

    this._d = window.driver({
      showProgress: true,
      allowClose: true,
      overlayOpacity: 0.35,
      stagePadding: 8,
      stageRadius: 12,
      nextBtnText: 'Siguiente →',
      prevBtnText: '← Anterior',
      doneBtnText: '¡Entendido!',
      steps: pasosConHook,
      onDestroyed: () => {
        if (self._terminado) self._guardar('completado');
        self._d = null;
      },
    });

    this._d.drive(desde);
  }

  descartarPermanentemente() {
    this._guardar('descartado');
    if (this._d) this._d.destroy();
  }

  reactivar() {
    this._guardar('pendiente');
    this.start();
  }
}

const tutorialManager = new TutorialManager();
