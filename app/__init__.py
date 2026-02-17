from pathlib import Path

from robyn import Robyn

from .routes.route import route


def create_app():
    app = Robyn(__file__)
    app.include_router(route)

    app.serve_directory(
        route="/",
        directory_path=str(Path(Path(__file__).parent.resolve(), "static")),
        index_file="index.html",
    )

    return app
