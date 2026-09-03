# ============================================
# Lumina 墨光 · D-06 自主学习 + D-08 视频录播 单元测试
# 表结构 / schema 校验 / OpenAPI 注册
# 纯内存断言，不连数据库
# ============================================
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.database import Base
from app.models import (
    LearningPath, LearningPathNode, LearningPathProgress,
    UserXP, CheckInRecord, Badge, UserBadge,
    Challenge, ChallengeAttempt,
    Video, VideoChapter, VideoNote, VideoWatchHistory,
)
from app.schemas import (
    LearningPathOut, LearningPathNodeOut, UserXPOut,
    CheckInOut, CheckInCalendarOut,
    BadgeOut, ChallengeOut, ChallengeStartOut, ChallengeSubmitIn, ChallengeResultOut,
    LeaderboardOut, LeaderboardEntry, LearningStatsOut,
    VideoOut, VideoDetailOut, VideoChapterOut,
    VideoNoteCreate, VideoNoteOut,
    VideoWatchHistoryOut, VideoProgressIn,
)


@pytest.fixture(scope="module")
def tables():
    return set(Base.metadata.tables.keys())


# ───────────────────────────────────────────────────────────────
# D-06 表定义
# ───────────────────────────────────────────────────────────────
class TestD06TableDefinitions:

    def test_tables_exist(self, tables):
        required = {
            "learning_paths", "learning_path_nodes", "learning_path_progress",
            "user_xp", "check_in_records", "badges", "user_badges",
            "challenges", "challenge_attempts",
        }
        assert required.issubset(tables)

    def test_learning_path_columns(self):
        mapper = inspect(LearningPath)
        cols = {c.key for c in mapper.columns}
        assert {"id", "title", "description", "category", "difficulty",
                "total_nodes", "total_xp", "learner_count", "published"}.issubset(cols)

    def test_learning_path_node_columns(self):
        mapper = inspect(LearningPathNode)
        cols = {c.key for c in mapper.columns}
        assert {"id", "path_id", "sequence", "node_type", "title",
                "duration_min", "xp_reward", "content"}.issubset(cols)

    def test_learning_path_progress_unique(self):
        names = [getattr(c, "name", "") for c in LearningPathProgress.__table__.constraints]
        assert "uq_user_node_progress" in names

    def test_user_xp_primary_key(self):
        mapper = inspect(UserXP)
        assert mapper.columns["user_id"].primary_key

    def test_checkin_unique(self):
        names = [getattr(c, "name", "") for c in CheckInRecord.__table__.constraints]
        assert "uq_user_checkin_date" in names

    def test_challenge_questions_json(self):
        mapper = inspect(Challenge)
        assert str(mapper.columns["questions"].type) == "JSON"


# ───────────────────────────────────────────────────────────────
# D-08 表定义
# ───────────────────────────────────────────────────────────────
class TestD08TableDefinitions:

    def test_tables_exist(self, tables):
        required = {"videos", "video_chapters", "video_notes", "video_watch_history"}
        assert required.issubset(tables)

    def test_video_columns(self):
        mapper = inspect(Video)
        cols = {c.key for c in mapper.columns}
        assert {"id", "course_id", "title", "description", "category",
                "duration_sec", "video_url", "view_count", "published"}.issubset(cols)

    def test_video_chapter_unique(self):
        names = [getattr(c, "name", "") for c in VideoChapter.__table__.constraints]
        assert "uq_video_chapter_seq" in names

    def test_video_note_columns(self):
        mapper = inspect(VideoNote)
        cols = {c.key for c in mapper.columns}
        assert {"id", "user_id", "video_id", "timestamp_sec", "content"}.issubset(cols)

    def test_video_watch_history_unique(self):
        names = [getattr(c, "name", "") for c in VideoWatchHistory.__table__.constraints]
        assert "uq_user_video_history" in names


# ───────────────────────────────────────────────────────────────
# D-06 Schema 校验
# ───────────────────────────────────────────────────────────────
class TestD06Schemas:

    def test_learning_path_out(self):
        out = LearningPathOut(
            id=uuid.uuid4(), title="Python 入门", category="编程",
            difficulty="入门", total_nodes=10, total_xp=500,
            learner_count=100, created_at=datetime.now(timezone.utc),
        )
        assert out.progress_pct is None
        assert out.total_nodes == 10

    def test_learning_path_node_out(self):
        out = LearningPathNodeOut(
            id=uuid.uuid4(), path_id=uuid.uuid4(), sequence=1,
            node_type="reading", title="变量与类型",
            xp_reward=40, status="current",
        )
        assert out.status == "current"
        assert out.xp_earned == 0

    def test_user_xp_out(self):
        out = UserXPOut(
            user_id=uuid.uuid4(), total_xp=2680, level=27,
            streak_days=7, xp_to_next_level=20, level_progress_pct=80.0,
        )
        assert out.level == 27
        assert out.level_progress_pct == 80.0

    def test_checkin_out(self):
        out = CheckInOut(success=True, message="打卡成功", xp_awarded=10, streak_days=7)
        assert out.success is True
        assert out.already_checked is False

    def test_checkin_already_checked(self):
        out = CheckInOut(success=False, message="今日已打卡", already_checked=True)
        assert out.already_checked is True

    def test_badge_out(self):
        out = BadgeOut(
            id=uuid.uuid4(), code="streak_7", name="七日之约",
            icon="🔥", condition_type="streak", condition_value=7,
            earned=True, earned_at=datetime.now(timezone.utc),
        )
        assert out.earned is True

    def test_challenge_out(self):
        out = ChallengeOut(
            id=uuid.uuid4(), title="列表推导式挑战",
            question_count=8, max_attempts=3, pass_score=60, xp_reward=80,
            attempts_left=2,
        )
        assert out.attempts_left == 2

    def test_challenge_submit_in(self):
        payload = ChallengeSubmitIn(
            attempt_id=uuid.uuid4(),
            answers=[{"index": 0, "answer": "A"}, {"index": 1, "answer": "B"}],
        )
        assert len(payload.answers) == 2

    def test_challenge_result_out(self):
        out = ChallengeResultOut(
            attempt_id=uuid.uuid4(), score=75, passed=True,
            xp_earned=80, correct_count=6, total_count=8,
            answers_review=[],
        )
        assert out.passed is True

    def test_leaderboard_out(self):
        out = LeaderboardOut(
            entries=[
                LeaderboardEntry(rank=1, user_id=uuid.uuid4(), name="Alice",
                                 total_xp=5000, level=50, streak_days=30),
            ],
            my_rank=5, total_users=100,
        )
        assert out.my_rank == 5

    def test_learning_stats_out(self):
        out = LearningStatsOut(
            total_xp=2680, level=27, streak_days=7,
            paths_completed=3, paths_total=8,
            badges_earned=6, badges_total=18,
            challenges_passed=10, videos_watched=15, videos_total=50,
        )
        assert out.paths_completed == 3


# ───────────────────────────────────────────────────────────────
# D-08 Schema 校验
# ───────────────────────────────────────────────────────────────
class TestD08Schemas:

    def test_video_out(self):
        out = VideoOut(
            id=uuid.uuid4(), title="数据结构与算法",
            duration_sec=2412, view_count=1284,
            created_at=datetime.now(timezone.utc),
        )
        assert out.duration_sec == 2412
        assert out.duration_display is None
        assert out.progress_pct == 0

    def test_video_detail_out(self):
        out = VideoDetailOut(
            id=uuid.uuid4(), title="Pandas 实战",
            duration_sec=1445, view_count=906,
            created_at=datetime.now(timezone.utc),
            chapters=[], notes=[],
        )
        assert len(out.chapters) == 0

    def test_video_chapter_out(self):
        out = VideoChapterOut(
            id=uuid.uuid4(), video_id=uuid.uuid4(), sequence=1,
            title="本章导览", start_sec=0, start_display="00:00",
        )
        assert out.start_sec == 0

    def test_video_note_create_validation(self):
        with pytest.raises(ValidationError):
            VideoNoteCreate(video_id=uuid.uuid4(), timestamp_sec=-1, content="test")
        with pytest.raises(ValidationError):
            VideoNoteCreate(video_id=uuid.uuid4(), timestamp_sec=100, content="")
        payload = VideoNoteCreate(video_id=uuid.uuid4(), timestamp_sec=756, content="笔记内容")
        assert payload.timestamp_sec == 756

    def test_video_note_out(self):
        out = VideoNoteOut(
            id=uuid.uuid4(), video_id=uuid.uuid4(),
            timestamp_sec=756, timestamp_display="12:36",
            content="二分查找边界", created_at=datetime.now(timezone.utc),
        )
        assert out.timestamp_display == "12:36"

    def test_video_watch_history_out(self):
        out = VideoWatchHistoryOut(
            video_id=uuid.uuid4(), title="数据结构",
            duration_sec=2412, watched_sec=756, progress_pct=31,
            last_watched_at=datetime.now(timezone.utc),
        )
        assert out.progress_pct == 31

    def test_video_progress_in(self):
        payload = VideoProgressIn(video_id=uuid.uuid4(), watched_sec=1200, total_sec=2412)
        assert payload.watched_sec == 1200
        with pytest.raises(ValidationError):
            VideoProgressIn(video_id=uuid.uuid4(), watched_sec=-1, total_sec=100)


# ───────────────────────────────────────────────────────────────
# OpenAPI 注册
# ───────────────────────────────────────────────────────────────
class TestD06D08OpenAPIRegistration:

    @pytest.fixture(autouse=True)
    def _load_app(self):
        from app.main import app
        self.app = app

    def _paths(self):
        schema = self.app.openapi()
        return schema.get("paths", {})

    def test_learning_paths_registered(self):
        paths = self._paths()
        assert "/api/v1/learning/paths" in paths
        assert "/api/v1/learning/paths/{path_id}" in paths
        assert "/api/v1/learning/paths/{path_id}/join" in paths

    def test_learning_xp_registered(self):
        paths = self._paths()
        assert "/api/v1/learning/xp" in paths
        assert "/api/v1/learning/checkin" in paths
        assert "/api/v1/learning/checkin/calendar" in paths

    def test_learning_badges_registered(self):
        paths = self._paths()
        assert "/api/v1/learning/badges" in paths

    def test_learning_challenges_registered(self):
        paths = self._paths()
        assert "/api/v1/learning/challenges/{challenge_id}" in paths
        assert "/api/v1/learning/challenges/{challenge_id}/start" in paths
        assert "/api/v1/learning/challenges/attempts/{attempt_id}/submit" in paths

    def test_learning_leaderboard_registered(self):
        paths = self._paths()
        assert "/api/v1/learning/leaderboard" in paths
        assert "/api/v1/learning/stats" in paths

    def test_videos_registered(self):
        paths = self._paths()
        assert "/api/v1/videos" in paths
        assert "/api/v1/videos/{video_id}" in paths
        assert "/api/v1/videos/notes" in paths
        assert "/api/v1/videos/notes/{video_id}" in paths
        assert "/api/v1/videos/notes/{note_id}" in paths
        assert "/api/v1/videos/{video_id}/chapters" in paths
        assert "/api/v1/videos/progress" in paths
        assert "/api/v1/videos/history" in paths
        assert "/api/v1/videos/history/{video_id}" in paths

    def test_total_count_increases(self):
        schema = self.app.openapi()
        paths_count = len(schema["paths"])
        ops_count = sum(len(m) for m in schema["paths"].values())
        # D-07 基线 141 paths / 180 ops → D-06/D-08 新增 21 paths / 21 ops
        assert paths_count >= 160, f"预期 >=160 路径，实际 {paths_count}"
        assert ops_count >= 195, f"预期 >=195 操作，实际 {ops_count}"
