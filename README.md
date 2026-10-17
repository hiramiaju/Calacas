# Festival de Calaveras — Registro y boletos

## Inicio rápido

1. Instala Python 3.10 o posterior.
2. En la carpeta del proyecto, instala dependencias: `pip install -r requirements.txt`
3. Define una clave secreta estable antes de publicar: `SECRET_KEY="pon_aqui_una_clave_aleatoria_larga"` (en PowerShell: `$env:SECRET_KEY="..."`).
4. Ejecuta: `python app.py`
5. Abre http://127.0.0.1:5000

## Qué hace

- Formulario con nombre completo, universidad, teléfono mexicano de 10 dígitos y dirección.
- Persiste en `data/registros.json`; no usa SQL.
- Evita teléfonos duplicados, nombres idénticos y variantes que compartan primer nombre y último apellido. **Revisar coincidencias manualmente**: personas distintas pueden llamarse parecido.
- Máximo 3 registros por dispositivo identificado por una cookie firmada.
- Boleto personalizado PNG, usando como fondo `assets/boleto_original.png`.
- Solo el dispositivo que registró puede descargar el boleto mediante su enlace. Si pierde cookies, no podrá recuperarlo sin asistencia.

## Limitaciones técnicas importantes

La cookie firmada bloquea registros adicionales mientras persista, pero no es una prueba infalible de dispositivo: un usuario podría borrar cookies, cambiar navegador, usar modo incógnito u otro dispositivo. Para un límite fuerte requiere un control adicional como validación por SMS / correo o un identificador presencial. No se recomienda identificar usuarios solo por IP porque puede compartirse entre muchas personas.

El archivo JSON está protegido mediante bloqueo del proceso y `fcntl` en Linux, con escrituras atómicas. Para despliegues con mucho tráfico o varios servidores, conviene una BD transaccional. Nunca publiques `data/registros.json`, ya que contiene datos personales. Configura HTTPS, copias de seguridad, acceso restringido y un aviso de privacidad adecuado antes de abrir el registro al público. No se genera un código de barras válido para verificación: el del diseño es decorativo. Para verificar boletos en acceso, sería necesario un código QR único y un panel de validación.

## Ubicación del nombre

Si cambias la imagen, ajusta la posición del texto en `make_ticket()` dentro de `app.py`.
