// Lumina 墨光 · 移动端登录页
import { useState } from 'react'
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import type { NativeStackScreenProps } from '@react-navigation/native-stack'
import { post } from '../api/client'
import type { TokenResponse } from '../api/types'
import { APP_NAME } from '../config'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'
import type { RootStackParamList } from '../navigation'

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>

export default function Login({ navigation }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const setSession = useAuthStore((s) => s.setSession)

  async function onSubmit() {
    if (busy) return
    setBusy(true)
    try {
      const tr = await post<TokenResponse>('/auth/login', {
        username: username.trim(),
        password,
        device: 'mobile',
      })
      setSession(tr)
      track('auth.login', { device: 'mobile' })
      navigation.replace('Home')
    } catch (e) {
      track('auth.login_fail', { reason: String(e) })
      Alert.alert('登录失败', e instanceof Error ? e.message : '请检查账密')
    } finally {
      setBusy(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.wrap}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.card}>
        <Text style={styles.logo}>{APP_NAME}</Text>
        <Text style={styles.sub}>跨端教学协作平台</Text>
        <TextInput
          style={styles.input}
          placeholder="学号 / 工号 / 邮箱"
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          autoCorrect={false}
        />
        <TextInput
          style={styles.input}
          placeholder="密码"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />
        <Pressable style={styles.btn} onPress={onSubmit} disabled={busy}>
          {busy ? <ActivityIndicator color="#FAF6EC" /> : <Text style={styles.btnText}>登 录</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#FAF6EC', justifyContent: 'center', padding: 24 },
  card: { width: '100%', gap: 14 },
  logo: { fontSize: 34, fontWeight: '800', color: '#0F1020', textAlign: 'center' },
  sub: { fontSize: 14, color: '#6B6E85', textAlign: 'center', marginBottom: 20 },
  input: {
    borderWidth: 1, borderColor: '#D8D4C6', borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 16,
    backgroundColor: '#FFFFFF',
  },
  btn: {
    backgroundColor: '#3D46C9', borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginTop: 6,
  },
  btnText: { color: '#FAF6EC', fontSize: 17, fontWeight: '600' },
})