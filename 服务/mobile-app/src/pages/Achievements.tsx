// ============================================
// Lumina 墨光 · D-06 成就页
// 统计 + 打卡日历 + 徽章墙
// ============================================
import { useEffect, useState, useCallback } from 'react'
import {
  View, Text, ScrollView, StyleSheet, ActivityIndicator,
  TouchableOpacity, Alert,
} from 'react-native'
import { get } from '../api/client'
import type { LearningStats, CheckInCalendar, Badge } from '../api/types'

export default function Achievements() {
  const [stats, setStats] = useState<LearningStats | null>(null)
  const [calendar, setCalendar] = useState<CheckInCalendar | null>(null)
  const [badges, setBadges] = useState<Badge[]>([])
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    try {
      const [statsData, calData, badgeData] = await Promise.all([
        get<LearningStats>('/learning/stats'),
        get<CheckInCalendar>('/learning/checkin/calendar?days=30'),
        get<Badge[]>('/learning/badges'),
      ])
      setStats(statsData)
      setCalendar(calData)
      setBadges(badgeData)
    } catch (e) {
      console.error('loadData', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const showBadgeDetail = (b: Badge) => {
    Alert.alert(
      `${b.icon} ${b.name}`,
      `${b.description || ''}\n\n获取条件：${b.condition_type} ≥ ${b.condition_value}\n\n${b.earned ? '✅ 已获得' : '🔒 未获得'}`,
      [{ text: '知道啦' }]
    )
  }

  if (loading) {
    return <View style={s.center}><ActivityIndicator /></View>
  }

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      {/* 用户卡片 */}
      <View style={s.meCard}>
        <View style={s.avatar}>
          <Text style={s.avatarTxt}>墨</Text>
        </View>
        <View style={s.meInfo}>
          <Text style={s.nick}>墨小光 <Text style={s.level}>LV.{stats?.level || 1}</Text></Text>
          <View style={s.xpBar}>
            <Text style={s.xpLabel}>距离 LV.{(stats?.level || 1) + 1}</Text>
            <Text style={s.xpLabel}>{stats?.total_xp || 0} / {((stats?.level || 1) * 100)} XP</Text>
          </View>
          <View style={s.bar}>
            <View style={[s.barFill, { width: `${80}%` as any }]} />
          </View>
        </View>
      </View>

      {/* 统计网格 */}
      <View style={s.statGrid}>
        <View style={s.stat}>
          <Text style={[s.statVal, { color: '#3D46C9' }]}>{stats?.total_xp || 0}</Text>
          <Text style={s.statLabel}>总 XP</Text>
        </View>
        <View style={s.stat}>
          <Text style={[s.statVal, { color: '#E85D3A' }]}>{stats?.streak_days || 0} 天</Text>
          <Text style={s.statLabel}>连续打卡</Text>
        </View>
        <View style={s.stat}>
          <Text style={[s.statVal, { color: '#2A7F4F' }]}>{stats?.paths_completed || 0} / {stats?.paths_total || 0}</Text>
          <Text style={s.statLabel}>完成路径</Text>
        </View>
        <View style={s.stat}>
          <Text style={[s.statVal, { color: '#7C3AED' }]}>{stats?.badges_earned || 0} / {stats?.badges_total || 0}</Text>
          <Text style={s.statLabel}>获得徽章</Text>
        </View>
      </View>

      {/* 打卡日历 */}
      <Text style={s.secTitle}>打卡日历 <Text style={s.secSmall}>近 30 天</Text></Text>
      <View style={s.calCard}>
        <Text style={s.calHead}>🔥 本月已打卡 <Text style={s.calNum}>{calendar?.total_checked || 0}</Text> 天</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.calRow}>
          {calendar?.days.map((d, i) => (
            <View key={i} style={s.calDay}>
              <Text style={s.calDate}>{d.date.slice(-2)}</Text>
              <View style={[s.calCircle, d.checked && s.calHit]}>
                <Text style={s.calTxt}>{d.checked ? '✓' : ''}</Text>
              </View>
            </View>
          ))}
        </ScrollView>
      </View>

      {/* 徽章墙 */}
      <Text style={s.secTitle}>徽章墙 <Text style={s.secSmall}>TAP 查看详情</Text></Text>
      <View style={s.badgeGrid}>
        {badges.map(b => (
          <TouchableOpacity
            key={b.id}
            style={[s.badge, b.earned && s.badgeEarned]}
            onPress={() => showBadgeDetail(b)}
          >
            <View style={[s.badgeIcon, !b.earned && s.badgeLocked]}>
              <Text style={s.badgeEmoji}>{b.icon}</Text>
            </View>
            <Text style={s.badgeName}>{b.name}</Text>
            <Text style={s.badgeStatus}>{b.earned ? '已获得' : '未获得'}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAF6EC' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#FAF6EC' },
  content: { padding: 16 },
  meCard: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  avatar: { width: 54, height: 54, borderRadius: 27, backgroundColor: '#7C3AED', justifyContent: 'center', alignItems: 'center', marginRight: 13, borderWidth: 2.5, borderColor: '#F5B800' },
  avatarTxt: { color: '#fff', fontSize: 22, fontStyle: 'italic' },
  meInfo: { flex: 1 },
  nick: { fontSize: 16, fontWeight: '500' },
  level: { fontSize: 9, backgroundColor: '#F5B800', color: '#0F1020', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8, fontWeight: '600' },
  xpBar: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 7 },
  xpLabel: { fontSize: 9, color: '#2A2B3D' },
  bar: { height: 5, backgroundColor: '#F2EBD8', borderRadius: 3, marginTop: 4, overflow: 'hidden' },
  barFill: { height: '100%', backgroundColor: '#3D46C9' },
  statGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 14 },
  stat: { width: '48%', padding: 12, backgroundColor: '#fff', borderRadius: 12, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  statVal: { fontSize: 22, fontWeight: '600', fontStyle: 'italic' },
  statLabel: { fontSize: 9, color: '#2A2B3D', marginTop: 2, textTransform: 'uppercase' },
  secTitle: { fontSize: 16, fontWeight: '500', marginBottom: 10 },
  secSmall: { fontSize: 9, color: '#2A2B3D', fontWeight: '400' },
  calCard: { backgroundColor: '#fff', borderRadius: 12, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  calHead: { fontSize: 14, fontWeight: '500', marginBottom: 12 },
  calNum: { color: '#F5B800', fontStyle: 'italic', fontWeight: '600' },
  calRow: { gap: 0 },
  calDay: { width: 38, alignItems: 'center', gap: 5 },
  calDate: { fontSize: 8, color: '#2A2B3D' },
  calCircle: { width: 24, height: 24, borderRadius: 12, backgroundColor: '#F2EBD8', justifyContent: 'center', alignItems: 'center' },
  calHit: { backgroundColor: '#F5B800' },
  calTxt: { fontSize: 10, fontWeight: '700' },
  badgeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  badge: { width: '30%', padding: 14, backgroundColor: '#fff', borderRadius: 12, alignItems: 'center', borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  badgeEarned: { borderColor: '#F5B800' },
  badgeIcon: { width: 46, height: 46, borderRadius: 23, backgroundColor: '#F2EBD8', justifyContent: 'center', alignItems: 'center', marginBottom: 8 },
  badgeLocked: { opacity: 0.5 },
  badgeEmoji: { fontSize: 22 },
  badgeName: { fontSize: 11, fontWeight: '600' },
  badgeStatus: { fontSize: 8, color: '#2A2B3D', marginTop: 2 },
})
