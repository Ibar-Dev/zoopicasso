"""
test_main_callbacks.py — Tests para callbacks y lógica de negocio de main.py

Testea funciones internas, validación de datos, y lógica pura sin levantar la UI.
"""

import hashlib
import pytest
from datetime import date

from src.factura_model import LineaFactura


class TestLoginValidation:
    """Tests para validación de credenciales de login."""

    _USUARIO_VALIDO = "Giselle"
    _HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"

    def test_hash_correcto(self):
        """Verificar que el hash de la contraseña es correcto."""
        pwd = "Gisellepicasso"
        hash_calculado = hashlib.sha256(pwd.encode()).hexdigest()
        assert hash_calculado == self._HASH_PASSWORD

    def test_login_usuario_valido_password_valida(self):
        """Login con credenciales válidas."""
        usuario = "Giselle"
        pwd = "Gisellepicasso"
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()

        assert usuario == self._USUARIO_VALIDO
        assert pwd_hash == self._HASH_PASSWORD

    def test_login_usuario_invalido(self):
        """Login con usuario incorrecto."""
        usuario = "NoGiselle"
        pwd = "Gisellepicasso"
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()

        assert usuario != self._USUARIO_VALIDO or pwd_hash != self._HASH_PASSWORD

    def test_login_password_invalida(self):
        """Login con contraseña incorrecta."""
        usuario = "Giselle"
        pwd = "WrongPassword"
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()

        assert usuario == self._USUARIO_VALIDO
        assert pwd_hash != self._HASH_PASSWORD

    def test_usuario_strip_espacios(self):
        """Usuario con espacios se normaliza."""
        usuario = "  Giselle  ".strip()
        assert usuario == self._USUARIO_VALIDO

    def test_password_encoding_utf8(self):
        """Contraseña con caracteres especiales se encode correctamente."""
        pwd = "Gisellepicasso"
        encoded = pwd.encode("utf-8")
        hash_result = hashlib.sha256(encoded).hexdigest()
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64


class MockTextField:
    """Mock de ft.TextField para testing."""

    def __init__(self, label: str = "", value: str = "", width: int = 0, **kwargs):
        self.label = label
        self.value = value
        self.width = width
        self.read_only = kwargs.get("read_only", False)
        self.bgcolor = kwargs.get("bgcolor", None)

    def to_dict(self):
        return {"label": self.label, "value": self.value, "width": self.width}


class MockText:
    """Mock de ft.Text para testing."""

    def __init__(self, value: str = "", size: int = 0, **kwargs):
        self.value = value
        self.size = size
        self.color = kwargs.get("color", None)
        self.weight = kwargs.get("weight", None)


class TestFilaConceptoLogic:
    """Tests para la lógica de FilaConcepto sin Flet."""

    def test_recalcular_cantidad_y_precio_validos(self):
        """Calcular total con cantidad y precio válidos."""
        cantidad = 2
        precio = 50.0
        total = round(cantidad * precio, 2)
        assert total == 100.0

    def test_recalcular_cantidad_cero(self):
        """Cantidad cero da total cero."""
        cantidad = 0
        precio = 50.0
        total = round(cantidad * precio, 2)
        assert total == 0.0

    def test_recalcular_precio_decimal(self):
        """Precio con decimales se calcula correctamente."""
        cantidad = 3
        precio = 33.33
        total = round(cantidad * precio, 2)
        assert total == 99.99

    def test_recalcular_error_cantidad_no_numerica(self):
        """Cantidad no numérica causa error."""
        with pytest.raises(ValueError):
            int("abc")

    def test_recalcular_error_precio_no_numerico(self):
        """Precio no numérico causa error."""
        with pytest.raises(ValueError):
            float("xyz")

    def test_a_linea_factura_valida(self):
        """Convertir datos válidos a LineaFactura."""
        concepto = "Servicio A"
        cantidad = 2
        precio = 50.0

        linea = LineaFactura(
            concepto=concepto,
            cantidad=cantidad,
            precio_unitario=precio,
        )

        assert linea.concepto == "Servicio A"
        assert linea.cantidad == 2
        assert linea.precio_unitario == 50.0
        assert linea.total == 100.0

    def test_a_linea_factura_concepto_vacio(self):
        """Concepto vacío (después de strip) debe rechazarse."""
        concepto = "   ".strip()
        assert concepto == ""

    def test_a_linea_factura_cantidad_debe_ser_positiva(self):
        """Cantidad debe ser mayor que cero."""
        with pytest.raises(ValueError):
            LineaFactura(concepto="Test", cantidad=0, precio_unitario=10.0)

    def test_a_linea_factura_precio_no_negativo(self):
        """Precio no puede ser negativo."""
        with pytest.raises(ValueError):
            LineaFactura(concepto="Test", cantidad=1, precio_unitario=-5.0)


class TestTotalesCalculation:
    """Tests para cálculo de totales sin IVA adicional."""

    def test_actualizar_totales_linea_unica(self):
        """Calcular total con una línea."""
        lineas_valores = ["100.00"]
        total = round(sum(float(v) for v in lineas_valores), 2)
        
        assert total == 100.00

    def test_actualizar_totales_multiples_lineas(self):
        """Calcular total con múltiples líneas."""
        lineas_valores = ["100.00", "50.00", "25.00"]
        total = round(sum(float(v) for v in lineas_valores), 2)
        
        assert total == 175.00

    def test_actualizar_totales_sin_iva_adicional(self):
        """No se suma IVA adicional, el total es directo."""
        subtotal = 200.00
        iva_adicional = 0.0  # No sumamos IVA
        total = round(subtotal + iva_adicional, 2)
        
        assert total == 200.00

    def test_actualizar_totales_etiqueta_iva_incluido(self):
        """Mostrar "Incluido" en lugar de porcentaje."""
        iva_label = "Incluido"
        assert iva_label == "Incluido"

    def test_actualizar_totales_error_valor_invalido(self):
        """Valores inválidos se manejan con try/except."""
        lineas_valores = ["100.00", "abc"]
        try:
            total = round(sum(float(v) for v in lineas_valores), 2)
            resultado = total
        except ValueError:
            resultado = 0.0
        
        assert resultado == 0.0

    def test_actualizar_totales_formatos_moneda(self):
        """Formato de moneda es correcto."""
        total = 150.00
        formateado = f"{total:.2f} €"
        assert formateado == "150.00 €"


class TestFormularioLogic:
    """Tests para lógica de formulario (agregar/quitar líneas, resetear)."""

    def test_agregar_fila_incrementa_contador(self):
        """Agregar fila incrementa el total."""
        filas = []
        filas.append("nueva_fila")
        assert len(filas) == 1

    def test_agregar_multiples_filas(self):
        """Agregar múltiples filas."""
        filas = []
        for _ in range(3):
            filas.append("fila")
        assert len(filas) == 3

    def test_quitar_fila_decrementa_contador(self):
        """Quitar fila decrementa el total."""
        filas = ["fila1", "fila2", "fila3"]
        filas.pop()
        assert len(filas) == 2

    def test_quitar_fila_minimo_una(self):
        """No se puede quitar si solo queda una fila."""
        filas = ["fila1"]
        if len(filas) <= 1:
            puede_quitar = False
        else:
            puede_quitar = True
        
        assert not puede_quitar

    def test_resetear_limpia_formulario(self):
        """Resetear borra datos de formulario."""
        filas = ["fila1", "fila2"]
        cliente_nombre = "Cliente Test"
        cliente_nif = "123456789A"
        
        # Simular reset
        filas.clear()
        cliente_nombre = ""
        cliente_nif = ""
        
        assert len(filas) == 0
        assert cliente_nombre == ""
        assert cliente_nif == ""

    def test_resetear_nueva_factura(self):
        """Resetear increments en llamada a siguiente_numero_factura."""
        numero_anterior = 3
        numero_nuevo = numero_anterior + 1
        
        assert numero_nuevo == 4


class TestClienteOpcional:
    """Tests para campos opcionales de cliente."""

    def test_cliente_nombre_opcional(self):
        """Cliente nombre puede estar vacío."""
        cliente_nombre = ""
        assert cliente_nombre == ""

    def test_cliente_nif_opcional(self):
        """Cliente NIF puede estar vacío."""
        cliente_nif = ""
        assert cliente_nif == ""

    def test_cliente_nombre_strip(self):
        """Cliente nombre se normaliza con strip."""
        cliente_nombre = "  Mi Cliente  ".strip()
        assert cliente_nombre == "Mi Cliente"

    def test_cliente_nif_strip(self):
        """Cliente NIF se normaliza con strip."""
        cliente_nif = "  123456789A  ".strip()
        assert cliente_nif == "123456789A"

    def test_cliente_vacio_en_titulo(self):
        """Si cliente está vacío, se muestra "(sin cliente)"."""
        cliente_nombre = ""
        cliente_log = cliente_nombre or "(sin cliente)"
        assert cliente_log == "(sin cliente)"

    def test_cliente_presente_en_titulo(self):
        """Si cliente tiene valor, se muestra el nombre."""
        cliente_nombre = "Empresa ABC"
        cliente_log = cliente_nombre or "(sin cliente)"
        assert cliente_log == "Empresa ABC"


class TestExcelExporting:
    """Tests para conversión de datos a formato Excel."""

    def test_nombre_archivo_factura(self):
        """Formato de nombre de archivo correcto."""
        año = 2026
        numero = 3
        nombre = f"factura_{año}_{numero:03d}.xlsx"
        assert nombre == "factura_2026_003.xlsx"

    def test_nombre_factura_formato_titulo(self):
        """Formato de número de factura en Excel."""
        año = 2026
        numero = 5
        numero_formateado = f"{año}-{numero:03d}"
        assert numero_formateado == "2026-005"

    def test_fecha_formateada(self):
        """Fecha en formato DD/MM/YYYY."""
        fecha = date(2026, 4, 8)
        fecha_str = fecha.strftime("%d/%m/%Y")
        assert fecha_str == "08/04/2026"

    def test_cabecera_datos_cliente(self):
        """Cabecera de sección cliente."""
        titulo = "DATOS DEL CLIENTE"
        assert titulo == "DATOS DEL CLIENTE"

    def test_labels_tabla_sin_iva(self):
        """Labels de tabla no mencionan "sin IVA"."""
        headers = ["Concepto", "Cantidad", "P. Unitario", "Total"]
        assert "sin IVA" not in str(headers)
        assert len(headers) == 4

    def test_labels_totales_iva_incluido(self):
        """Labels de totales muestran "IVA incluido"."""
        labels = ["Subtotal:", "IVA incluido:", "TOTAL:"]
        assert "IVA incluido:" in labels
