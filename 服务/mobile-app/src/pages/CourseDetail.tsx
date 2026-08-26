// Lumina 墨光 · 移动端课程详情（章节 + 选课/退课）
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
import type { Chapter, Course } from '../api/types'
import { track, trackPageView } from '../utils/tracker'
import type { RootStackParamList } from '../navigation'

type Props = NativeStackScreenProps<RootStackParamList, 'CourseDetail'>

export default function CourseDetail({ route, navigation }: Props) {
  const { courseId } = route.params
  const [course, setCourse] = useState<Course | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [enrolled, setEnrolled] = useState(false)

  useEffect(() => {
    trackPageView('course_detail')
    void load()
  }, [courseId])

  async function load() {
    try {
      const [c, ch] = await Promise.all([
        get<Course>(`/courses/${courseId}`),
        get<Chapter[]>(`/courses/${courseId}/chapters`),
      ])
      setCourse(c)
      setChapters(ch)
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
})