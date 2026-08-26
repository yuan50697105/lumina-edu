import { useEffect, useState } from 'react'
import { get, patch, post } from '../api/client'
import type { AiModel, AiProvider, ApiStyle, ModelCreate } from '../api/types'
import { track } from '../utils/tracker'

const TASK_OPTIONS = ['chat', 'grade', 'generate', 'vl', 'speech']
const STYLES: ApiStyle[] = ['openai', 'anthropic', 'gemini']

export default function AdminModels() {
  const [models, setModels] = useState<AiModel[]>([])
  const [providers, setProviders] = useState<AiProvider[]>([])
  const [err, setErr] = useState('')

  const empty = { provider_name: 'qwen', model_name: '', display_name: '', task_types: ['chat'] }
  const [form, setForm] = useState<ModelCreate & { task_types: string[] }>({ ...empty })
  const [saving, setSaving] = useState(false)

  function reload() {
    Promise.all([
      get<AiModel[]>('/ai/gateway/models'),
      get<AiProvider[]>('/ai/gateway/providers'),
    ])
      .then(([m, p]) => {
        setModels(m ?? [])
        setProviders(p ?? [])
      })
      .catch((e) => setErr((e as Error).message))
  }

  useEffect(reload, [])

  async function toggleModel(m: AiModel) {
    await patch(`/ai/gateway/models/${m.id}`, { enabled: !m.enabled }).catch((e) =>
      alert((e as Error).message),
    )
    track('model.toggle', { model: m.model_name, enabled: !m.enabled })
    reload()
  }

  async function createModel(e: React.FormEvent) {
    e.preventDefault()
    if (!form.model_name.trim() || !form.display_name.trim()) return
    setSaving(true)
    try {
      await post<AiModel>('/ai/gateway/models', {
        provider_name: form.provider_name,
        model_name: form.model_name.trim(),
        display_name: form.display_name.trim(),
        task_types: form.task_types,
        priority: 50,
        cost_per_1k_tokens: '0.01',
        api_style: form.api_style ?? 'openai',
      })
      track('model.register', { model: form.model_name, style: form.api_style })
      setForm({ ...empty })
      reload()
    } catch (ex) {
      alert((ex as Error).message)
    } finally {
      setSaving(false)
    }
  }

  function toggleTask(t: string) {
    setForm((f) => ({
      ...f,
      task_types: f.task_types.includes(t)
        ? f.task_types.filter((x) => x !== t)
        : [...f.task_types, t],
    }))
  }

  return (
    <div>
      <h1 className="page-title">模型池配置（运营端）</h1>
      <p className="muted">供应商与模型完全由运营端自定义 —— 注册厂商 → 注册模型 → 注入 Key 后即可被智能路由使用。</p>
      {err && <p className="error">{err}</p>}

      <section>
        <h2 className="section-title">供应商（{providers.length}）</h2>
        <table className="table">
          <thead>
            <tr>
              <th>名称</th>
              <th>厂商</th>
              <th>API Base URL（endpoint_base）</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {providers.map((p) => (
              <tr key={p.id}>
                <td>
                  <b>{p.name}</b>
                </td>
                <td>{p.display_name}</td>
                <td className="mono">{p.endpoint_base ?? '—'}</td>
                <td>
                  <span className={`pill ${p.enabled ? 'ok' : ''}`}>{p.enabled ? '启用' : '停用'}</span>
                </td>
              </tr>
            ))}
            {providers.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  暂无供应商，请先注册（POST /ai/gateway/providers）
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section>
        <h2 className="section-title">模型（{models.length}）</h2>
        <table className="table">
          <thead>
            <tr>
              <th>模型</th>
              <th>显示名</th>
              <th>协议</th>
              <th>任务类型</th>
              <th>价格</th>
              <th>优先级</th>
              <th>启用</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => (
              <tr key={m.id}>
                <td className="mono">{m.model_name}</td>
                <td>{m.display_name}</td>
                <td>
                  <span className={`pill style-${m.api_style ?? 'openai'}`}>{m.api_style ?? 'openai'}</span>
                </td>
                <td>{m.task_types.join(' / ')}</td>
                <td>{m.cost_per_1k_tokens ?? 0}</td>
                <td>{m.priority}</td>
                <td>
                  <button className={`btn tiny ${m.enabled ? 'ghost' : 'primary'}`} onClick={() => toggleModel(m)} data-track="model-toggle">
                    {m.enabled ? '停用' : '启用'}
                  </button>
                </td>
              </tr>
            ))}
            {models.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  空池 —— 用下方表单注册第一个模型
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2 className="section-title">注册模型</h2>
        <form className="form-grid" onSubmit={createModel}>
          <label className="field">
            供应商
            <select value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })}>
              {providers.map((p) => (
                <option key={p.id} value={p.name}>
                  {p.display_name}（{p.name}）
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            协议风格（api_style）
            <select
              value={form.api_style ?? 'openai'}
              onChange={(e) => setForm({ ...form, api_style: e.target.value as ApiStyle })}
            >
              {STYLES.map((s) => (
                <option key={s} value={s}>
                  {s} — {s === 'openai' ? 'Bearer' : s === 'anthropic' ? 'x-api-key' : 'x-goog-api-key'}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            模型名（model_name）
            <input
              value={form.model_name}
              onChange={(e) => setForm({ ...form, model_name: e.target.value })}
              placeholder="qwen-max / claude-3-5-sonnet / gemini-2.0-flash"
            />
          </label>
          <label className="field">
            显示名
            <input
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              placeholder="通义千问 Max"
            />
          </label>
          <div className="field">
            任务类型
            <div className="chips">
              {TASK_OPTIONS.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`chip ${form.task_types.includes(t) ? 'on' : ''}`}
                  onClick={() => toggleTask(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="form-actions">
            <button className="btn primary" disabled={saving || !form.model_name.trim() || !form.display_name.trim()} data-track="model-create">
              {saving ? '注册中…' : '注册模型'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}