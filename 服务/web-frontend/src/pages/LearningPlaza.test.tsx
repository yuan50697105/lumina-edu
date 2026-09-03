import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LearningPlaza from './LearningPlaza'
import * as client from '../api/client'

// Mock API client
vi.mock('../api/client', () => ({
  get: vi.fn(),
  post: vi.fn(),
}))

// Mock tracker
vi.mock('../utils/tracker', () => ({
  track: vi.fn(),
}))

const mockPaths = {
  code: 200,
  data: [
    {
      id: 'path-1',
      title: 'Python 入门闯关',
      description: '从零开始学习 Python',
      category: '编程',
      difficulty: '入门',
      cover_emoji: '🐍',
      cover_gradient: 'linear-gradient(135deg,#3D46C9,#7C3AED)',
      stage_count: 12,
      total_xp: 630,
      learner_count: 156,
      my_progress: 25,
      created_by: '2026-01-01',
    },
    {
      id: 'path-2',
      title: 'UI 设计思维',
      description: '培养设计思维',
      category: '设计',
      difficulty: '入门',
      cover_emoji: '🎨',
      cover_gradient: 'linear-gradient(135deg,#E85D3A,#F5B800)',
      stage_count: 8,
      total_xp: 410,
      learner_count: 89,
      my_progress: null,
      created_by: '2026-01-02',
    },
  ],
  pagination: { offset: 0, limit: 50, total: 2, has_more: false },
}

const mockXp = {
  total_xp: 1250,
  current_streak: 7,
  longest_streak: 15,
  level: 5,
  tier: 't3',
  next_level_xp: 2000,
}

describe('LearningPlaza', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderWithRouter = () =>
    render(
      <MemoryRouter>
        <LearningPlaza />
      </MemoryRouter>
    )

  it('shows loading state initially', () => {
    vi.mocked(client.get).mockImplementation(() => new Promise(() => {})) // Never resolves
    renderWithRouter()
    expect(screen.getByText('加载中…')).toBeInTheDocument()
  })

  it('renders hero section with XP and streak after loading', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths) // paths
      .mockResolvedValueOnce(mockXp) // xp

    renderWithRouter()

    await waitFor(() => {
      expect(screen.queryByText('加载中…')).not.toBeInTheDocument()
    })

    expect(screen.getByText('学习')).toBeInTheDocument()
    expect(screen.getByText('1,250')).toBeInTheDocument()
    expect(screen.getByText('累计 XP')).toBeInTheDocument()
    expect(screen.getByText('🔥 7 天')).toBeInTheDocument()
    expect(screen.getByText('连续打卡')).toBeInTheDocument()
  })

  it('renders path cards', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getByText('UI 设计思维')).toBeInTheDocument()
    expect(screen.getAllByText('630 XP').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('156 人学习')).toBeInTheDocument()
  })

  it('renders filter bar', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getByText('分类')).toBeInTheDocument()
    expect(screen.getByText('难度')).toBeInTheDocument()
    expect(screen.getByText('排序')).toBeInTheDocument()
    expect(screen.getAllByText('全部').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('编程').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('设计').length).toBeGreaterThanOrEqual(1)
  })

  it('renders daily challenge card', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getByText(/今日挑战/)).toBeInTheDocument()
    expect(screen.getByText('立即作答')).toBeInTheDocument()
  })

  it('renders compliance hint', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getByText(/个性化推荐/)).toBeInTheDocument()
  })

  it('shows continue learning card when path has progress', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getByText('▶ 继续学习')).toBeInTheDocument()
    expect(screen.getByText('25% 完成')).toBeInTheDocument()
  })

  it('filters paths by category', async () => {
    const user = userEvent.setup()
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    })

    // Click "编程" filter
    await user.click(screen.getByRole('button', { name: '编程' }))

    // Python path should still be visible (in both card and continue learning)
    expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    // UI design should be filtered out
    expect(screen.queryByText('UI 设计思维')).not.toBeInTheDocument()
  })

  it('shows empty state when no paths match filter', async () => {
    const user = userEvent.setup()
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getAllByText('Python 入门闯关').length).toBeGreaterThanOrEqual(1)
    })

    // Click "语言" filter (no paths in this category)
    await user.click(screen.getByRole('button', { name: '语言' }))

    expect(screen.getByText(/该筛选组合下暂无路径/)).toBeInTheDocument()
  })

  it('handles check-in button click', async () => {
    const user = userEvent.setup()
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockPaths)
      .mockResolvedValueOnce(mockXp)
    vi.mocked(client.post).mockResolvedValueOnce({
      checked_in: true,
      xp_earned: 10,
      new_streak: 8,
    })

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('📅 今日打卡')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '📅 今日打卡' }))

    await waitFor(() => {
      expect(screen.getByText('✅ 已打卡')).toBeInTheDocument()
    })

    expect(client.post).toHaveBeenCalledWith('/learning/checkin', {})
  })
})
