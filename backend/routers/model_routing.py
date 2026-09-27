"""Protected operational model-routing API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..model_routing import clear_model_route_override, list_model_routes, update_model_route

router = APIRouter(prefix="/api/model-routing")


class ModelRouteUpdate(BaseModel):
    value: Any


@router.get("")
async def get_model_routes():
    return list_model_routes()


@router.put("/{route_id}")
async def put_model_route(route_id: str, payload: ModelRouteUpdate):
    try:
        return update_model_route(route_id, payload.value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{route_id}")
async def delete_model_route(route_id: str):
    try:
        return clear_model_route_override(route_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
