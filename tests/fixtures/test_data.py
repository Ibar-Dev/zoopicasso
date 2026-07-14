"""
Datos de prueba para E2E tests
"""

# Categorías disponibles
CATEGORIES = ["perro", "gato", "Roedor", "ave", "peces", "reptiles", "peluqueria"]

# Métodos de pago
PAYMENT_METHODS = ["efectivo", "tarjeta", "mixto"]

# Datos para Test 1: Validación de formato de precio
TEST_DATA_VALIDATIONS = {
    "test_1_valid_prices": [
        {"precio": "25.50", "esperado": "aceptado"},
        {"precio": "25,50", "esperado": "aceptado"},
        {"precio": "100", "esperado": "aceptado"},
        {"precio": "0.99", "esperado": "aceptado"},
    ],
    "test_1_invalid_prices": [
        {"precio": "-25.50", "esperado": "rechazado"},
        {"precio": "25.999", "esperado": "rechazado"},  # 3 decimales
        {"precio": "abc", "esperado": "rechazado"},
        {"precio": "", "esperado": "rechazado"},
    ],
}

# Datos para Test 2: Validación de cantidad
TEST_DATA_QUANTITY = {
    "test_2_valid_quantities": [
        {"cantidad": 1, "esperado": "aceptado"},
        {"cantidad": 10, "esperado": "aceptado"},
        {"cantidad": 100, "esperado": "aceptado"},
    ],
    "test_2_invalid_quantities": [
        {"cantidad": 0, "esperado": "rechazado"},
        {"cantidad": -1, "esperado": "rechazado"},
        {"cantidad": 999999, "esperado": "rechazado"},  # Podría ser límite de negocio
    ],
}

# Datos para Tests 3-5: Validaciones simples
TEST_DATA_SIMPLE_VALIDATIONS = {
    "test_3_categoria_vacia": {
        "categoria": None,
        "cantidad": 1,
        "precio": "10.00",
        "esperado": "rechazado"
    },
    "test_4_cliente_vacio": {
        "cliente_nombre": "",
        "categoria": "perro",
        "cantidad": 1,
        "precio": "10.00",
        "esperado": "rechazado"
    },
    "test_5_multiple_validations": {
        "lineas": [
            {"categoria": "perro", "cantidad": 2, "precio": "15.50"},
            {"categoria": "gato", "cantidad": 1, "precio": "20.00"},
        ],
        "cliente": "Cliente Test",
        "metodo_pago": "efectivo",
        "esperado": "aceptado"
    }
}

# Datos para Tests 6-10: Cálculos
TEST_DATA_CALCULATIONS = {
    "test_6_simple": {
        "cantidad": 2,
        "precio": "10.00",
        "esperado_total": 20.00
    },
    "test_7_rounding": {
        "cantidad": 3,
        "precio": "10.01",
        "esperado_total": 30.03
    },
    "test_8_multiline": {
        "lineas": [
            {"cantidad": 2, "precio": "15.50"},  # 31.00
            {"cantidad": 1, "precio": "10.75"},  # 10.75
            {"cantidad": 3, "precio": "5.25"},   # 15.75
        ],
        "esperado_total": 57.50
    },
    "test_9_with_change": {
        "total": 45.50,
        "pagado": 50.00,
        "esperado_vuelto": 4.50
    },
    "test_10_high_precision": {
        "cantidad": 3,
        "precio": "33.33",
        "esperado_total": 99.99
    }
}

# Datos para Tests 11-15: Verificación en BD
TEST_DATA_DB_VERIFICATION = {
    "test_11_single_line_insert": {
        "categoria": "perro",
        "cantidad": 1,
        "precio": "25.00",
        "cliente": "Test Cliente 11",
        "usuario": "TEST_USER",
    },
    "test_12_incremental_counter": {
        "base_numero": "2024-100",
        "lineas": [
            {"categoria": "gato", "cantidad": 1, "precio": "15.00"},
        ]
    },
    "test_13_correct_storage": {
        "lineas": [
            {"categoria": "perro", "cantidad": 2, "precio": "20.00"},
            {"categoria": "gato", "cantidad": 1, "precio": "15.00"},
        ],
        "cliente": "Test Cliente 13",
        "total_esperado": 55.00
    },
    "test_14_resumen_update": {
        "lineas": [
            {"categoria": "perro", "cantidad": 1, "precio": "10.00"},
            {"categoria": "gato", "cantidad": 1, "precio": "20.00"},
        ],
        "esperado_por_categoria": {
            "perro": 10.00,
            "gato": 20.00
        }
    },
    "test_15_multiple_facturas": [
        {
            "lineas": [{"categoria": "perro", "cantidad": 1, "precio": "15.00"}],
            "total": 15.00
        },
        {
            "lineas": [{"categoria": "gato", "cantidad": 1, "precio": "20.00"}],
            "total": 20.00
        }
    ]
}

# Datos para edge cases (Tests 16-20)
TEST_DATA_EDGE_CASES = {
    "test_16_small_amounts": {
        "precio": "0.01",
        "cantidad": 1,
        "esperado_total": 0.01
    },
    "test_17_large_amounts": {
        "precio": "9999.99",
        "cantidad": 10,
        "esperado_total": 99999.90
    },
    "test_18_many_lines": {
        "num_lineas": 50,
        "precio_unitario": "10.50",
        "esperado_total": 525.00
    },
    "test_19_refund": {
        "total": 50.00,
        "pagado": 30.00,
        "estado": "credito",
        "esperado": -20.00
    },
    "test_20_mixed_decimals": {
        "lineas": [
            {"cantidad": 1, "precio": "10.1"},
            {"cantidad": 1, "precio": "20.2"},
            {"cantidad": 1, "precio": "30.3"},
        ],
        "esperado_total": 60.60
    }
}
