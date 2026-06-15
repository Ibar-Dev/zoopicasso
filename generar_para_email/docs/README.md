# 📋 MANUAL DE CIERRES - Zoo Picasso

## 📁 Archivos en esta carpeta

### 1. `MANUAL_CIERRES_CLIENTA.pdf` ⭐
**El archivo principal - ESTO ES LO QUE ENVÍAS A LA CLIENTA**

- Formato: PDF profesional
- Tamaño: ~29 KB
- Audiencia: Operadores, Gerentes, Administradores
- Idioma: Español
- Imprimible: Sí ✅

**Contenido:**
- Introducción a los cierres
- Explicación de los 4 tipos de cierres
- Guía paso a paso para cada cierre
- Ejemplos prácticos con números
- Diagramas visuales del flujo
- Preguntas frecuentes
- Resolución de problemas
- Buenas prácticas

---

### 2. `MANUAL_CIERRES_CLIENTA.md`
**Archivo fuente en Markdown**

- Formato: Markdown plano (texto)
- Útil para: Editar, versionar, actualizar
- Ubicación: Para documentación del proyecto

Si necesitas actualizar el manual:
1. Edita este archivo `.md`
2. Ejecuta `generate_pdf.py` para regenerar el PDF
3. Distribuye el nuevo PDF

---

### 3. `generate_pdf.py`
**Script para generar PDF desde Markdown**

- Convierte automáticamente `.md` → `.pdf`
- Aplica estilos profesionales (colores, fuentes)
- Genera tablas, códigos, advertencias

**Cómo usar:**
```bash
cd generar_para_email
.venv_new/bin/python docs/generate_pdf.py
```

---

## 📤 Cómo distribuir el manual

### Opción 1: Email a la clienta
```
Asunto: "Guía de Cierres - Zoo Picasso"

Adjunto: MANUAL_CIERRES_CLIENTA.pdf

Cuerpo del email:
"Hola [Nombre clienta],

Adjunto encontrarás la guía completa sobre cómo
hacer cierres en el sistema. Este manual explica 
paso a paso cada tipo de cierre.

Si tienes preguntas, no dudes en contactarme.

Saludos,
[Tu nombre]"
```

### Opción 2: Imprimir
- Abrir PDF con Acrobat Reader o navegador
- Imprimir (configuración: B&N o color)
- Entregar en mano

### Opción 3: En el sistema
- Subir PDF a una sección "Documentación" del sistema
- Mostrar a operadores dónde descargarlo

---

## ✅ Verificación del manual

- ✅ Lenguaje claro (sin jerga técnica)
- ✅ Pasos numerados y accionables
- ✅ Ejemplos con números reales
- ✅ Diagramas visuales del flujo
- ✅ Diferencia clara entre cierres diarios y mensual
- ✅ Advertencias sobre irreversibilidad
- ✅ Preguntas frecuentes incluidas
- ✅ Resolución de problemas
- ✅ Formato profesional PDF

---

## 🔄 Actualizar el manual

Si necesitas hacer cambios:

1. **Editar el Markdown:**
   ```bash
   nano docs/MANUAL_CIERRES_CLIENTA.md
   ```

2. **Regenerar el PDF:**
   ```bash
   cd generar_para_email
   .venv_new/bin/python docs/generate_pdf.py
   ```

3. **Verificar resultado:**
   ```bash
   file docs/MANUAL_CIERRES_CLIENTA.pdf
   du -h docs/MANUAL_CIERRES_CLIENTA.pdf
   ```

---

## 📝 Notas

- El PDF se genera automáticamente desde el Markdown
- Ambos archivos están en control de versiones (Git)
- Si el negocio cambia, actualiza el Markdown y regenera

---

**Última actualización:** 15 de Junio, 2026  
**Versión del manual:** 1.0  
**Para:** Zoo Picasso
