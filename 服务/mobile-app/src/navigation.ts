// Lumina 墨光 · 移动端导航栈定义
export type RootStackParamList = {
  Login: undefined
  Home: undefined
  CourseDetail: { courseId: string }
  AIChat: { conversationId?: string }
  Grades: undefined
  LiveRoom: { roomId: string }
}