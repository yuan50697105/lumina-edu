// ============================================
// Lumina 墨光 · 历史页
// 视频观看历史（简化版）
// ============================================
import { useEffect, useState, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator,
} from 'react-native'
import { get, del } from '../api/client'
import type { VideoWatchHistory } from '../api/types'

export default function History() {
  const [history, setHistory] = useState<VideoWatchHistory[]>([])
  const [loading, setLoading] = useState(true)

  const loadHistory = useCallback(async () => {
    try {
      const data = await get<VideoWatchHistory[]>('/videos/history')
      setHistory(data)
    } catch (e) {
      console.error('loadHistory', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadHistory() }, [loadHistory])

  const deleteItem = async (videoId: string) => {
    try {
      await del(`/videos/history/${videoId}`)
      setHistory(prev => prev.filter(h => h.video_id !== videoId))
    } catch (e) {
      alert('删除失败')
    }
  }

  if (loading) {
    return <View style={s.center}><ActivityIndicator /></View>
  }

  return (
    <FlatList
      data={history}
      keyExtractor={h => h.video_id}
      contentContainerStyle={s.list}
      ListHeaderComponent={
        <Text style={s.hint}>← 左滑删除记录（简化版）</Text>
      }
      renderItem={({ item }) => (
        <View style={s.item}>
          <View style={s.thumb}>
            <Text style={s.emoji}>{'🎬'}</Text>
            <Text style={s.dur}>{item.duration_display}</Text>
          </View>
          <View style={s.info}>
            <Text style={s.title}>{item.title}</Text>
            <Text style={s.meta}>进度 {item.progress_pct}% · {item.duration_display}</Text>
          </View>
          <TouchableOpacity onPress={() => deleteItem(item.video_id)} style={s.delBtn}>
            <Text style={s.delTxt}>删除</Text>
          </TouchableOpacity>
        </View>
      )}
      ListEmptyComponent={
        <View style={s.empty}>
          <Text style={s.emptyIcon}>🕰</Text>
          <Text style={s.emptyTxt}>暂无观看历史</Text>
        </View>
      }
    />
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAF6EC' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#FAF6EC' },
  list: { padding: 16 },
  hint: { fontSize: 11, color: '#2A2B3D', marginBottom: 8 },
  item: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 12, padding: 10, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  thumb: { width: 86, height: 56, borderRadius: 8, backgroundColor: '#3D46C9', justifyContent: 'center', alignItems: 'center', marginRight: 11, position: 'relative' },
  emoji: { fontSize: 20, color: 'rgba(255,255,255,0.9)' },
  dur: { position: 'absolute', right: 3, bottom: 3, fontSize: 8, backgroundColor: 'rgba(0,0,0,0.6)', color: '#fff', paddingHorizontal: 4, paddingVertical: 1, borderRadius: 3 },
  info: { flex: 1 },
  title: { fontSize: 12.5, fontWeight: '600' },
  meta: { fontSize: 9, color: '#2A2B3D', marginTop: 4 },
  delBtn: { backgroundColor: '#E85D3A', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6 },
  delTxt: { color: '#fff', fontSize: 11 },
  empty: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 40, marginBottom: 10 },
  emptyTxt: { fontSize: 12, color: '#2A2B3D' },
})
