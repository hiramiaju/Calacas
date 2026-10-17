import os, re, json, uuid, hmac, hashlib, tempfile, threading, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file, make_response
from PIL import Image, ImageDraw, ImageFont
from itsdangerous import URLSafeSerializer, BadSignature
from werkzeug.middleware.proxy_fix import ProxyFix

BASE = Path(__file__).resolve().parent
DB = BASE / 'data' / 'registros.json'
TICKET = BASE / 'assets' / 'boleto_original.png'
FONT = BASE / 'assets' / 'font.ttf'
DB.parent.mkdir(exist_ok=True)
if not DB.exists(): DB.write_text('[]', encoding='utf-8')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'DEV_ONLY_CHANGE_THIS_SECRET_BEFORE_DEPLOYING')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
# Only enable ProxyFix if deployed behind a trusted reverse proxy and configured appropriately.
serializer = URLSafeSerializer(app.config['SECRET_KEY'], salt='festival-device-v1')
lock = threading.RLock()
try:
    import fcntl
except ImportError:
    fcntl = None


def fold(s):
    s = unicodedata.normalize('NFD', s.casefold())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def normalize_name(s):
    return ' '.join(re.sub(r'[^a-zñ ]', ' ', fold(s)).split())


def valid_name(s):
    parts = s.split()
    return 2 <= len(parts) <= 8 and len(s) <= 95 and all(len(p) >= 2 and p.replace('-', '').isalpha() for p in parts)


def load_db():
    with DB.open('r', encoding='utf-8') as f:
        rows = json.load(f)
    if not isinstance(rows, list): raise ValueError('Formato JSON inválido')
    return rows


def save_db(rows):
    fd, tmp = tempfile.mkstemp(dir=DB.parent, prefix='.tmp_', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, DB)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


class DatabaseLock:
    def __enter__(self):
        lock.acquire()
        self.f = open(DB.parent / '.registro.lock', 'a+')
        if fcntl: fcntl.flock(self.f.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *args):
        if fcntl: fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)
        self.f.close()
        lock.release()


def device_id():
    cookie = request.cookies.get('festival_device', '')
    try:
        val = serializer.loads(cookie)
        if re.fullmatch(r'[0-9a-f]{32}', val): return val, False
    except (BadSignature, TypeError): pass
    return uuid.uuid4().hex, True


def set_device_cookie(resp, device):
    resp.set_cookie('festival_device', serializer.dumps(device), max_age=60*60*24*365,
                    secure=request.is_secure, httponly=True, samesite='Lax', path='/')
    return resp


@app.after_request
def headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'same-origin'
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.get('/')
def index():
    device, _ = device_id()
    with DatabaseLock():
        count = sum(row['device_id'] == device for row in load_db())
    resp = make_response(render_template('index.html', remaining=max(0, 3-count)))
    return set_device_cookie(resp, device)


@app.get('/api/estado')
def estado():
    dev, _ = device_id()
    with DatabaseLock():
        count = sum(row['device_id'] == dev for row in load_db())
    return set_device_cookie(jsonify(restantes=max(0, 3-count)), dev)


@app.post('/api/registro')
def registrar():
    if not request.is_json:
        return jsonify(error='Envía los datos en formato JSON.'), 415
    data = request.get_json(silent=True) or {}
    nombre = ' '.join(str(data.get('nombre', '')).strip().split())
    universidad = ' '.join(str(data.get('universidad', '')).strip().split())
    direccion = ' '.join(str(data.get('direccion', '')).strip().split())
    telefono = re.sub(r'\D', '', str(data.get('telefono', '')))
    if not valid_name(nombre):
        return jsonify(error='Escribe tu nombre completo, mínimo nombre y apellido (solo letras).'), 400
    if not (3 <= len(universidad) <= 120):
        return jsonify(error='Escribe el nombre completo de tu universidad.'), 400
    if len(telefono) != 10:
        return jsonify(error='El teléfono debe tener exactamente 10 dígitos.'), 400
    if not (8 <= len(direccion) <= 220):
        return jsonify(error='Escribe una dirección completa (calle, número y colonia).'), 400
    device, _ = device_id()
    normalized = normalize_name(nombre)
    tokens = normalized.split()
    with DatabaseLock():
        rows = load_db()
        if sum(x['device_id'] == device for x in rows) >= 3:
            return jsonify(error='Este dispositivo alcanzó el máximo de 3 registros.'), 403
        for x in rows:
            prev = x['nombre_normalizado'].split()
            if x['telefono'] == telefono:
                return jsonify(error='Este número telefónico ya fue registrado.'), 409
            if x['nombre_normalizado'] == normalized:
                return jsonify(error='Esta persona ya está registrada.'), 409
            # Mitiga inscripciones duplicadas con nombres intermedios omitidos.
            if len(prev) >= 2 and tokens[0] == prev[0] and tokens[-1] == prev[-1]:
                return jsonify(error='Ya existe un registro con el mismo primer nombre y último apellido. Contacta al organizador si es otra persona.'), 409
        rid = uuid.uuid4().hex
        rows.append({'id': rid, 'nombre': nombre, 'nombre_normalizado': normalized,
                     'universidad': universidad, 'telefono': telefono, 'direccion': direccion,
                     'device_id': device, 'fecha_utc': datetime.now(timezone.utc).isoformat()})
        save_db(rows)
        restantes = 3 - sum(x['device_id'] == device for x in rows)
    return set_device_cookie(jsonify(ok=True, id=rid, nombre=nombre, restantes=restantes,
                                     boleto_url=f'/boleto/{rid}.png'), device), 201


def make_ticket(nombre):
    image = Image.open(TICKET).convert('RGB')
    draw = ImageDraw.Draw(image)
    # Name-writing area: x=430..1133, baseline ~750, on 1659x948 ticket.
    text = nombre.upper()
    max_width = 685
    size = 36
    while size >= 17:
        font = ImageFont.truetype(str(FONT), size)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width: break
        size -= 1
    if draw.textbbox((0, 0), text, font=font)[2] > max_width:
        raise ValueError('El nombre es demasiado largo para el boleto')
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]
    draw.text((435, 748 - text_h/2 - bbox[1]), text, font=font, fill='#792568')
    buff = BytesIO()
    image.save(buff, format='PNG', optimize=True)
    buff.seek(0)
    return buff


@app.get('/boleto/<rid>.png')
def boleto(rid):
    if not re.fullmatch(r'[0-9a-f]{32}', rid): return jsonify(error='Boleto no encontrado.'), 404
    device, _ = device_id()
    with DatabaseLock():
        row = next((x for x in load_db() if x['id'] == rid and x['device_id'] == device), None)
    if row is None: return jsonify(error='Boleto no encontrado para este dispositivo.'), 404
    return send_file(make_ticket(row['nombre']), mimetype='image/png', as_attachment=True,
                     download_name=f'boleto_festival_{rid[:8]}.png')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')), debug=False)
