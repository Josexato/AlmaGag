"""Servidor HTTP local para el visor web de AlmaGag.

Sin dependencias nuevas: usa http.server de la librería estándar. El
renderizado reutiliza AlmaGag.generator.generate_diagram escribiendo el
archivo de entrada y el SVG de salida en un directorio temporal.
"""

import io
import json
import logging
import os
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from AlmaGag.generator import generate_diagram

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

# generate_diagram no es reentrante (logging global, estado de módulo):
# un render a la vez. Para uso local mono-usuario es suficiente.
_render_lock = threading.Lock()

VALID_EXTENSIONS = ('.sdjf', '.gag')


def render_source(filename, content, layout_algorithm='select', view='auto',
                  visualdebug=False):
    """Renderiza el contenido de un .sdjf/.gag y devuelve (ok, svg, log).

    ok: bool; svg: str con el XML del SVG (o None si falló); log: str con
    los mensajes WARNING/ERROR del motor durante el render.
    """
    base = os.path.basename(filename) or 'diagrama.sdjf'
    ext = os.path.splitext(base)[1].lower()
    if ext not in VALID_EXTENSIONS:
        base += '.sdjf'

    log_buffer = io.StringIO()
    log_handler = logging.StreamHandler(log_buffer)
    log_handler.setLevel(logging.WARNING)
    log_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

    with _render_lock:
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        try:
            with tempfile.TemporaryDirectory(prefix='almagag_web_') as tmp:
                input_path = os.path.join(tmp, base)
                output_path = os.path.join(tmp, 'salida.svg')
                with open(input_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                try:
                    ok = generate_diagram(
                        input_path,
                        output_file=output_path,
                        layout_algorithm=layout_algorithm,
                        view=view,
                        visualdebug=visualdebug,
                    )
                except Exception as e:  # el motor no debe tumbar el servidor
                    logging.getLogger(__name__).error(
                        f"Excepción durante el render: {e}")
                    ok = False
                svg = None
                if ok and os.path.exists(output_path):
                    with open(output_path, 'r', encoding='utf-8') as f:
                        svg = f.read()
                elif ok:
                    ok = False
                    log_buffer.write('[ERROR] El motor no produjo el SVG\n')
        finally:
            root_logger.removeHandler(log_handler)

    return bool(ok and svg), svg, log_buffer.getvalue()


class VisorHandler(BaseHTTPRequestHandler):
    server_version = 'AlmaGagVisor/1.0'

    def log_message(self, format, *args):
        # Silenciar el log por request; el terminal queda para el motor.
        pass

    def _send(self, status, body, content_type):
        data = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            index = os.path.join(STATIC_DIR, 'index.html')
            with open(index, 'r', encoding='utf-8') as f:
                self._send(HTTPStatus.OK, f.read(), 'text/html')
        else:
            self._send(HTTPStatus.NOT_FOUND, 'No encontrado', 'text/plain')

    def do_POST(self):
        if self.path != '/render':
            self._send(HTTPStatus.NOT_FOUND, 'No encontrado', 'text/plain')
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            filename = payload.get('filename', 'diagrama.sdjf')
            content = payload.get('content', '')
            options = payload.get('options', {})
        except (ValueError, UnicodeDecodeError) as e:
            self._send(HTTPStatus.BAD_REQUEST,
                       json.dumps({'ok': False, 'log': f'Petición inválida: {e}'}),
                       'application/json')
            return

        ok, svg, log = render_source(
            filename, content,
            layout_algorithm=options.get('layout_algorithm', 'select'),
            view=options.get('view', 'auto'),
            visualdebug=bool(options.get('visualdebug', False)),
        )
        self._send(HTTPStatus.OK,
                   json.dumps({'ok': ok, 'svg': svg, 'log': log}),
                   'application/json')


def serve(host='127.0.0.1', port=8321):
    httpd = ThreadingHTTPServer((host, port), VisorHandler)
    print(f"Visor AlmaGag corriendo en http://{host}:{port}  (Ctrl+C para salir)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nVisor detenido.")
    finally:
        httpd.server_close()
