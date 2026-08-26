// Lumina 墨光 · 移动端成绩单
import { useEffect, useState } from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { get } from '../api/client'
import type { MyGrades } from '../api/types'
import { track, trackPageView } from '../utils/tracker'

export default function Grades() {
  const [grades, setGrades] = useState<MyGrades | null>(null)

  useEffect(() => {
    trackPageView('grades')
    void get<MyGrades>('/grades/me')
      .then((g) => setGrades(g))
      .catch(() => setGrades(null))
    track('grade.view', { scope: 'me' })
  }, [])

  return (
    <View style={styles.wrap}>
      <View style={styles.summary}>
        <View>
          <Text style={styles.sumLabel}>GPA</Text>
          <Text style={styles.sumValue}>{grades?.gpa ?? '--'}</Text>
        </View>
        <View>
          <Text style={styles.sumLabel}>总学分</Text>
          <Text style={styles.sumValue}>{grades?.total_credits ?? '--'}</Text>
        </View>
        <View>
          <Text style={styles.sumLabel}>已修</Text>
          <Text style={styles.sumValue}>{grades?.course_count ?? 0}</Text>
        </View>
      </View>
      <FlatList
        data={grades?.courses ?? []}
        keyExtractor={(c) => c.course_id}
        contentContainerStyle={{ padding: 20, gap: 10 }}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.meta}>{item.semester} · {item.credit ?? '?'} 学分</Text>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={styles.score}>{item.score ?? '--'}</Text>
              <Text style={styles.grade}>{item.grade ?? ''}</Text>
            </View>
          </View>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#FAF6EC' },
  summary: {
    flexDirection: 'row', justifyContent: 'space-around',
    backgroundColor: '#FFFFFF', paddingVertical: 22, margin: 16, borderRadius: 14,
    borderWidth: 1, borderColor: '#EEE9DB',
  },
  sumLabel: { color: '#6B6E85', fontSize: 12, textAlign: 'center' },
  sumValue: { color: '#0F1020', fontSize: 24, fontWeight: '800', marginTop: 4, textAlign: 'center' },
  row: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#FFFFFF', borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: '#EEE9DB',
  },
  title: { color: '#0F1020', fontSize: 16, fontWeight: '600' },
  meta: { color: '#6B6E85', fontSize: 12, marginTop: 4 },
  score: { color: '#3D46C9', fontSize: 22, fontWeight: '800' },
  grade: { color: '#2A7F4F', fontSize: 13, fontWeight: '700' },
})