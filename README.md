# Affinity MCP Server (Windows)

Servidor MCP (Model Context Protocol) adaptado para **Windows** que permite a asistentes de IA (como Claude, Antigravity, Cursor, etc.) controlar la suite creativa de **Affinity** (Affinity Designer, Photo, Publisher y la app unificada Canva Affinity).

Adaptado del proyecto original para macOS de [sekharmalla/affinity-mcp-server](https://github.com/sekharmalla/affinity-mcp-server).

---

## 🚀 Características

* **Detección y control de ventana**: Detección nativa del proceso `Affinity.exe` y control de foco.
* **Captura de pantalla de alta fidelidad**: Captura directa de la ventana de Affinity (`PrintWindow` / GDI) para retroalimentación visual en tiempo real.
* **Operaciones de documentos**: Crear nuevo documento, abrir archivo, guardar (`Ctrl+S`), Guardar como (`Ctrl+Shift+S`), exportar (`Ctrl+Alt+Shift+S`) y cerrar.
* **Herramientas de dibujo y selección**: Selección de herramientas vectoriales y ráster mediante atajos estándar (`v` mover, `m` formas, `t` texto, `p` pluma, `b` pincel, etc.).
* **Gestión de capas**: Crear nuevas capas de píxeles, capas vectoriales, máscaras o ajustes.
* **Interacción con ratón y teclado**: Clics, doble clic, clic derecho, arrastre suave de dibujo (`drag`), escritura de texto y atajos arbitrarios.
* **Historial**: Deshacer (`Ctrl+Z`) y Rehacer (`Ctrl+Y`).

---

## 🛠️ Herramientas disponibles (17 tools)

1. `affinity_status`: Estado actual, PID, dimensiones y título de ventana de Affinity.
2. `affinity_launch`: Inicia Affinity si está cerrado o lo trae al frente.
3. `affinity_open_file`: Abre un archivo existente (`.af`, `.psd`, `.svg`, etc.).
4. `affinity_new_document`: Crea un nuevo documento (con o sin diálogo de ajustes preestablecidos).
5. `affinity_save`: Guarda el documento actual (`Ctrl+S`) o "Guardar como" (`Ctrl+Shift+S`).
6. `affinity_export`: Abre el diálogo de exportación rápida o por formato.
7. `affinity_close_document`: Cierra el documento activo (`Ctrl+W`).
8. `affinity_select_tool`: Selecciona herramientas (`move`, `node`, `pen`, `pencil`, `brush`, `eraser`, `rectangle`, `ellipse`, `text`, `fill`, `gradient`, `eyedropper`, `zoom`, `hand`, `crop`).
9. `affinity_keystroke`: Envía combinaciones de teclas con modificadores (`ctrl`, `shift`, `alt`, `win`).
10. `affinity_key_code`: Envía teclas de navegación/acción (`escape`, `enter`, `tab`, `delete`, etc.).
11. `affinity_type_text`: Escribe texto en la herramienta o campo enfocado.
12. `affinity_mouse_action`: Acciones de ratón (`click`, `double_click`, `right_click`, `drag`) relativas a la ventana.
13. `affinity_screenshot`: Captura la ventana de Affinity y guarda un PNG para inspección visual.
14. `affinity_undo_redo`: Deshacer (`Ctrl+Z`) o Rehacer (`Ctrl+Y`) `n` veces.
15. `affinity_add_layer`: Añade capas de píxeles, capas vectoriales o máscaras.
16. `affinity_document_ops`: Acciones sobre el documento (acoplar, rotar, voltear, recortar lienzo).
17. `affinity_run_macro`: Importa o ejecuta un archivo `.afmacro`.

---

## ⚙️ Configuración en Clientes MCP

### Configuración con Python Virtualenv (Recomendada)

En `claude_desktop_config.json` o `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "affinity-mcp": {
      "command": "C:/Users/jpazo/DEV/affinity-control-mcp/.venv/Scripts/python.exe",
      "args": [
        "C:/Users/jpazo/DEV/affinity-control-mcp/server.py"
      ]
    }
  }
}
```

O si usas `uv`:

```json
{
  "mcpServers": {
    "affinity-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:/Users/jpazo/DEV/affinity-control-mcp",
        "server.py"
      ]
    }
  }
}
```
