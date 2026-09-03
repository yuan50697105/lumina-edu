import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LearningPath from './LearningPath'
import * as client from '../api/client'

vi.mock('../api/client', () => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('../utils/tracker', () => ({
  track: vi.fn(),
}))

const mockPath = {
  id: 'path-1',
  title: 'Python 入门闯关',
  description: '从零开始学习 Python',
  category: '编程',
  difficulty: '入门',
  cover_emoji: '🐍',
  cover_gradient: 'linear-gradient(135deg,#3D46C9,#7C3AED)',
  stage_count: 3,
  total_xp: 120,
  learner_count: 156,
  my_progress: 33,
  created_by: '2026-01-01',
}

const mockStages = [
  {
    id: 'stage-1',
    path_id: 'path-1',
    title: '变量与数据类型',
    description: '学习基本变量',
    order_num: 1,
    resource_type: 'reading',
    xp_reward: 40,
    estimated_minutes: 6,
    status: 'completed',
    my_progress: { status: 'completed', xp_earned: 40 },
  },
  {
    id: 'stage-2',
    path_id: 'path-1',
    title: '条件与循环',
    description: '学习控制流',
    order_num: 2,
    resource_type: 'video',
    xp_reward: 50,
    estimated_minutes: 12,
    status: 'in_progress',
    my_progress: null,
  },
  {
    id: 'stage-3',
    path_id: 'path-1',
    title: '小测验',
    description: '测验',
    order_num: 3,
    resource_type: 'quiz',
    xp_reward: 30,
    estimated_minutes: 5,
    status: 'locked',
    my_progress: null,
  },
]

describe('LearningPath', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderWithRouter = (pathId = 'path-1') =>
    render(
      <MemoryRouter initialEntries={[`/learning/paths/${pathId}`]}>
        <Routes>
          <Route path="/learning/paths/:id" element={<LearningPath />} />
        </Routes>
      </MemoryRouter>
    )

  it('shows loading state initially', () => {
    vi.mocked(client.get).mockImplementation(() => new Promise(() => {}))
    renderWithRouter()
    expect(screen.getByText('加载中…')).toBeInTheDocument()
  })

  it('renders path title and progress', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPath)
      .mockResolvedValueOnce(mockStages)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Python 入门闯关')).toBeInTheDocument()
    })

    expect(screen.getByText(/完成 1/)).toBeInTheDocument()
    expect(screen.getAllByText(/3 关/).length).toBeGreaterThanOrEqual(1)
  })

  it('renders stage nodes', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPath)
      .mockResolvedValueOnce(mockStages)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText(/变量与数据类型/).length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getAllByText(/条件与循环/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/小测验/)).toBeInTheDocument()
  })

  it('selects current stage by default', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPath)
      .mockResolvedValueOnce(mockStages)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText(/变量与数据类型/).length).toBeGreaterThanOrEqual(1)
    })

    // Should auto-select the in_progress stage
    expect(screen.getAllByText(/条件与循环/).length).toBeGreaterThanOrEqual(1)
  })

  it('shows path not found message', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce([])

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('路径不存在')).toBeInTheDocument()
    })
  })
})
