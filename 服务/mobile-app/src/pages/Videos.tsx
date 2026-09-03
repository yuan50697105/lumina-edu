// ============================================
// Lumina 墨光 · D-08 视频录播页
// 视频列表 + 播放器（简化版）
// ============================================
import { useEffect, useState, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, RefreshControl, TextInput,
} from 'react-native'
import { get, post, del } from '../api/client'
import type { Video, VideoDetail, VideoNoteCreate, VideoWatchHistory } from '../api/types'

export default function Videos() {
  const [videos, setVideos] = useState<Video[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState<VideoDetail | null>(null)
  const [noteText, setNoteText] = useState('')
  const [history, setHistory] = useState<VideoWatchHistory[]>([])
  const [showHistory, setShowHistory] = useState(false)

  const loadVideos = useCallback(async () => {
    try {
      const data = await get<Video[]>('/videos')
      setVideos(data)
    } catch (e) {
      console.error('loadVideos', e)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  const loadHistory = useCallback(async () => {
    try {
      const data = await get<VideoWatchHistory[]>('/videos/history')
      setHistory(data)
    } catch (e) {
      console.error('loadHistory', e)
    }
  }, [])

  useEffect(() => { loadVideos(); loadHistory() }, [loadVideos, loadHistory])

  const onRefresh = () => { setRefreshing(true); loadVideos() }

  const openVideo = async (v: Video) => {
    try {
      const detail = await get<VideoDetail>(`/videos/${v.id}`)
      setSelectedVideo(detail)
    } catch (e) {
      console.error('openVideo', e)
    }
  }

  const addNote = async () => {
    if (!selectedVideo || !noteText.trim()) return
    try {
      const payload: VideoNoteCreate = {
        video_id: selectedVideo.id,
        timestamp_sec: 0, // 简化：固定 0
        content: noteText.trim(),
      }
      await post('/videos/notes', payload)
      setNoteText('')
      // 重新加载视频详情
      const detail = await get<VideoDetail>(`/videos/${selectedVideo.id}`)
      setSelectedVideo(detail)
      alert('✅ 笔记已保存')
    } catch (e) {
      alert('保存失败')
    }
  }

  const deleteHistoryItem = async (videoId: string) => {
    try {
      await del(`/videos/history/${videoId}`)
      setHistory(prev => prev.filter(h => h.video_id !== videoId))
    } catch (e) {
      alert('删除失败')
    }
  }

  const filteredVideos = videos.filter(v =>
    !search || v.title.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return <View style={s.center}><ActivityIndicator /></View>
  }

  // 视频详情视图
  if (selectedVideo) {
    return (
      <View style={s.container}>
        <View style={s.playerPlaceholder}>
          <Text style={s.playerEmoji}>{selectedVideo.cover_emoji || '🎬'}</Text>
          <Text style={s.playerNote}>◉ 录播回放 · {selectedVideo.duration_display}</Text>
        </View>
        <View style={s.videoInfo}>
          <Text style={s.videoTitle}>{selectedVideo.title}</Text>
          <Text style={s.videoDesc}>{selectedVideo.description}</Text>
        </View>
        <View style={s.tabs}>
          <TouchableOpacity style={s.tab}>
            <Text style={s.tabTxt}>简介</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.tab}>
            <Text style={s.tabTxt}>笔记 ({selectedVideo.notes.length})</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.tab}>
            <Text style={s.tabTxt}>章节 ({selectedVideo.chapters.length})</Text>
          </TouchableOpacity>
        </View>
        <FlatList
          data={selectedVideo.notes}
          keyExtractor={n => n.id}
          contentContainerStyle={s.noteList}
          ListHeaderComponent={
            <View style={s.noteInput}>
              <TextInput
                style={s.input}
                placeholder="✏️ 插入笔记..."
                value={noteText}
                onChangeText={setNoteText}
                multiline
              />
              <TouchableOpacity style={s.saveBtn} onPress={addNote}>
                <Text style={s.saveTxt}>保存</Text>
              </TouchableOpacity>
            </View>
          }
          renderItem={({ item }) => (
            <View style={s.noteItem}>
              <Text style={s.noteTs}>{item.timestamp_display}</Text>
              <Text style={s.noteContent}>{item.content}</Text>
            </View>
          )}
          ListEmptyComponent={<Text style={s.empty}>暂无笔记</Text>}
        />
        <TouchableOpacity style={s.backToList} onPress={() => setSelectedVideo(null)}>
          <Text style={s.backTxt}>← 返回列表</Text>
        </TouchableOpacity>
      </View>
    )
  }

  // 观看历史视图
  if (showHistory) {
    return (
      <View style={s.container}>
        <View style={s.histHeader}>
          <TouchableOpacity onPress={() => setShowHistory(false)}>
            <Text style={s.backTxt}>← 返回</Text>
          </TouchableOpacity>
          <Text style={s.histTitle}>观看历史</Text>
        </View>
        <FlatList
          data={history}
          keyExtractor={h => h.video_id}
          contentContainerStyle={s.histList}
          renderItem={({ item }) => (
            <View style={s.histItem}>
              <View style={s.histInfo}>
                <Text style={s.histTitle2}>{item.title}</Text>
                <Text style={s.histMeta}>进度 {item.progress_pct}% · {item.duration_display}</Text>
              </View>
              <TouchableOpacity onPress={() => deleteHistoryItem(item.video_id)} style={s.delBtn}>
                <Text style={s.delTxt}>删除</Text>
              </TouchableOpacity>
            </View>
          )}
          ListEmptyComponent={<Text style={s.empty}>暂无观看记录</Text>}
        />
      </View>
    )
  }

  // 视频列表视图
  return (
    <FlatList
      data={filteredVideos}
      keyExtractor={v => v.id}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      contentContainerStyle={s.list}
      ListHeaderComponent={
        <View>
          <View style={s.searchBox}>
            <Text style={s.searchIcon}>🔍</Text>
            <TextInput
              style={s.searchInput}
              placeholder="搜索课程视频 / 知识点"
              value={search}
              onChangeText={setSearch}
            />
          </View>
          <TouchableOpacity style={s.histLink} onPress={() => setShowHistory(true)}>
            <Text style={s.histLinkTxt}>📚 观看历史 →</Text>
          </TouchableOpacity>
        </View>
      }
      renderItem={({ item }) => (
        <TouchableOpacity style={s.videoCard} onPress={() => openVideo(item)}>
          <View style={[s.thumb, { backgroundColor: '#3D46C9' }]}>
            <Text style={s.thumbEmoji}>{item.cover_emoji || '🎬'}</Text>
            <Text style={s.dur}>{item.duration_display}</Text>
            {item.progress_pct > 0 && (
              <View style={s.resumeBar}>
                <View style={[s.resumeFill, { width: `${item.progress_pct}%` as any }]} />
              </View>
            )}
          </View>
          <View style={s.videoBody}>
            <Text style={s.videoTitle2}>{item.title}</Text>
            <Text style={s.videoMeta}>▶ {item.view_count} 次播放{item.progress_pct > 0 ? ` · 看到 ${item.progress_pct}%` : ''}</Text>
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
  searchBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 12, padding: 9, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  searchIcon: { fontSize: 14, marginRight: 8 },
  searchInput: { flex: 1, fontSize: 13 },
  histLink: { paddingVertical: 8, alignItems: 'flex-end', marginBottom: 10 },
  histLinkTxt: { fontSize: 12, color: '#3D46C9' },
  videoCard: { backgroundColor: '#fff', borderRadius: 12, overflow: 'hidden', marginBottom: 14, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  thumb: { aspectRatio: 16 / 9, justifyContent: 'center', alignItems: 'center', position: 'relative' },
  thumbEmoji: { fontSize: 42, color: 'rgba(255,255,255,0.9)' },
  dur: { position: 'absolute', right: 8, bottom: 8, fontSize: 9, backgroundColor: 'rgba(15,16,32,0.72)', color: '#fff', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  resumeBar: { position: 'absolute', left: 0, right: 0, bottom: 0, height: 3, backgroundColor: 'rgba(255,255,255,0.3)' },
  resumeFill: { height: '100%', backgroundColor: '#F5B800' },
  videoBody: { padding: 10 },
  videoTitle2: { fontSize: 14, fontWeight: '500', lineHeight: 1.35 },
  videoMeta: { fontSize: 10, color: '#2A2B3D', marginTop: 6 },
  playerPlaceholder: { aspectRatio: 16 / 9, backgroundColor: '#000', justifyContent: 'center', alignItems: 'center', position: 'relative' },
  playerEmoji: { fontSize: 58, color: 'rgba(255,255,255,0.9)' },
  playerNote: { position: 'absolute', top: 10, left: 12, fontSize: 9, color: 'rgba(255,255,255,0.65)', backgroundColor: 'rgba(0,0,0,0.4)', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  videoInfo: { padding: 14 },
  videoTitle: { fontSize: 17, fontWeight: '500', lineHeight: 1.35 },
  videoDesc: { fontSize: 12, color: '#2A2B3D', marginTop: 7, lineHeight: 1.7 },
  tabs: { flexDirection: 'row', borderBottomWidth: 1, borderColor: 'rgba(15,16,32,0.12)', paddingHorizontal: 18 },
  tab: { paddingVertical: 12, marginRight: 22 },
  tabTxt: { fontSize: 13, color: '#3D46C9', fontWeight: '600' },
  noteList: { padding: 14 },
  noteInput: { marginBottom: 12 },
  input: { backgroundColor: '#fff', borderRadius: 10, padding: 10, fontSize: 13, minHeight: 88, textAlignVertical: 'top', borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  saveBtn: { backgroundColor: '#3D46C9', borderRadius: 8, padding: 13, marginTop: 12, alignItems: 'center' },
  saveTxt: { color: '#fff', fontSize: 14, fontWeight: '600' },
  noteItem: { flexDirection: 'row', gap: 10, backgroundColor: '#fff', borderRadius: 10, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  noteTs: { fontSize: 10, color: '#3D46C9', backgroundColor: '#E8EAFB', borderRadius: 6, paddingHorizontal: 7, paddingVertical: 3 },
  noteContent: { flex: 1, fontSize: 12, lineHeight: 1.55 },
  empty: { textAlign: 'center', color: '#2A2B3D', fontSize: 12, paddingVertical: 20 },
  backToList: { padding: 14, alignItems: 'center', borderTopWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  backTxt: { fontSize: 14, color: '#3D46C9' },
  histHeader: { flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  histTitle: { flex: 1, fontSize: 17, fontWeight: '500', textAlign: 'center' },
  histList: { padding: 16 },
  histItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 12, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  histInfo: { flex: 1 },
  histTitle2: { fontSize: 13, fontWeight: '600' },
  histMeta: { fontSize: 9, color: '#2A2B3D', marginTop: 4 },
  delBtn: { backgroundColor: '#E85D3A', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6 },
  delTxt: { color: '#fff', fontSize: 11 },
})
