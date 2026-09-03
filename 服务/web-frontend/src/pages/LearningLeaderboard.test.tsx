import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LearningLeaderboard from './LearningLeaderboard'
import * as client from '../api/client'

vi.mock('../api/client', () => ({
  get: vi.fn(),
}))

const mockLeaderboard = {
  period: 'week',
  entries: [
    { rank: 1, user_id: 'u1', name: '李四', xp: 5000, level: 10, tier_name: '黄金' },
    { rank: 2, user_id: 'u2', name: '王五', xp: 4500, level: 9, tier_name: '黄金' },
    { rank: 3, user_id: 'u3', name: '赵六', xp: 4000, level: 8, tier_name: '白银' },
    { rank: 4, user_id: 'u4', name: '钱七', xp: 3500, level: 7, tier_name: '白银' },
    { rank: 5, user_id: 'u5', name: '孙八', xp: 3000, level: 6, tier_name: '青铜' },
  ],
  my_rank: 10,
}

describe('LearningLeaderboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderWithRouter = () =>
    render(
      <MemoryRouter>
        <LearningLeaderboard />
      </MemoryRouter>
    )

  it('shows loading state initially', () => {
    vi.mocked(client.get).mockImplementation(() => new Promise(() => {}))
    renderWithRouter()
    expect(screen.getByText('加载中…')).toBeInTheDocument()
  })

  it('renders leaderboard title', async () => {
    vi.mocked(client.get).mockResolvedValueOnce(mockLeaderboard)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('排行榜')).toBeInTheDocument()
    })
  })

  it('renders top 3 podium', async () => {
    vi.mocked(client.get).mockResolvedValueOnce(mockLeaderboard)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('李四')).toBeInTheDocument()
    })

    expect(screen.getByText('王五')).toBeInTheDocument()
    expect(screen.getByText('赵六')).toBeInTheDocument()
    expect(screen.getByText('5,000 XP')).toBeInTheDocument()
    expect(screen.getByText('4,500 XP')).toBeInTheDocument()
    expect(screen.getByText('4,000 XP')).toBeInTheDocument()
  })

  it('renders rank list', async () => {
    vi.mocked(client.get).mockResolvedValueOnce(mockLeaderboard)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('李四')).toBeInTheDocument()
    })

    expect(screen.getByText('钱七')).toBeInTheDocument()
    expect(screen.getByText('孙八')).toBeInTheDocument()
    expect(screen.getByText(/3,500/)).toBeInTheDocument()
    expect(screen.getByText(/3,000/)).toBeInTheDocument()
  })

  it('renders my rank bar', async () => {
    vi.mocked(client.get).mockResolvedValueOnce(mockLeaderboard)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('李四')).toBeInTheDocument()
    })

    expect(screen.getByText('#10')).toBeInTheDocument()
    expect(screen.getByText('我')).toBeInTheDocument()
  })

  it('switches between week/month/all periods', async () => {
    const user = userEvent.setup()
    vi.mocked(client.get).mockResolvedValue(mockLeaderboard)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('李四')).toBeInTheDocument()
    })

    // Click "月榜"
    await user.click(screen.getByRole('button', { name: '月榜' }))
    expect(client.get).toHaveBeenCalledWith('/learning/leaderboard?period=month&limit=50')

    // Click "总榜"
    await user.click(screen.getByRole('button', { name: '总榜' }))
    expect(client.get).toHaveBeenCalledWith('/learning/leaderboard?period=all&limit=50')
  })

  it('renders export button', async () => {
    vi.mocked(client.get).mockResolvedValueOnce(mockLeaderboard)

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('李四')).toBeInTheDocument()
    })

    expect(screen.getByText(/导出 CSV/)).toBeInTheDocument()
  })
})
