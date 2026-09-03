// ============================================
// Lumina 墨光 · D-06 自主学习页
// 学习广场 + 路径地图
// ============================================
import { useEffect, useState, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, RefreshControl, ScrollView,
} from 'react-native'
import { get, post } from '../api/client'
import type { LearningPath, LearningPathNode, UserXP } from '../api/types'

const EMOJIS: Record<string, string> = {
  编程: '💻', 设计: '🎨', 语言: '🗣️', 数学: '∑',
}

export default function Learning() {
  const [paths, setPaths] = useState<LearningPath[]>([])
  const [xp, setXp] = useState<UserXP | null>(null)
  const [selectedPath, setSelectedPath] = useState<LearningPath | null>(null)
  const [nodes, setNodes] = useState<LearningPathNode[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const [pathsData, xpData] = await Promise.all([
        get<LearningPath[]>('/learning/paths'),
        get<UserXP>('/learning/xp'),
      ])
      setPaths(pathsData)
      setXp(xpData)
    } catch (e) {
      console.error('loadData', e)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const onRefresh = () => { setRefreshing(true); loadData() }

  const openPath = async (p: LearningPath) => {
    setSelectedPath(p)
    try {
      const nodesData = await get<LearningPathNode[]>(`/learning/paths/${p.id}`)
      setNodes(nodesData)
    } catch (e) {
      console.error('openPath', e)
    }
  }

  const doCheckin = async () => {
    try {
      const result = await post<{ success: boolean; message: string; xp_awarded: number; streak_days: number }>('/learning/checkin')
      if (result.success) {
        setXp(prev => prev ? { ...prev, total_xp: prev.total_xp + result.xp_awarded, streak_days: result.streak_days } : prev)
      }
      alert(result.message)
    } catch (e) {
      alert('打卡失败')
    }
  }

  if (loading) {
    return <View style={s.center}><ActivityIndicator /></View>
  }

  // 路径地图视图
  if (selectedPath) {
    return (
      <View style={s.container}>
        <View style={s.mapHeader}>
          <TouchableOpacity onPress={() => setSelectedPath(null)} style={s.backBtn}>
            <Text style={s.backTxt}>← 返回</Text>
          </TouchableOpacity>
          <Text style={s.mapTitle}>{selectedPath.title}</Text>
          <Text style={s.mapCount}>{nodes.length} 关</Text>
        </View>
        <ScrollView style={s.timeline} contentContainerStyle={{ paddingVertical: 12 }}>
          {nodes.map((n) => (
            <View key={n.id} style={[s.node, n.status === 'locked' && s.nodeLocked]}>
              <View style={[s.dot, n.status === 'done' && s.dotDone, n.status === 'current' && s.dotCurrent]}>
                <Text style={s.dotTxt}>{n.status === 'done' ? '✓' : n.status === 'current' ? '🎯' : '🔒'}</Text>
              </View>
              <View style={s.nodeBox}>
                <Text style={s.nodeTitle}>{n.sequence}. {n.title}</Text>
                <Text style={s.nodeDesc}>{n.description}</Text>
                <View style={s.nodeMeta}>
                  <Text style={s.nodeXP}>XP +{n.xp_reward}</Text>
                  <Text style={[s.nodeStatus, n.status === 'done' && s.stDone, n.status === 'current' && s.stCur]}>
                    {n.status === 'done' ? '已完成' : n.status === 'current' ? '当前关' : '未解锁'}
                  </Text>
                </View>
              </View>
            </View>
          ))}
        </ScrollView>
      </View>
    )
  }

  // 学习广场视图
  return (
    <FlatList
      data={paths}
      keyExtractor={p => p.id}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      contentContainerStyle={s.list}
      ListHeaderComponent={
        <View>
          {/* XP Hero */}
          <View style={s.hero}>
            <View style={s.heroRow}>
              <Text style={s.heroStreak}>🔥 连续打卡 <Text style={s.heroNum}>{xp?.streak_days || 0}</Text> 天</Text>
              <TouchableOpacity style={s.checkinBtn} onPress={doCheckin}>
                <Text style={s.checkinTxt}>打卡</Text>
              </TouchableOpacity>
            </View>
            <Text style={s.xpLine}>累计经验值 <Text style={s.xpNum}>{(xp?.total_xp || 0).toLocaleString()}</Text> XP</Text>
          </View>
          <Text style={s.secTitle}>学习路径</Text>
        </View>
      }
      renderItem={({ item }) => (
        <TouchableOpacity style={s.pathCard} onPress={() => openPath(item)}>
          <View style={[s.pathCover, { backgroundColor: '#3D46C9' }]}>
            <Text style={s.pathEmoji}>{item.cover_emoji || EMOJIS[item.category] || '📚'}</Text>
            <Text style={s.pathLv}>{item.total_nodes} 关 · {item.total_xp} XP</Text>
          </View>
          <View style={s.pathBody}>
            <Text style={s.pathTitle}>{item.title}</Text>
            <View style={s.pathTags}>
              <Text style={s.tag}>{item.category}</Text>
              <Text style={s.tag}>{item.difficulty}</Text>
              <Text style={s.tag}>🧩 {item.total_nodes} 关</Text>
            </View>
            <View style={s.pathFoot}>
              <Text style={s.footXP}>总 XP <Text style={s.xpNum}>{item.total_xp}</Text></Text>
              <Text style={s.footLearners}>{item.learner_count} 人在学</Text>
            </View>
          </View>
        </TouchableOpacity>
      )}
    />
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAF6EC' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#FAF6EC' },
  list: { padding: 16 },
  hero: { backgroundColor: '#0F1020', borderRadius: 16, padding: 18, marginBottom: 16 },
  heroRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  heroStreak: { color: '#fff', fontSize: 15 },
  heroNum: { color: '#F5B800', fontSize: 22, fontWeight: '700' },
  checkinBtn: { backgroundColor: '#F5B800', paddingHorizontal: 14, paddingVertical: 7, borderRadius: 16 },
  checkinTxt: { color: '#0F1020', fontSize: 12, fontWeight: '700' },
  xpLine: { color: 'rgba(255,255,255,0.65)', fontSize: 12, marginTop: 14 },
  xpNum: { color: '#F5B800', fontSize: 26, fontWeight: '700', fontStyle: 'italic' },
  secTitle: { fontSize: 16, fontWeight: '500', marginBottom: 10 },
  pathCard: { backgroundColor: '#fff', borderRadius: 12, overflow: 'hidden', marginBottom: 14, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  pathCover: { aspectRatio: 16 / 9, justifyContent: 'center', alignItems: 'center', position: 'relative' },
  pathEmoji: { fontSize: 52 },
  pathLv: { position: 'absolute', right: 10, bottom: 8, color: '#fff', fontSize: 10 },
  pathBody: { padding: 12 },
  pathTitle: { fontSize: 15, fontWeight: '500', marginBottom: 6 },
  pathTags: { flexDirection: 'row', gap: 6, marginBottom: 10 },
  tag: { fontSize: 9, paddingVertical: 2, paddingHorizontal: 8, borderRadius: 8, backgroundColor: '#E8EAFB', color: '#3D46C9' },
  pathFoot: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderColor: 'rgba(15,16,32,0.12)', borderStyle: 'dashed', paddingTop: 9 },
  footXP: { fontSize: 10, color: '#2A2B3D' },
  footLearners: { fontSize: 10, color: '#2A2B3D' },
  mapHeader: { flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  backBtn: { paddingHorizontal: 10 },
  backTxt: { fontSize: 14, color: '#3D46C9' },
  mapTitle: { flex: 1, fontSize: 16, fontWeight: '500', textAlign: 'center' },
  mapCount: { fontSize: 10, color: '#2A2B3D' },
  timeline: { flex: 1, paddingHorizontal: 18 },
  node: { flexDirection: 'row', marginBottom: 16, gap: 14 },
  nodeLocked: { opacity: 0.6 },
  dot: { width: 30, height: 30, borderRadius: 15, backgroundColor: '#fff', borderWidth: 2, borderColor: 'rgba(15,16,32,0.12)', justifyContent: 'center', alignItems: 'center' },
  dotDone: { backgroundColor: '#2A7F4F', borderColor: '#2A7F4F' },
  dotCurrent: { backgroundColor: '#3D46C9', borderColor: '#3D46C9', width: 36, height: 36, borderRadius: 18 },
  dotTxt: { fontSize: 13, color: '#fff' },
  nodeBox: { flex: 1, backgroundColor: '#fff', borderRadius: 12, padding: 11, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  nodeTitle: { fontSize: 14, fontWeight: '500' },
  nodeDesc: { fontSize: 11, color: '#2A2B3D', marginTop: 2 },
  nodeMeta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 7 },
  nodeXP: { fontSize: 10, color: '#2A2B3D' },
  nodeStatus: { fontSize: 9, paddingVertical: 3, paddingHorizontal: 8, borderRadius: 8, backgroundColor: '#F2EBD8', color: '#2A2B3D' },
  stDone: { backgroundColor: '#D4EDDC', color: '#2A7F4F' },
  stCur: { backgroundColor: '#E8EAFB', color: '#3D46C9' },
})
