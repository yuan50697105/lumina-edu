// ============================================
// Lumina 墨光 · 我的页
// 个人中心 + 设置
// ============================================
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert } from 'react-native'
import { useAuthStore } from '../store/auth'

export default function Profile() {
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    Alert.alert('退出登录', '确定要退出吗？', [
      { text: '取消', style: 'cancel' },
      { text: '确定', onPress: logout },
    ])
  }

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      {/* 头部 */}
      <View style={s.head}>
        <View style={s.avatar}>
          <Text style={s.avatarTxt}>{user?.name?.charAt(0) || '墨'}</Text>
        </View>
        <View>
          <Text style={s.nick}>{user?.name || '墨小光'}</Text>
          <Text style={s.uid}>学号 {user?.student_id || '20260001'} · {user?.department || '计算机学院'}</Text>
        </View>
      </View>

      {/* 功能列表 */}
      <View style={s.list}>
        <TouchableOpacity style={s.row} onPress={() => Alert.alert('我的课程', '跳转到课程列表')}>
          <View style={[s.icon, { backgroundColor: '#E8EAFB' }]}><Text style={s.iconTxt}>📚</Text></View>
          <Text style={s.lbl}>我的课程</Text>
          <Text style={s.arr}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.row} onPress={() => Alert.alert('我的作业', '跳转到作业列表')}>
          <View style={[s.icon, { backgroundColor: '#D4EDDC' }]}><Text style={s.iconTxt}>📝</Text></View>
          <Text style={s.lbl}>我的作业</Text>
          <Text style={s.arr}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.row} onPress={() => Alert.alert('我的成绩', '跳转到成绩单')}>
          <View style={[s.icon, { backgroundColor: '#FDE68A' }]}><Text style={s.iconTxt}>📊</Text></View>
          <Text style={s.lbl}>我的成绩</Text>
          <Text style={s.arr}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.row} onPress={() => Alert.alert('消息通知', '跳转到消息中心')}>
          <View style={[s.icon, { backgroundColor: '#FDE0D4' }]}><Text style={s.iconTxt}>🔔</Text></View>
          <Text style={s.lbl}>消息通知</Text>
          <Text style={s.arr}>›</Text>
        </TouchableOpacity>
      </View>

      <View style={s.list}>
        <TouchableOpacity style={s.row} onPress={() => Alert.alert('设置', '账号·隐私·偏好')}>
          <View style={[s.icon, { backgroundColor: '#EDE9FE' }]}><Text style={s.iconTxt}>⚙️</Text></View>
          <Text style={s.lbl}>设置</Text>
          <Text style={s.subLbl}>账号 · 隐私 · 偏好</Text>
          <Text style={s.arr}>›</Text>
        </TouchableOpacity>
      </View>

      <View style={s.list}>
        <TouchableOpacity style={s.row} onPress={() => Alert.alert('关于', 'Lumina 墨光 v1.0 · 教育原型')}>
          <View style={[s.icon, { backgroundColor: '#F2EBD8' }]}><Text style={s.iconTxt}>ℹ️</Text></View>
          <Text style={s.lbl}>关于</Text>
          <Text style={s.subLbl}>v1.0</Text>
          <Text style={s.arr}>›</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={s.logoutBtn} onPress={handleLogout}>
        <Text style={s.logoutTxt}>退出登录</Text>
      </TouchableOpacity>

      <Text style={s.footer}>LUMINA · 墨光 · 自主学习 + 视频录播</Text>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAF6EC' },
  content: { paddingBottom: 40 },
  head: { flexDirection: 'row', alignItems: 'center', padding: 18, backgroundColor: '#E8EAFB', gap: 14 },
  avatar: { width: 62, height: 62, borderRadius: 31, backgroundColor: '#7C3AED', justifyContent: 'center', alignItems: 'center' },
  avatarTxt: { color: '#fff', fontSize: 26, fontStyle: 'italic' },
  nick: { fontSize: 19, fontWeight: '600' },
  uid: { fontSize: 10, color: '#2A2B3D', marginTop: 3 },
  list: { marginHorizontal: 18, marginVertical: 8, backgroundColor: '#fff', borderRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: 'rgba(15,16,32,0.12)' },
  row: { flexDirection: 'row', alignItems: 'center', padding: 14, gap: 12, borderBottomWidth: 1, borderBottomColor: 'rgba(15,16,32,0.12)' },
  icon: { width: 30, height: 30, borderRadius: 9, justifyContent: 'center', alignItems: 'center' },
  iconTxt: { fontSize: 15 },
  lbl: { flex: 1, fontSize: 13.5 },
  subLbl: { fontSize: 10.5, color: '#2A2B3D', marginRight: 8 },
  arr: { color: 'rgba(15,16,32,0.22)', fontSize: 13 },
  logoutBtn: { marginHorizontal: 18, marginTop: 20, backgroundColor: '#E85D3A', borderRadius: 8, padding: 13, alignItems: 'center' },
  logoutTxt: { color: '#fff', fontSize: 14, fontWeight: '600' },
  footer: { textAlign: 'center', fontSize: 9, color: '#2A2B3D', marginTop: 20, letterSpacing: 1 },
})
