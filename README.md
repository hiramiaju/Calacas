# Festival de Calaveras — Registro ligero

## Configuración
1. Abre `app.py` y cambia la constante `UNIVERSIDAD_FIJA = 'UNIVERSIDAD_POR_CONFIGURAR'` por el nombre de tu universidad (ejemplo: `'Universidad Politécnica de Aguascalientes'`). No se pregunta en el formulario y **todos los nuevos registros** usarán ese mismo valor.
2. Instala dependencias: `pip install -r requirements.txt`
3. Configura `SECRET_KEY` con una cadena aleatoria privada y estable para producción.
4. Ejecuta `python app.py`.

## Funcionamiento
- Guarda únicamente datos en `data/registros.json` y muestra confirmación en pantalla.
- No genera PNG ni boleto personalizado en el servidor. Se conserva una imagen estática opcional del festival en la página.
- Mantiene el límite de 3 registros por cookie/dispositivo y las comprobaciones de duplicados. El límite no es invulnerable si se borran las cookies.
- Conserva registros previos sin modificarlos: la constante solo aplica a los nuevos.
- Los datos personales deben mantenerse fuera de carpetas públicas y protegerse con aviso de privacidad y acceso restringido.
