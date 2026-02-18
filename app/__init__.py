from pathlib import Path

from robyn import Robyn, Response

from .routes.route import route


def create_app():
    app = Robyn(__file__)
    app.include_router(route)

    app.serve_directory(
        route="/",
        directory_path=str(Path(Path(__file__).parent.resolve(), "static")),
        index_file="index.html",
    )

    @app.exception
    def handle_exception(error: Exception):
        return Response(
            status_code=500,
            description=f"An error occurred: {error}",
            headers={"Content-Type": "text/plain"},
        )

    return app
