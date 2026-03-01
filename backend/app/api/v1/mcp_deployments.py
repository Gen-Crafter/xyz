"""
MCP Deployment Registration API — UI-based registration of AI deployments for MCP.

When an AI project is registered here, it receives a unique API key and
ready-to-use MCP connection snippets (Python, JSON, etc.) that the AI agent
can use to connect to the governance server's MCP endpoint.
"""

import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.db_models import MCPDeploymentModel, UserModel

router = APIRouter(prefix="/mcp-deployments", tags=["MCP Deployments"])


# ── Schemas ────────────────────────────────────────────────────────────────

class DeploymentCreate(BaseModel):
    name: str
    description: str = ""
    framework: str = "custom"       # langchain, crewai, autogen, openai, custom
    environment: str = "development" # development, staging, production
    default_action: str = "AUDIT"
    config: dict[str, Any] = {}


class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    framework: Optional[str] = None
    environment: Optional[str] = None
    is_active: Optional[bool] = None
    default_action: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class DeploymentResponse(BaseModel):
    id: str
    name: str
    description: str
    framework: str
    environment: str
    api_key: str
    is_active: bool
    default_action: str
    last_seen_at: Optional[datetime]
    total_scans: int
    total_violations: int
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPConfigSnippet(BaseModel):
    """Ready-to-use MCP connection configs for various frameworks."""
    python_langchain: str
    python_generic: str
    json_config: str
    env_vars: str
    mcp_server_url: str
    api_key: str


class DeploymentStats(BaseModel):
    total_deployments: int
    active_deployments: int
    total_scans: int
    total_violations: int
    frameworks: dict[str, int]


# ── Helpers ────────────────────────────────────────────────────────────────

def _generate_api_key() -> str:
    """Generate a secure 48-char API key with 'mcp_' prefix."""
    return "mcp_" + secrets.token_urlsafe(36)


def _to_response(m: MCPDeploymentModel, mask_key: bool = False) -> DeploymentResponse:
    key = m.api_key
    if mask_key:
        key = key[:8] + "••••••••" + key[-4:]
    return DeploymentResponse(
        id=str(m.id), name=m.name, description=m.description or "",
        framework=m.framework or "custom", environment=m.environment or "development",
        api_key=key, is_active=m.is_active,
        default_action=m.default_action or "AUDIT",
        last_seen_at=m.last_seen_at,
        total_scans=m.total_scans or 0,
        total_violations=m.total_violations or 0,
        config=m.config or {},
        created_at=m.created_at, updated_at=m.updated_at,
    )


def _build_mcp_config(deployment: MCPDeploymentModel, base_url: str) -> MCPConfigSnippet:
    """Generate copy-pastable MCP connection snippets for various frameworks."""
    mcp_url = f"{base_url}/mcp"
    api_key = deployment.api_key

    python_langchain = f'''from langchain_mcp import MCPToolkit

# Connect to AI Governance Server MCP
toolkit = MCPToolkit(
    server_url="{mcp_url}",
    headers={{"X-API-Key": "{api_key}"}},
    transport="sse",
)
tools = toolkit.get_tools()

# Use in your agent
from langchain.agents import initialize_agent
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
'''

    python_generic = f'''from mcp import ClientSession
from mcp.client.sse import sse_client

# Connect to AI Governance Server MCP
async with sse_client("{mcp_url}/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # List available compliance tools
        tools = await session.list_tools()
        print(f"Available tools: {{[t.name for t in tools.tools]}}")

        # Scan an agent request
        result = await session.call_tool("scan_agent_request", {{
            "request_id": "req-001",
            "title": "My AI Task",
            "source_app": "{deployment.name}",
            "tool_chain": [
                {{"tool_name": "web_search", "input": {{}}, "output": {{}}, "sequence": 1}}
            ],
        }})
        print(result)
'''

    json_config = f'''{{"mcpServers": {{
  "{deployment.name.lower().replace(' ', '-')}": {{
    "url": "{mcp_url}/sse",
    "transport": "sse",
    "headers": {{
      "X-API-Key": "{api_key}"
    }}
  }}
}}}}'''

    env_vars = f'''# Add to your .env file
MCP_SERVER_URL={mcp_url}
MCP_API_KEY={api_key}
MCP_TRANSPORT=sse
GOVERNANCE_APP_NAME={deployment.name}
'''

    return MCPConfigSnippet(
        python_langchain=python_langchain,
        python_generic=python_generic,
        json_config=json_config,
        env_vars=env_vars,
        mcp_server_url=mcp_url,
        api_key=api_key,
    )


# ── CRUD ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DeploymentResponse])
async def list_deployments(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MCPDeploymentModel)
        .where(MCPDeploymentModel.tenant_id == user.tenant_id)
        .order_by(MCPDeploymentModel.created_at.desc())
    )
    return [_to_response(m) for m in result.scalars().all()]


@router.post("", response_model=DeploymentResponse, status_code=201)
async def create_deployment(
    body: DeploymentCreate,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.framework not in ("langchain", "crewai", "autogen", "openai", "anthropic", "custom"):
        raise HTTPException(400, "framework must be one of: langchain, crewai, autogen, openai, anthropic, custom")
    if body.default_action not in ("AUDIT", "BLOCK", "ALLOW"):
        raise HTTPException(400, "default_action must be AUDIT, BLOCK, or ALLOW")

    m = MCPDeploymentModel(
        tenant_id=user.tenant_id,
        name=body.name,
        description=body.description,
        framework=body.framework,
        environment=body.environment,
        api_key=_generate_api_key(),
        default_action=body.default_action,
        config=body.config,
        created_by=user.id,
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)
    return _to_response(m)


@router.patch("/{deploy_id}", response_model=DeploymentResponse)
async def update_deployment(
    deploy_id: str,
    body: DeploymentUpdate,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MCPDeploymentModel).where(MCPDeploymentModel.id == uuid.UUID(deploy_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(404, "Deployment not found")
    for field in ("name", "description", "framework", "environment", "is_active", "default_action"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(m, field, val)
    if body.config is not None:
        m.config = body.config
    await db.flush()
    await db.refresh(m)
    return _to_response(m)


@router.delete("/{deploy_id}", status_code=204)
async def delete_deployment(
    deploy_id: str,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MCPDeploymentModel).where(MCPDeploymentModel.id == uuid.UUID(deploy_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(404, "Deployment not found")
    await db.delete(m)
    await db.flush()


# ── MCP Config Snippet ─────────────────────────────────────────────────────

@router.get("/{deploy_id}/mcp-config", response_model=MCPConfigSnippet)
async def get_mcp_config(
    deploy_id: str,
    request: Request,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get ready-to-use MCP connection snippets for this deployment."""
    result = await db.execute(
        select(MCPDeploymentModel).where(MCPDeploymentModel.id == uuid.UUID(deploy_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(404, "Deployment not found")

    base_url = str(request.base_url).rstrip("/")
    return _build_mcp_config(m, base_url)


# ── Regenerate API Key ─────────────────────────────────────────────────────

@router.post("/{deploy_id}/regenerate-key", response_model=DeploymentResponse)
async def regenerate_api_key(
    deploy_id: str,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key for this deployment (invalidates the old one)."""
    result = await db.execute(
        select(MCPDeploymentModel).where(MCPDeploymentModel.id == uuid.UUID(deploy_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(404, "Deployment not found")
    m.api_key = _generate_api_key()
    await db.flush()
    await db.refresh(m)
    return _to_response(m)


# ── Stats ──────────────────────────────────────────────────────────────────

@router.get("/stats/overview", response_model=DeploymentStats)
async def deployment_stats(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(MCPDeploymentModel).where(MCPDeploymentModel.tenant_id == user.tenant_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    active_q = base.where(MCPDeploymentModel.is_active == True)
    active = (await db.execute(select(func.count()).select_from(active_q.subquery()))).scalar() or 0
    scans = (await db.execute(
        select(func.coalesce(func.sum(MCPDeploymentModel.total_scans), 0))
        .where(MCPDeploymentModel.tenant_id == user.tenant_id)
    )).scalar() or 0
    violations = (await db.execute(
        select(func.coalesce(func.sum(MCPDeploymentModel.total_violations), 0))
        .where(MCPDeploymentModel.tenant_id == user.tenant_id)
    )).scalar() or 0

    # Framework breakdown
    fw_rows = (await db.execute(
        select(MCPDeploymentModel.framework, func.count())
        .where(MCPDeploymentModel.tenant_id == user.tenant_id)
        .group_by(MCPDeploymentModel.framework)
    )).all()
    frameworks = {row[0] or "custom": row[1] for row in fw_rows}

    return DeploymentStats(
        total_deployments=total, active_deployments=active,
        total_scans=scans, total_violations=violations,
        frameworks=frameworks,
    )
