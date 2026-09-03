# ============================================
# Lumina 墨光 · D-08 视频录播路由
# 视频列表 / 播放 / 章节 / 笔记 / 观看历史
# ============================================
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user
from app.models import (
    Video, VideoChapter, VideoNote, VideoWatchHistory, Course,
)
from app.schemas import (
    VideoOut, VideoDetailOut, VideoChapterOut,
    VideoNoteCreate, VideoNoteOut,
    VideoWatchHistoryOut, VideoProgressIn,
)

router = APIRouter(prefix="/videos", tags=["视频录播（D-08）"])


def _format_duration(sec: int) -> str:
    """秒数转 MM:SS 格式"""
    if sec <= 0:
        return "00:00"
    m, s = divmod(sec, 60)
    return f"{m:02d}:{s:02d}"


# ═══════════════════════════════════════════════════════════════════
# 1. 视频列表
# ═══════════════════════════════════════════════════════════════════

@router.get("", response_model=list[VideoOut], summary="视频列表")
def list_videos(
    category: Optional[str] = Query(None, description="分类过滤"),
    course_id: Optional[str] = Query(None, description="课程 ID 过滤"),
    search: Optional[str] = Query(None, description="搜索关键字"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取已发布视频列表，支持分类/课程/搜索过滤"""
    q = db.query(Video).filter(Video.published == True)

    if category:
        q = q.filter(Video.category == category)
    if course_id:
        q = q.filter(Video.course_id == course_id)
    if search:
        q = q.filter(Video.title.contains(search))

    videos = q.order_by(Video.created_at.desc()).offset(offset).limit(limit).all()

    out = []
    for v in videos:
        # 获取当前用户观看进度
        history = db.query(VideoWatchHistory).filter(
            VideoWatchHistory.user_id == user.id,
            VideoWatchHistory.video_id == v.id,
        ).first()
        progress_pct = history.progress_pct if history else 0

        out.append(VideoOut(
            id=v.id, course_id=v.course_id,
            title=v.title, description=v.description,
            category=v.category, tags=v.tags,
            duration_sec=v.duration_sec,
            duration_display=_format_duration(v.duration_sec),
            video_url=v.video_url, thumbnail_url=v.thumbnail_url,
            cover_emoji=v.cover_emoji, cover_gradient=v.cover_gradient,
            view_count=v.view_count,
            progress_pct=progress_pct,
            created_at=v.created_at,
        ))
    return out


@router.get("/{video_id}", response_model=VideoDetailOut, summary="视频详情")
def get_video_detail(
    video_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取视频详情（含章节、笔记）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 增加观看次数
    video.view_count = (video.view_count or 0) + 1
    db.commit()

    # 获取章节
    chapters = db.query(VideoChapter).filter(
        VideoChapter.video_id == video_id
    ).order_by(VideoChapter.sequence).all()

    chapter_out = [
        VideoChapterOut(
            id=c.id, video_id=c.video_id, sequence=c.sequence,
            title=c.title, start_sec=c.start_sec,
            start_display=_format_duration(c.start_sec),
        )
        for c in chapters
    ]

    # 获取当前用户笔记
    notes = db.query(VideoNote).filter(
        VideoNote.user_id == user.id,
        VideoNote.video_id == video_id,
    ).order_by(VideoNote.timestamp_sec).all()

    note_out = [
        VideoNoteOut(
            id=n.id, video_id=n.video_id,
            timestamp_sec=n.timestamp_sec,
            timestamp_display=_format_duration(n.timestamp_sec),
            content=n.content, created_at=n.created_at,
        )
        for n in notes
    ]

    # 获取观看进度
    history = db.query(VideoWatchHistory).filter(
        VideoWatchHistory.user_id == user.id,
        VideoWatchHistory.video_id == video_id,
    ).first()
    progress_pct = history.progress_pct if history else 0

    return VideoDetailOut(
        id=video.id, course_id=video.course_id,
        title=video.title, description=video.description,
        category=video.category, tags=video.tags,
        duration_sec=video.duration_sec,
        duration_display=_format_duration(video.duration_sec),
        video_url=video.video_url, thumbnail_url=video.thumbnail_url,
        cover_emoji=video.cover_emoji, cover_gradient=video.cover_gradient,
        view_count=video.view_count,
        progress_pct=progress_pct,
        created_at=video.created_at,
        chapters=chapter_out,
        notes=note_out,
    )


# ═══════════════════════════════════════════════════════════════════
# 2. 视频笔记
# ═══════════════════════════════════════════════════════════════════

@router.post("/notes", response_model=VideoNoteOut, status_code=201, summary="添加视频笔记")
def create_note(
    payload: VideoNoteCreate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """在指定时间点添加笔记"""
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    note = VideoNote(
        user_id=user.id,
        video_id=payload.video_id,
        timestamp_sec=payload.timestamp_sec,
        content=payload.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return VideoNoteOut(
        id=note.id, video_id=note.video_id,
        timestamp_sec=note.timestamp_sec,
        timestamp_display=_format_duration(note.timestamp_sec),
        content=note.content, created_at=note.created_at,
    )


@router.get("/notes/{video_id}", response_model=list[VideoNoteOut], summary="获取视频笔记列表")
def list_notes(
    video_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户在指定视频的所有笔记"""
    notes = db.query(VideoNote).filter(
        VideoNote.user_id == user.id,
        VideoNote.video_id == video_id,
    ).order_by(VideoNote.timestamp_sec).all()

    return [
        VideoNoteOut(
            id=n.id, video_id=n.video_id,
            timestamp_sec=n.timestamp_sec,
            timestamp_display=_format_duration(n.timestamp_sec),
            content=n.content, created_at=n.created_at,
        )
        for n in notes
    ]


@router.delete("/notes/{note_id}", summary="删除视频笔记")
def delete_note(
    note_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除笔记（仅本人）"""
    note = db.query(VideoNote).filter(VideoNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    if note.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权删除")

    db.delete(note)
    db.commit()
    return {"message": "笔记已删除"}


# ═══════════════════════════════════════════════════════════════════
# 3. 视频章节
# ═══════════════════════════════════════════════════════════════════

@router.get("/{video_id}/chapters", response_model=list[VideoChapterOut], summary="获取视频章节")
def list_chapters(
    video_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取视频章节列表"""
    chapters = db.query(VideoChapter).filter(
        VideoChapter.video_id == video_id
    ).order_by(VideoChapter.sequence).all()

    return [
        VideoChapterOut(
            id=c.id, video_id=c.video_id, sequence=c.sequence,
            title=c.title, start_sec=c.start_sec,
            start_display=_format_duration(c.start_sec),
        )
        for c in chapters
    ]


# ═══════════════════════════════════════════════════════════════════
# 4. 观看历史 / 进度
# ═══════════════════════════════════════════════════════════════════

@router.post("/progress", summary="上报播放进度")
def update_progress(
    payload: VideoProgressIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上报当前播放进度（watched_sec / total_sec）"""
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    progress_pct = int((payload.watched_sec / payload.total_sec) * 100) if payload.total_sec > 0 else 0
    progress_pct = min(100, progress_pct)

    history = db.query(VideoWatchHistory).filter(
        VideoWatchHistory.user_id == user.id,
        VideoWatchHistory.video_id == payload.video_id,
    ).first()

    if history:
        history.watched_sec = max(history.watched_sec, payload.watched_sec)
        history.total_sec = payload.total_sec
        history.progress_pct = progress_pct
        history.last_watched_at = func.now()
    else:
        history = VideoWatchHistory(
            user_id=user.id,
            video_id=payload.video_id,
            watched_sec=payload.watched_sec,
            total_sec=payload.total_sec,
            progress_pct=progress_pct,
        )
        db.add(history)

    db.commit()
    return {"message": "进度已更新", "progress_pct": progress_pct}


@router.get("/history", response_model=list[VideoWatchHistoryOut], summary="观看历史")
def watch_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户观看历史"""
    histories = db.query(VideoWatchHistory).filter(
        VideoWatchHistory.user_id == user.id
    ).order_by(VideoWatchHistory.last_watched_at.desc()).offset(offset).limit(limit).all()

    out = []
    for h in histories:
        video = db.query(Video).filter(Video.id == h.video_id).first()
        if video:
            out.append(VideoWatchHistoryOut(
                video_id=h.video_id,
                title=video.title,
                cover_emoji=video.cover_emoji,
                cover_gradient=video.cover_gradient,
                duration_sec=video.duration_sec,
                duration_display=_format_duration(video.duration_sec),
                watched_sec=h.watched_sec,
                progress_pct=h.progress_pct,
                last_watched_at=h.last_watched_at,
            ))
    return out


@router.delete("/history/{video_id}", summary="删除观看记录")
def delete_history(
    video_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除指定视频的观看记录"""
    history = db.query(VideoWatchHistory).filter(
        VideoWatchHistory.user_id == user.id,
        VideoWatchHistory.video_id == video_id,
    ).first()

    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.delete(history)
    db.commit()
    return {"message": "记录已删除"}
