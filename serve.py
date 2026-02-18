"""A module that runs the application server."""

from concurrent.futures import ThreadPoolExecutor

import click

from app import create_app


@click.command("server")
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="The host to bind the server to.",
)
@click.option(
    "--port",
    type=int,
    default=8080,
    help="The port to run the server on.",
)
@click.option(
    "--mode",
    type=click.Choice(["server", "desktop"]),
    default="desktop",
    help="The mode to run the app in (server, desktop).",
)
def serve(host: str, port: int, mode: str) -> None:
    """Run the application based on the provided arguments.

    Example usage:
        For server:
            uv run serve.py --host 127.0.0.1 --port 5000 --mode=server
        For desktop:
            uv run serve.py
    """
    app = create_app()

    match mode:
        case "server":
            app.start(host=host, port=port)
        case _:
            from webgui import start_browser

            with ThreadPoolExecutor(max_workers=2) as executor:
                server_future = executor.submit(app.start, host, port)
                browser_future = executor.submit(start_browser, host, port)
                try:
                    server_future.result()
                    browser_future.result()
                except KeyboardInterrupt:
                    executor.shutdown()


if __name__ == "__main__":
    serve()
