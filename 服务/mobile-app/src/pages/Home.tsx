// Lumina 墨光 · 移动端首页（课程列表 + 我的课程）
import { useCallback, useEffect, useState } from 'react'
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import type { NativeStackScreenProps } from '@react-navigation/native-stack'
import { get } from '../api/client'
import type { Course, CourseListResp, User } from '../api/types'
import { useAuthStore } from '../store/auth'
import { track, trackPageView } from '../utils/tracker'
import type { RootStackParamList } from '../navigation'

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>

export default function Home({ navigation }: Props) {
  const [courses, setCourses] = useState<Course[]>([])
  const [refreshing, setRefreshing] = useState(false)
  const [onlyMine, setOnlyMine] = useState(false)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    trackPageView('home')
    void load()
  }, [onlyMine])

  const load = useCallback(async () => {
    setRefreshing(true)
    try {
      if (onlyMine) {
        const mine = await get<Course[]>('/courses/me/enrolled').catch(() => [])
        setCourses(mine)
      } else {
        const resp = await get<CourseListResp>('/courses?limit=24')
        setCourses(resp.data ?? [])
      }
    } catch { /* 布局用下拉可重试 */ } finally {
      setRefreshing(false)
    }
  }, [onlyMine])

  function onLogout() {
    track('user.logout')
    logout()
    navigation.replace('Login')
  }

  return (
    <View style={styles.wrap}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Lumina 墨光</Text>
          <Text style={styles.greet}>{nameOf(user)}，今天也要保持批判思考</Text>
        </View>
        <Pressable onPress={onLogout}><Text style={styles.link}>退出</Text></Pressable>
      </View>

      <View style={styles.tabs}>
        <Pressable style={[styles.tab, !onlyMine && styles.tabActive]} onPress={() => setOnlyMine(false)}>
          <Text style={!onlyMine ? styles.tabTextActive : styles.tabText}>全部课程</Text>
        </Pressable>
        <Pressable style={[styles.tab, onlyMine && styles.tabActive]} onPress={() => setOnlyMine(true)}>
          <Text style={onlyMine ? styles.tabTextActive : styles.tabText}>我的课程</Text>
        </Pressable>
      </View>

      <FlatList
        data={courses}
        keyExtractor={(c) => c.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        ListEmptyComponent={<Text style={styles.empty}>暂无课程，下拉刷新</Text>}
        renderItem={({ item }) => (
          <Pressable
            style={styles.course}
            onPress={() => {
              track('course.view', { course_id: item.id })
              navigation.navigate('CourseDetail', { courseId: item.id })
            }}
          >
            <Text style={styles.courseCode}>{item.code}</Text>
            <Text style={styles.courseTitle}>{item.title}</Text>
            <Text style={styles.courseMeta}>@{item.teacher?.name ?? '未知教师'} · {item.semester}</Text>
          </Pressable>
        )}
      />
    </View>
  )

  function nameOf(u: User | null): string {
    switch (u?.role) {
      case 'teacher': return '老师'
      case 'admin': return '管理员'
      default: return u?.name || '同学'
    }
  }
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#FAF6EC' },
  header: {
    paddingTop: 64, paddingHorizontal: 20, paddingBottom: 12,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end',
  },
  title: { fontSize: 26, fontWeight: '800', color: '#0F1020' },
  greet: { fontSize: 13, color: '#6B6E85', marginTop: 4 },
  link: { color: '#E85D3A', fontSize: 14, fontWeight: '600' },
  tabs: { flexDirection: 'row', gap: 16, paddingHorizontal: 20, marginBottom: 4 },
  tab: { paddingVertical: 8 },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#3D46C9' },
  tabText: { color: '#6B6E85', fontSize: 15 },
  tabTextActive: { color: '#3D46C9', fontSize: 15, fontWeight: '700' },
  course: {
    backgroundColor: '#FFFFFF', borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: '#EEE9DB',
  },
  courseCode: { color: '#3D46C9', fontSize: 12, fontWeight: '700' },
  courseTitle: { color: '#0F1020', fontSize: 17, fontWeight: '600', marginTop: 4 },
  courseMeta: { color: '#6B6E85', fontSize: 12, marginTop: 6 },
  empty: { color: '#6B6E85', textAlign: 'center', marginTop: 60 },
})