# ============================================
# Lumina 墨光 · AI 网关路由
# /ai/models 对外列表 · /ai/gateway/* 管理面
# ============================================
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import AuthUser, get_current_user, require_role
from ..instrumentation import (
    EVENT_AI_CALL_RECORDED,
    EVENT_AI_MODEL_REGISTERED,
    EVENT_AI_MODELS,
    EVENT_AI_MODEL_UPDATED,
    EVENT_AI_ROUTE,
    EVENT_AI_USAGE,
    Instrumentation,
)
from ..models import AICallLog, AIModel, AIProvider
from ..schemas import (
    CallRecordRequest,
    ModelCreate,
    ModelOut,
    ModelUpdate,
    ProviderCreate,
    ProviderOut,
    PublicModel,
    RouteRequest,
    RouteResult,
    SuccessResponse,
    UsageStats,
)

router = APIRouter(prefix="/ai", tags=["AI 网关"])


# ─── 工具 ───
def _model_out(m: AIModel) -> ModelOut:
    out = ModelOut.model_validate(m)
    out.provider_name = m.provider.name if m.provider else None
    return out


def _get_model(db: Session, model_id) -> AIModel:
    m = db.get(AIModel, model_id)
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")
    return m


def _get_provider_by_name(db: Session, name: str) -> AIProvider:
    p = db.query(AIProvider).filter(AIProvider.name == name).first()
    if not p:
        raise HTTPException(status_code=400, detail=f"供应商不存在: {name}")
    return p


# ─── 对外：可用模型列表 ───
@router.get("/models", response_model=list[PublicModel], summary="可用模型列表")
def list_public_models(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    task_type: str | None = None,
):
    """仅返回已启用模型（含其供应商启用），可按 task_type 过滤"""
    query = (
        db.query(AIModel)
        .join(AIProvider, AIProvider.id == AIModel.provider_id)
        .filter(AIModel.enabled.is_(True), AIProvider.enabled.is_(True))
    )
    if task_type:
        query = query.filter(AIModel.task_types.contains([task_type]))

    models = query.order_by(AIModel.priority, AIModel.created_at).all()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_AI_MODELS, properties={"task_type": task_type, "count": len(models)}
    )
    return [PublicModel(
        model_name=m.model_name,
        display_name=m.display_name,
        provider=m.provider.name if m.provider else "",
        task_types=m.task_types or [],
        description=m.description,
        cost_per_1k_tokens=m.cost_per_1k_tokens,
    ) for m in models]


# ─── 智能路由 ───
@router.post("/gateway/route", response_model=RouteResult, summary="智能路由（按任务类型选模型）")
def route_model(
    payload: RouteRequest,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按任务类型返回主选/备选模型（已启用、按优先级、配额可用）"""
    candidates = (
        db.query(AIModel)
        .join(AIProvider, AIProvider.id == AIModel.provider_id)
        .filter(
            AIModel.enabled.is_(True),
            AIProvider.enabled.is_(True),
            AIModel.task_types.contains([payload.task_type]),
        )
        .order_by(AIModel.priority, AIModel.created_at)
        .all()
    )
    available = [m for m in candidates if _quota_ok(m.provider)]
    if not available:
        Instrumentation(db, request, str(user.id)).track(
            EVENT_AI_ROUTE, properties={"task_type": payload.task_type, "result": "none"}
        )
        return RouteResult(task_type=payload.task_type, primary=None, fallback=None,
                           note="无可用的已启用模型，请在管理端检查配额或启用状态")

    pick = available[:2]
    Instrumentation(db, request, str(user.id)).track(
        EVENT_AI_ROUTE, properties={
            "task_type": payload.task_type,
            "primary": pick[0].model_name,
            "fallback": pick[1].model_name if len(pick) > 1 else None,
        }
    )
    return RouteResult(
        task_type=payload.task_type,
        primary=_model_out(pick[0]),
        fallback=_model_out(pick[1]) if len(pick) > 1 else None,
        note="OK",
    )


def _quota_ok(provider: AIProvider) -> bool:
    """配额检查：不限或未超预算"""
    if provider.monthly_quota is None or float(provider.monthly_quota) <= 0:
        return True
    return float(provider.used_quota or 0) < float(provider.monthly_quota)


# ─── 用量记录 / 统计 ───
@router.post("/gateway/calls/record", response_model=SuccessResponse, summary="记录模型调用用量")
def record_call(
    payload: CallRecordRequest,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对话/批阅服务调用模型后上报用量，并累加供应商已用额度"""
    model = _get_model(db, payload.model_id)
    tokens = payload.prompt_tokens + payload.completion_tokens
    cost = (Decimal(tokens) / 1000) * (model.cost_per_1k_tokens or Decimal("0"))

    log = AICallLog(
        user_id=user.id,
        model_id=model.id,
        model_name=model.model_name,
        task_type=payload.task_type,
        prompt_tokens=payload.prompt_tokens,
        completion_tokens=payload.completion_tokens,
        latency_ms=payload.latency_ms,
        cost=cost,
        ok=payload.ok,
        error_message=payload.error_message,
    )
    db.add(log)
    if model.provider:
        model.provider.used_quota = (model.provider.used_quota or Decimal("0")) + cost
    db.commit()

    Instrumentation(db, request, str(user.id)).track(
        EVENT_AI_CALL_RECORDED, properties={
            "model": model.model_name, "task_type": payload.task_type, "tokens": tokens,
            "cost": str(cost), "ok": str(payload.ok),
        }
    )
    return SuccessResponse()


@router.get("/gateway/usage", response_model=UsageStats, summary="用量统计（管理员）")
def usage_stats(
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    days: int = 30,
):
    """近 N 天按模型/用户的调用量与成本统计"""
    since = None
    if days > 0:
        from datetime import datetime, timedelta, timezone
        since = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(AICallLog)
    if since:
        query = query.filter(AICallLog.created_at >= since)

    logs = query.all()
    stats = UsageStats(
        total_calls=len(logs),
        total_tokens=sum(l.prompt_tokens + l.completion_tokens for l in logs),
        total_cost=sum((l.cost or Decimal("0")) for l in logs),
    )
    by_model: dict = {}
    by_user: dict = {}
    for l in logs:
        bm = by_model.setdefault(l.model_name, {"calls": 0, "tokens": 0, "cost": Decimal("0")})
        bm["calls"] += 1
        bm["tokens"] += l.prompt_tokens + l.completion_tokens
        bm["cost"] += (l.cost or Decimal("0"))
        bu = by_user.setdefault(str(l.user_id), {"calls": 0, "tokens": 0, "cost": Decimal("0")})
        bu["calls"] += 1
        bu["tokens"] += l.prompt_tokens + l.completion_tokens
        bu["cost"] += (l.cost or Decimal("0"))
    stats.by_model = by_model
    stats.by_user = by_user

    Instrumentation(db, request, str(admin.id)).track(
        EVENT_AI_USAGE, properties={"days": days, "calls": stats.total_calls}
    )
    return stats


# ─── 管理面：模型池 ───
@router.get("/gateway/models", response_model=list[ModelOut], summary="模型池（管理员）")
def admin_models(
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    models = db.query(AIModel).order_by(AIModel.priority, AIModel.created_at).all()
    return [_model_out(m) for m in models]


@router.post("/gateway/models", response_model=ModelOut, status_code=201, summary="注册模型（管理员）")
def register_model(
    payload: ModelCreate,
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    provider = _get_provider_by_name(db, payload.provider_name)
    if db.query(AIModel).filter(AIModel.model_name == payload.model_name).first():
        raise HTTPException(status_code=409, detail="模型名已存在")

    m = AIModel(
        provider_id=provider.id,
        model_name=payload.model_name,
        display_name=payload.display_name,
        task_types=payload.task_types,
        description=payload.description,
        priority=payload.priority,
        cost_per_1k_tokens=payload.cost_per_1k_tokens,
        max_tokens=payload.max_tokens,
        openai_compatible=payload.openai_compatible,
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    Instrumentation(db, request, str(admin.id)).track(
        EVENT_AI_MODEL_REGISTERED, properties={"model": m.model_name, "provider": provider.name}
    )
    return _model_out(m)


@router.patch("/gateway/models/{model_id}", response_model=ModelOut, summary="启停/更新模型（管理员）")
def update_model(
    model_id: uuid.UUID,
    payload: ModelUpdate,
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    m = _get_model(db, model_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(m, key, value)
    db.commit()
    db.refresh(m)

    Instrumentation(db, request, str(admin.id)).track(
        EVENT_AI_MODEL_UPDATED, properties={"model": m.model_name, "fields": list(data.keys())}
    )
    return _model_out(m)


# ─── 管理面：供应商 ───
@router.get("/gateway/providers", response_model=list[ProviderOut], summary="供应商列表（管理员）")
def admin_providers(
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return db.query(AIProvider).order_by(AIProvider.created_at).all()


@router.post("/gateway/providers", response_model=ProviderOut, status_code=201, summary="新增供应商（管理员）")
def register_provider(
    payload: ProviderCreate,
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if db.query(AIProvider).filter(AIProvider.name == payload.name).first():
        raise HTTPException(status_code=409, detail="供应商已存在")
    p = AIProvider(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p