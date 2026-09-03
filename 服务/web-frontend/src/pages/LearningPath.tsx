// ============================================
// Lumina 墨光 · D-06 路径地图
// 自主学习与闯关奖励系统 · 关卡导航
// ============================================
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { get, post } from '../api/client'
import type { LearningPath, LearningStage, StageResourceType } from '../api/types'
import { track } from '../utils/tracker'

interface StageDetail extends LearningStage {
  my_progress?: {
    status: string
    xp_earned: number
    quiz_score?: number | null
  } | null
}

export default function LearningPath() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [path, setPath] = useState<LearningPath | null>(null)
  const [stages, setStages] = useState<StageDetail[]>([])
  const [selectedStage, setSelectedStage] = useState<StageDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [modalXp, setModalXp] = useState(0)

  useEffect(() => {
    if (!id) return
    ;(async () => {
      try {
        const [pathRes, stagesRes] = await Promise.all([
          get<LearningPath>(`/learning/paths/${id}`),
          get<StageDetail[]>(`/learning/paths/${id}/nodes`),
        ])
        setPath(pathRes)
        setStages(stagesRes)
        // 默认选中当前关（in_progress）或第一个未完成的
        const current = stagesRes.find((s) => s.status === 'in_progress' || s.status === 'unlocked')
        if (current) setSelectedStage(current)
        else if (stagesRes.length > 0) setSelectedStage(stagesRes[0])
      } finally {
        setLoading(false)
      }
    })()
  }, [id])

  async function handleStartStage() {
    if (!selectedStage || !id) return
    track('learning.stage_start', { stage_id: selectedStage.id, path_id: id })

    // 如果是测验或挑战类型，直接进入答题
    if (selectedStage.resource_type === 'quiz' || selectedStage.resource_type === 'challenge') {
      navigate(`/learning/stages/${selectedStage.id}`)
      return
    }

    // 文章/视频类型：模拟完成（实际应该记录进度）
    try {
      const res = await post<{ xp_earned: number; next_stage_id?: string }>(
        `/learning/stages/${selectedStage.id}/complete`,
        {}
      )
      setModalXp(res.xp_earned)
      setShowModal(true)
      track('learning.stage_complete', { stage_id: selectedStage.id, xp_earned: res.xp_earned })

      // 更新本地状态
      setStages((prev) =>
        prev.map((s) => {
          if (s.id === selectedStage.id) {
            return { ...s, status: 'completed', my_progress: { status: 'completed', xp_earned: res.xp_earned } }
          }
          if (res.next_stage_id && s.id === res.next_stage_id && s.status === 'locked') {
            return { ...s, status: 'unlocked' }
          }
          return s
        })
      )
    } catch (err) {
      console.error('完成关卡失败', err)
    }
  }

  if (loading) return <div className="muted">加载中…</div>
  if (!path) return <div className="muted">路径不存在</div>

  const completedCount = stages.filter((s) => s.status === 'completed').length
  const progressPercent = Math.round((completedCount / stages.length) * 100)

  return (
    <div>
      <div className="path-layout">
        {/* 左侧：地图 */}
        <div className="card map-card">
          <div className="map-head">
            <div>
              <h2 className="page-title" style={{ marginBottom: 4 }}>
                {path.title}
              </h2>
              <div className="map-meta">
                {path.stage_count} 关 · 总奖励 <span className="xp-hl">{path.total_xp} XP</span> ·{' '}
                {path.learner_count} 人正在学习 · 完成 {completedCount}/{path.stage_count}
              </div>
            </div>
            <span className="pill cobalt">{path.category} · {path.difficulty}</span>
          </div>

          <div className="map-scroll">
            {/* 起点 */}
            <div className="start-node">
              <div className="bigdot" />
              <div className="node-label">起点 · Start</div>
            </div>

            {/* 关卡节点 */}
            <div className="node-list">
              {stages.map((stage, idx) => (
                <StageNode
                  key={stage.id}
                  stage={stage}
                  index={idx}
                  selected={selectedStage?.id === stage.id}
                  onClick={() => {
                    if (stage.status === 'locked') {
                      alert('🔒 该关卡尚未解锁，请先完成前面的关卡')
                      return
                    }
                    setSelectedStage(stage)
                    track('learning.stage_view', { stage_id: stage.id })
                  }}
                />
              ))}
            </div>

            {/* 终点 */}
            <div className="end-node">
              <div className="trophy">🏆</div>
              <div className="node-label">
                终点 · 完成全部 {path.stage_count} 关解锁 <b>「路径征服者」</b>徽章 + <b>{path.total_xp} XP</b>
              </div>
            </div>
          </div>
        </div>

        {/* 右侧：详情面板 */}
        {selectedStage && (
          <aside className="card detail-card">
            <div className="detail-type">当前关卡详情 · LEVEL {String(selectedStage.order_num).padStart(2, '0')}</div>
            <h3 className="detail-title">
              {getTypeIcon(selectedStage.resource_type)} {selectedStage.title}
            </h3>
            <div className="detail-facts">
              <span className="pill cobalt">{getTypeLabel(selectedStage.resource_type)}</span>
              <span className="pill gray">⏱ {selectedStage.estimated_minutes} 分钟</span>
              <span className="pill yellow">+{selectedStage.xp_reward} XP</span>
              {selectedStage.status === 'completed' ? (
                <span className="pill green">✅ 已通过</span>
              ) : (
                <span className="pill red">🎯 进行中</span>
              )}
            </div>

            {/* 预览区 */}
            <div className="detail-preview">
              {selectedStage.resource_type === 'article' && (
                <div className="preview-article">
                  <b>正文预览</b>
                  <br />
                  {selectedStage.description || '本节内容将通过富文本形式展示……'}
                  <div className="preview-meta">
                    预计 {selectedStage.estimated_minutes} 分钟
                  </div>
                </div>
              )}
              {selectedStage.resource_type === 'video' && (
                <div className="preview-video">
                  <div className="play-btn">▶</div>
                  <div className="video-meta">
                    视频占位 · 1080P · {selectedStage.estimated_minutes}:00 · 支持字幕与倍速
                  </div>
                </div>
              )}
              {selectedStage.resource_type === 'quiz' && (
                <div className="preview-quiz">
                  <b>测验预览 · {selectedStage.quiz_questions?.length ?? 0} 题</b>
                  <div style={{ marginTop: 8 }}>点击「开始闯关」进入答题面板</div>
                </div>
              )}
              {selectedStage.resource_type === 'challenge' && (
                <div className="preview-challenge">
                  <b>⚔️ 挑战任务</b>
                  <br />
                  {selectedStage.description || '综合挑战，限时完成'}
                  <div className="preview-meta">
                    限时 {selectedStage.estimated_minutes} 分钟 · 最多 3 次提交
                  </div>
                </div>
              )}
            </div>

            {/* 操作按钮 */}
            <div className="detail-actions">
              {selectedStage.status === 'completed' ? (
                <>
                  <button className="btn" onClick={() => alert('原型演示：重新学习该关卡')}>
                    重新学习
                  </button>
                  <button className="btn primary" onClick={handleNextStage}>
                    下一关 →
                  </button>
                </>
              ) : (
                <button className="btn primary lg" onClick={handleStartStage}>
                  ⚔️ 开始闯关
                </button>
              )}
              <button className="btn" onClick={() => alert('已加入书架，可在「我的学习」查看')}>
                📌 稍后再学
              </button>
            </div>

            <div className="compliance-hint" style={{ marginTop: 16 }}>
              ⚖️ 挑战题 AI 预批改结果仅供参考，成绩以教师复核为准
            </div>
          </aside>
        )}
      </div>

      {/* 完成弹窗 */}
      {showModal && (
        <div className="modal-mask" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-badge">🎉</div>
            <h3>关卡完成！</h3>
            <div className="modal-xp">
              +{modalXp}
              <small> XP</small>
            </div>
            <div className="modal-sub">
              第 {selectedStage?.order_num} 关「{selectedStage?.title}」
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => alert('原型演示：生成战绩分享卡片')}>
                分享战绩
              </button>
              <button className="btn primary" onClick={handleNextStage}>
                下一关 →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  function handleNextStage() {
    setShowModal(false)
    const currentIdx = stages.findIndex((s) => s.id === selectedStage?.id)
    if (currentIdx >= 0 && currentIdx < stages.length - 1) {
      const nextStage = stages[currentIdx + 1]
      if (nextStage.status !== 'locked') {
        setSelectedStage(nextStage)
      }
    }
  }
}

function StageNode({ stage, index, selected, onClick }: {
  stage: StageDetail
  index: number
  selected: boolean
  onClick: () => void
}) {
  const stateClass = stage.status === 'completed' ? 'done' : stage.status === 'locked' ? 'locked' : 'current'

  return (
    <div className={`node ${stateClass} ${selected ? 'selected' : ''}`} onClick={onClick}>
      <div className="node-dot">
        {stage.status === 'locked' ? '🔒' : stage.status === 'completed' ? '✓' : getTypeIcon(stage.resource_type)}
      </div>
      <div className="node-body">
        <div className="node-seq">
          LEVEL {String(stage.order_num).padStart(2, '0')} · {getTypeLabel(stage.resource_type)}
        </div>
        <div className="node-title">
          {getTypeIcon(stage.resource_type)} {stage.title}
        </div>
        <div className="node-tags">
          {stage.status === 'completed' && <span className="pill green">✅ 已完成</span>}
          {stage.status === 'in_progress' && <span className="pill cobalt">🎯 当前关</span>}
          {stage.status === 'unlocked' && <span className="pill cobalt">🔓 可开始</span>}
          {stage.status === 'locked' && <span className="pill gray">🔒 未解锁</span>}
          <span className="pill yellow">+{stage.xp_reward} XP</span>
          <span className="node-mins">⏱ 约 {stage.estimated_minutes} 分钟</span>
        </div>
      </div>
    </div>
  )
}

function getTypeIcon(type: StageResourceType): string {
  const icons: Record<StageResourceType, string> = {
    article: '📖',
    video: '🎬',
    quiz: '📝',
    challenge: '⚔️',
  }
  return icons[type] ?? '📖'
}

function getTypeLabel(type: StageResourceType): string {
  const labels: Record<StageResourceType, string> = {
    article: '📖 文章',
    video: '🎬 视频',
    quiz: '📝 测验',
    challenge: '⚔️ 挑战',
  }
  return labels[type] ?? '📖 文章'
}
