// Lumina 墨光 · 移动端课程详情（章节 + 选课/退课 + 直播课堂）
import { useEffect, useState } from 'react'
import {
  Alert,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import type { NativeStackScreenProps } from '@react-navigation/native-stack'
import { del, get, post } from '../api/client'
import type { Chapter, Course, LiveRoom } from '../api/types'
import { useAuthStore } from '../store/auth'
import { track, trackClick, trackPageView } from '../utils/tracker'
import type { RootStackParamList } from '../navigation'

const LIVE_STATUS: Record<string, string> = { scheduled: '未开始', live: '直播中', ended: '已结束' }

type Props = NativeStackScreenProps<RootStackParamList, 'CourseDetail'>

export default function CourseDetail({ route, navigation }: Props) {
  const { courseId } = route.params
  const user = useAuthStore((s) => s.user)
  const [course, setCourse] = useState<Course | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [liveRooms, setLiveRooms] = useState<LiveRoom[]>([])
  const [enrolled, setEnrolled] = useState(false)

  const isTeacher = !!user && !!course && (user.role === 'admin' || user.id === course.teacher?.id)

  useEffect(() => {
    trackPageView('course_detail')
    void load()
  }, [courseId])

  async function load() {
    try {
      const [c, ch, rooms] = await Promise.all([
        get<Course>(`/courses/${courseId}`),
        get<Chapter[]>(`/courses/${courseId}/chapters`),
        get<LiveRoom[]>(`/courses/${courseId}/live/rooms`).catch(() => []),
      ])
      setCourse(c)
      setChapters(ch)
      setLiveRooms(rooms ?? [])
    } catch { /* mock 后逻辑简化：进详情页显示不了则报错 */ }
    try {
      const mine = (await get<Array<{ course_id: string }>>('/courses/me/enrolled')) as Array<{ course_id: string }>
      setEnrolled(mine.some((e) => e.course_id === courseId))
    } catch { /* ignore */ }
  }

  async function onEnroll() {
    try {
      await post(`/courses/${courseId}/enroll`)
      track('course.enroll', { course_id: courseId })
      setEnrolled(true)
    } catch (e) {
      Alert.alert('操作失败', e instanceof Error ? e.message : '请重试')
    }
  }

  async function onUnenroll() {
    try {
      await del(`/courses/${courseId}/enroll`)
      track('course.unenroll', { course_id: courseId })
      setEnrolled(false)
    } catch (e) {
      Alert.alert('操作失败', e instanceof Error ? e.message : '请重试')
    }
  }

  async function createLive() {
    // 移动端无 window.prompt：直接用课程标题创建（后端允许空则回退），进入后可在直播页互动
    trackClick('live-create')
    try {
      const r = await post<LiveRoom>(`/live/rooms`, {
        course_id: courseId,
        title: course?.title ? `${course.title} 直播` : undefined,
      })
      track('live.room_create', { course_id: courseId })
      navigation.navigate('LiveRoom', { roomId: r.id })
    } catch (e) {
      Alert.alert('创建失败', e instanceof Error ? e.message : '请重试')
    }
  }

  return (
    <View style={styles.wrap}>
      <FlatList
        data={chapters}
        keyExtractor={(c) => c.id}
        ListHeaderComponent={
          <View>
            <Text style={styles.code}>{course?.code ?? ''}</Text>
            <Text style={styles.title}>{course?.title ?? '课程详情'}</Text>
            <Text style={styles.meta}>
              {course?.teacher?.name ?? ''} · {course?.semester ?? ''} · {course?.students_count ?? 0} 人在学
            </Text>
            <Pressable
              style={[styles.enrollBtn, enrolled && styles.enrollBtnDone]}
              onPress={enrolled ? onUnenroll : onEnroll}
            >
              <Text style={styles.enrollText}>{enrolled ? '已选课 · 点击退课' : '选课'}</Text>
            </Pressable>
            <View style={styles.liveHead}>
              <Text style={styles.section}>直播课堂（{liveRooms.length}）</Text>
              {isTeacher && (
                <Pressable style={styles.createBtn} onPress={() => void createLive()}>
                  <Text style={styles.createText}>＋ 创建直播</Text>
                </Pressable>
              )}
            </View>
            {liveRooms.map((r) => (
              <Pressable
                key={r.id}
                style={styles.liveCard}
                onPress={() => {
                  track('live.room_view', { room_id: r.id })
                  navigation.navigate('LiveRoom', { roomId: r.id })
                }}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.liveTitle} numberOfLines={1}>{r.title}</Text>
                  <Text style={styles.meta}>
                    在线 {r.online_count ?? 0} · 累计 {r.viewer_count ?? 0} 人次
                    {r.status === 'live' && (r.stream_url?.startsWith('http') || r.stream_url?.startsWith('/media')) ? ' · 有推流' : ''}
                  </Text>
                </View>
                <Text style={[styles.statusPill, r.status === 'live' && styles.statusLive]}>
                  {LIVE_STATUS[r.status]}
                </Text>
              </Pressable>
            ))}
            {liveRooms.length === 0 && <Text style={styles.muted}>暂无直播安排。</Text>}
            <Text style={styles.section}>章节 {chapters.length}</Text>
          </View>
        }
        contentContainerStyle={{ padding: 20, gap: 10 }}
        renderItem={({ item }) => (
          <Pressable
            style={styles.chapter}
            onPress={() => {
              track('chapter.view', { course_id: courseId, chapter_id: item.id })
              Alert.alert(item.title, item.content ?? '本章节暂无内容')
            }}
          >
            <Text style={styles.chapterNo}>{item.order_num + 1}</Text>
            <Text style={styles.chapterTitle}>{item.title}</Text>
          </Pressable>
        )}
      />
      <View style={styles.footer}>
        <Pressable
          style={styles.aiBtn}
          onPress={() => {
            track('ai.chat.open', { course_id: courseId })
            navigation.navigate('AIChat', { conversationId: undefined })
          }}
        >
          <Text style={styles.aiText}>AI 苏格拉底导师</Text>
        </Pressable>
        <Pressable style={styles.aiBtn} onPress={() => navigation.navigate('Grades')}>
          <Text style={styles.aiText}>成绩单</Text>
        </Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#FAF6EC' },
  code: { color: '#3D46C9', fontSize: 13, fontWeight: '700' },
  title: { color: '#0F1020', fontSize: 24, fontWeight: '800', marginTop: 4 },
  meta: { color: '#6B6E85', fontSize: 13, marginTop: 6 },
  enrollBtn: {
    backgroundColor: '#3D46C9', alignSelf: 'flex-start', borderRadius: 8,
    paddingHorizontal: 20, paddingVertical: 10, marginTop: 14,
  },
  enrollBtnDone: { backgroundColor: '#2A7F4F' },
  enrollText: { color: '#FAF6EC', fontSize: 15, fontWeight: '600' },
  section: { fontSize: 16, fontWeight: '700', color: '#0F1020', marginTop: 18 },
  chapter: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: '#FFFFFF', borderRadius: 10, padding: 14,
    borderWidth: 1, borderColor: '#EEE9DB',
  },
  chapterNo: {
    width: 26, height: 26, borderRadius: 13, backgroundColor: '#F5B800',
    textAlign: 'center', lineHeight: 26, color: '#0F1020', fontWeight: '800',
  },
  chapterTitle: { color: '#0F1020', fontSize: 15, flex: 1 },
  footer: {
    flexDirection: 'row', gap: 12, padding: 16, paddingBottom: 28,
    borderTopWidth: 1, borderTopColor: '#EEE9DB',
  },
  aiBtn: {
    flex: 1, backgroundColor: '#7C3AED', borderRadius: 10,
    paddingVertical: 14, alignItems: 'center',
  },
  aiText: { color: '#FFFFFF', fontSize: 15, fontWeight: '700' },
  liveHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18 },
  createBtn: { backgroundColor: '#3D46C9', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6 },
  createText: { color: '#FFFFFF', fontSize: 13, fontWeight: '700' },
  liveCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: '#FFFFFF', borderRadius: 10, padding: 14,
    borderWidth: 1, borderColor: '#EEE9DB',
  },
  liveTitle: { color: '#0F1020', fontSize: 15, fontWeight: '700' },
  statusPill: {
    backgroundColor: '#F0EDE0', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4,
    fontSize: 12, color: '#6B6E85', fontWeight: '600', overflow: 'hidden',
  },
  statusLive: { backgroundColor: 'rgba(42,127,79,0.14)', color: '#2A7F4F' },
  muted: { color: '#6B6E85', fontSize: 13 },
})