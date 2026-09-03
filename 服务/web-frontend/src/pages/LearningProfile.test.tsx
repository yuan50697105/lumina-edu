import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LearningProfile from './LearningProfile'
import * as client from '../api/client'

vi.mock('../api/client', () => ({
  get: vi.fn(),
}))

const mockXp = {
  total_xp: 2500,
  level: 8,
  current_streak: 15,
  longest_streak: 30,
  next_level_xp: 3000,
  tier_name: '黄金',
}

const mockStats = {
  paths_completed: 3,
  challenges_correct: 45,
  total_study_hours: 28,
  rank_percentile: 15,
}

const mockBadges = [
  {
    id: 'badge-1',
    name: '初露锋芒',
    description: '累计获得 100 XP',
    icon: '🌱',
    condition_type: 'xp_threshold',
    condition_value: 100,
    xp_reward: 0,
    earned: true,
    earned_at: '2026-01-15',
  },
  {
    id: 'badge-2',
    name: '七日成习',
    description: '连续打卡 7 天',
    icon: '🔥',
    condition_type: 'streak',
    condition_value: 7,
    xp_reward: 0,
    earned: true,
    earned_at: '2026-01-20',
  },
  {
    id: 'badge-3',
    name: '月度坚持',
    description: '连续打卡 30 天',
    icon: '🏆',
    condition_type: 'streak',
    condition_value: 30,
    xp_reward: 0,
    earned: false,
    earned_at: null,
  },
]

const mockCheckins = {
  current_streak: 15,
  longest_streak: 30,
  days: [
    { date: '2026-09-01', xp_earned: 10 },
    { date: '2026-09-02', xp_earned: 10 },
    { date: '2026-09-03', xp_earned: 10 },
  ],
}

describe('LearningProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderWithRouter = () =>
    render(
      <MemoryRouter>
        <LearningProfile />
      </MemoryRouter>
    )

  it('shows loading state initially', () => {
    vi.mocked(client.get).mockImplementation(() => new Promise(() => {}))
    renderWithRouter()
    expect(screen.getByText('加载中…')).toBeInTheDocument()
  })

  it('renders user info and tier', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockXp)
      .mockResolvedValueOnce(mockBadges)
      .mockResolvedValueOnce(mockCheckins)
      .mockResolvedValueOnce(mockStats)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('2,500')).toBeInTheDocument()
    })

    expect(screen.getByText('累计 XP')).toBeInTheDocument()
    expect(screen.getByText(/Lv\.8/)).toBeInTheDocument()
  })

  it('renders stats cards', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockXp)
      .mockResolvedValueOnce(mockBadges)
      .mockResolvedValueOnce(mockCheckins)
      .mockResolvedValueOnce(mockStats)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('2,500')).toBeInTheDocument()
    })

    // Look for the stat labels
    expect(screen.getByText('完成路径')).toBeInTheDocument()
    expect(screen.getByText('获得徽章')).toBeInTheDocument()
  })

  it('renders badges', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockXp)
      .mockResolvedValueOnce(mockBadges)
      .mockResolvedValueOnce(mockCheckins)
      .mockResolvedValueOnce(mockStats)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('初露锋芒')).toBeInTheDocument()
    })

    expect(screen.getByText('七日成习')).toBeInTheDocument()
    expect(screen.getByText('🌱')).toBeInTheDocument()
    expect(screen.getByText('🔥')).toBeInTheDocument()
  })

  it('renders check-in calendar', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce(mockXp)
      .mockResolvedValueOnce(mockBadges)
      .mockResolvedValueOnce(mockCheckins)
      .mockResolvedValueOnce(mockStats)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('2,500')).toBeInTheDocument()
    })

    expect(screen.getByText(/近 30 天打卡/)).toBeInTheDocument()
    expect(screen.getByText(/当前连续 15 天/)).toBeInTheDocument()
  })
})
