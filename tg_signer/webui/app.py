from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from tg_signer.config import SupportAction

from .repository import (
    ConfigValidationError,
    SignTaskRepository,
    TaskConflictError,
    TaskNotFoundError,
)
from .schemas import (
    ActionMeta,
    ActionMetaResponse,
    SignTaskCreateRequest,
    SignTaskResponse,
    SignTaskUpdateRequest,
    TaskListResponse,
    TaskSummary,
)
from .settings import WebUISettings


def _read_index(static_dir: Path) -> str:
    index_path = static_dir / "index.html"
    with index_path.open("r", encoding="utf-8") as fp:
        return fp.read()


def create_app(settings: WebUISettings | None = None) -> FastAPI:
    settings = settings or WebUISettings.from_environment()
    app = FastAPI(title="tg-signer Web UI", version="1.0.0")
    repository = SignTaskRepository(settings)
    index_html = _read_index(settings.static_dir)

    app.mount(
        "/static",
        StaticFiles(directory=str(settings.static_dir), html=True),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return index_html

    @app.get("/api/sign/tasks", response_model=TaskListResponse)
    async def list_tasks() -> TaskListResponse:
        tasks = [TaskSummary(name=name) for name in repository.list_tasks()]
        return TaskListResponse(tasks=tasks)

    @app.post(
        "/api/sign/tasks",
        response_model=SignTaskResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_task(payload: SignTaskCreateRequest) -> SignTaskResponse:
        try:
            config = repository.create_task(payload.name, payload.config)
        except TaskConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ConfigValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return SignTaskResponse(name=payload.name, config=config.to_jsonable())

    @app.get(
        "/api/sign/tasks/{task_name}",
        response_model=SignTaskResponse,
    )
    async def get_task(task_name: str) -> SignTaskResponse:
        try:
            config = repository.load_task(task_name)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return SignTaskResponse(name=task_name, config=config.to_jsonable())

    @app.put(
        "/api/sign/tasks/{task_name}",
        response_model=SignTaskResponse,
    )
    async def update_task(
        task_name: str, payload: SignTaskUpdateRequest
    ) -> SignTaskResponse:
        try:
            config = repository.update_task(task_name, payload.config)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ConfigValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors) from exc
        return SignTaskResponse(name=task_name, config=config.to_jsonable())

    @app.delete(
        "/api/sign/tasks/{task_name}", status_code=status.HTTP_204_NO_CONTENT
    )
    async def delete_task(task_name: str) -> None:
        try:
            repository.delete_task(task_name)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/sign/template", response_model=SignTaskResponse)
    async def get_template() -> SignTaskResponse:
        config = repository.default_config()
        return SignTaskResponse(name="template", config=config.to_jsonable())

    @app.get("/api/meta/actions", response_model=ActionMetaResponse)
    async def list_actions() -> ActionMetaResponse:
        items: list[ActionMeta] = []
        for action in SupportAction:
            requires_text = action in {
                SupportAction.SEND_TEXT,
                SupportAction.SEND_DICE,
                SupportAction.CLICK_KEYBOARD_BY_TEXT,
            }
            label = action.desc
            items.append(
                ActionMeta(
                    value=int(action.value),
                    key=action.name,
                    label=label,
                    requires_text=requires_text,
                )
            )
        return ActionMetaResponse(actions=items)

    return app
