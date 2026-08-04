import argparse
import webbrowser
import threading

from AlmaGag.webapp.server import serve


def main():
    parser = argparse.ArgumentParser(
        description="Visor web local de AlmaGag: carga un .sdjf/.gag y ve su SVG."
    )
    parser.add_argument('--host', default='127.0.0.1',
                        help="Host de escucha (default: 127.0.0.1, solo local)")
    parser.add_argument('--port', type=int, default=8321,
                        help="Puerto de escucha (default: 8321)")
    parser.add_argument('--no-browser', action='store_true',
                        help="No abrir el navegador automáticamente")
    args = parser.parse_args()

    if not args.no_browser:
        url = f"http://{args.host}:{args.port}"
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()

    serve(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
