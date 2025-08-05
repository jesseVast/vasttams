from fastapi import APIRouter, Depends, Query, HTTPException, Request, File, UploadFile, Form
from typing import List, Optional
from .models import Flow, FlowsResponse, FlowSegment, FlowStorage, FlowStoragePost
from .vast_store import VASTStore
from .dependencies import get_vast_store
from .flows import FlowManager

router = APIRouter()
flow_manager = FlowManager()

@router.head("/flows")
async def head_flows():
    return {}

@router.get("/flows", response_model=FlowsResponse)
async def list_flows(
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    format: Optional[str] = Query(None, description="Filter by format"),
    codec: Optional[str] = Query(None, description="Filter by codec"),
    label: Optional[str] = Query(None, description="Filter by label"),
    frame_width: Optional[int] = Query(None, description="Filter by frame width"),
    frame_height: Optional[int] = Query(None, description="Filter by frame height"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results"),
    store: VASTStore = Depends(get_vast_store)
):
    filters = {}
    if source_id: filters['source_id'] = source_id
    if timerange: filters['timerange'] = timerange
    if format: filters['format'] = format
    if codec: filters['codec'] = codec
    if label: filters['label'] = label
    if frame_width: filters['frame_width'] = frame_width
    if frame_height: filters['frame_height'] = frame_height
    return await flow_manager.list_flows(filters, limit or 100, store)

@router.head("/flows/{flow_id}")
async def head_flow(flow_id: str):
    return {}

@router.get("/flows/{flow_id}", response_model=Flow)
async def get_flow(flow_id: str, store: VASTStore = Depends(get_vast_store)):
    return await flow_manager.get_flow(flow_id, store)

@router.put("/flows/{flow_id}", response_model=Flow)
async def update_flow(flow_id: str, flow: Flow, store: VASTStore = Depends(get_vast_store)):
    return await flow_manager.update_flow(flow_id, flow, store)

@router.delete("/flows/{flow_id}")
async def delete_flow(
    flow_id: str, 
    soft_delete: bool = Query(True, description="Perform soft delete (default) or hard delete"),
    cascade: bool = Query(True, description="Cascade delete to associated segments"),
    deleted_by: str = Query("system", description="User/system performing the deletion"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete a flow with optional soft delete and cascade options."""
    return await flow_manager.delete_flow(flow_id, store, soft_delete=soft_delete, cascade=cascade, deleted_by=deleted_by)



@router.post("/flows", response_model=Flow, status_code=201)
async def create_flow(flow: Flow, store: VASTStore = Depends(get_vast_store)):
    return await flow_manager.create_flow(flow, store) 