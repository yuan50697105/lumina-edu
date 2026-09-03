// ============================================
// Lumina 墨光 · 移动端入口
// React Navigation + 登录守卫
// ============================================
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { StatusBar } from 'expo-status-bar'
import { useAuthStore } from './src/store/auth'
import type { RootStackParamList } from './src/navigation'
import Login from './src/pages/Login'
import Home from './src/pages/Home'
import CourseDetail from './src/pages/CourseDetail'
import AIChat from './src/pages/AIChat'
import Grades from './src/pages/Grades'
import LiveRoom from './src/pages/LiveRoom'
import Learning from './src/pages/Learning'
import Videos from './src/pages/Videos'
import Achievements from './src/pages/Achievements'
import History from './src/pages/History'
import Profile from './src/pages/Profile'

const Stack = createNativeStackNavigator<RootStackParamList>()

export default function App() {
  const token = useAuthStore((s) => s.token)

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="dark" />
        <Stack.Navigator
          initialRouteName={token ? 'Home' : 'Login'}
          screenOptions={{
            headerStyle: { backgroundColor: '#FAF6EC' },
            headerTintColor: '#0F1020',
            headerTitleStyle: { fontWeight: '700' },
          }}
        >
          <Stack.Screen name="Login" component={Login} options={{ headerShown: false }} />
          <Stack.Screen name="Home" component={Home} options={{ headerShown: false }} />
          <Stack.Screen name="CourseDetail" component={CourseDetail} options={{ title: '课程详情' }} />
          <Stack.Screen name="AIChat" component={AIChat} options={{ title: 'AI 导师' }} />
          <Stack.Screen name="Grades" component={Grades} options={{ title: '我的成绩单' }} />
          <Stack.Screen name="LiveRoom" component={LiveRoom} options={{ title: '直播课堂' }} />
          <Stack.Screen name="Learning" component={Learning} options={{ title: '学习' }} />
          <Stack.Screen name="Videos" component={Videos} options={{ title: '视频' }} />
          <Stack.Screen name="Achievements" component={Achievements} options={{ title: '成就' }} />
          <Stack.Screen name="History" component={History} options={{ title: '历史' }} />
          <Stack.Screen name="Profile" component={Profile} options={{ title: '我的' }} />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  )
}