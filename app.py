from pathlib import Path

from robyn import Response, Robyn

from routes import route

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

if __name__ == "__main__":
    app.start()
