from fastapi import FastAPI
import contextlib
import uvicorn

from movies_mcp import movie_server as movie_mcp_server
from radio_mcp import server as radio_mcp_server

mcp_radio_app = radio_mcp_server.streamable_http_app(streamable_http_path="/mcp")
mcp_movie_app = movie_mcp_server.streamable_http_app(streamable_http_path="/mcp")


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(radio_mcp_server.session_manager.run())
        await stack.enter_async_context(movie_mcp_server.session_manager.run())
        yield


app = FastAPI(lifespan=lifespan)
app.mount("/radio", mcp_radio_app)
app.mount("/movie", mcp_movie_app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=10000, log_level="debug")