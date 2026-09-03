// ============================================
// Lumina 墨光 · 鸿蒙客户端 · 登录页
// pages/Index · 邮箱/密码登录
// ============================================
import { router } from '@kit.ArkUI';
import { promptAction } from '@kit.ArkUI';
import { api } from '../model/ApiClient';
import { Colors, FontSize, Spacing, Radius } from '../common/constants';

@Entry
@Component
struct Index {
  @State email: string = '';
  @State password: string = '';
  @State loading: boolean = false;

  build() {
    Column() {
      // Logo 区域
      Column() {
        Text('墨光')
          .fontSize(48)
          .fontWeight(FontWeight.Bold)
          .fontColor(Colors.ink)
        Text('LUMINA')
          .fontSize(14)
          .fontColor(Colors.ink3)
          .letterSpacing(4)
          .margin({ top: 4 })
        Text('面向高校师生的跨端教学协作平台')
          .fontSize(FontSize.sm)
          .fontColor(Colors.ink2)
          .margin({ top: Spacing.lg })
      }
      .margin({ top: 80, bottom: 48 })
      .alignItems(HorizontalAlign.Center)

      // 登录表单
      Column({ space: Spacing.lg }) {
        // 邮箱
        Column({ space: 6 }) {
          Text('邮箱')
            .fontSize(FontSize.sm)
            .fontColor(Colors.ink2)
          TextInput({ placeholder: 'your.name@lumina.edu', text: this.email })
            .type(InputType.Email)
            .onChange((v: string) => this.email = v)
            .height(48)
            .backgroundColor(Colors.paper)
            .borderRadius(Radius.md)
            .padding({ left: 16, right: 16 })
        }
        .alignItems(HorizontalAlign.Start)
        .width('100%')

        // 密码
        Column({ space: 6 }) {
          Text('密码')
            .fontSize(FontSize.sm)
            .fontColor(Colors.ink2)
          TextInput({ placeholder: '请输入密码', text: this.password })
            .type(InputType.Password)
            .onChange((v: string) => this.password = v)
            .height(48)
            .backgroundColor(Colors.paper)
            .borderRadius(Radius.md)
            .padding({ left: 16, right: 16 })
        }
        .alignItems(HorizontalAlign.Start)
        .width('100%')

        // 登录按钮
        Button(this.loading ? '登录中...' : '登录')
          .type(ButtonType.Capsule)
          .width('100%')
          .height(48)
          .fontSize(FontSize.md)
          .fontWeight(FontWeight.Medium)
          .backgroundColor(Colors.cobalt)
          .fontColor(Color.White)
          .enabled(!this.loading)
          .onClick(() => this.handleLogin())
          .margin({ top: Spacing.lg })

        // 测试账号提示
        Column({ space: 4 }) {
          Text('测试账号')
            .fontSize(FontSize.xs)
            .fontColor(Colors.ink3)
          Text('教师: teacher@lumina.edu')
            .fontSize(FontSize.xs)
            .fontColor(Colors.ink2)
          Text('学生: student@lumina.edu')
            .fontSize(FontSize.xs)
            .fontColor(Colors.ink2)
          Text('密码: Demo@2026')
            .fontSize(FontSize.xs)
            .fontColor(Colors.ink2)
        }
        .margin({ top: Spacing.xl })
        .padding(Spacing.md)
        .backgroundColor(Colors.cobaltLight)
        .borderRadius(Radius.md)
        .width('100%')
      }
      .width('100%')
      .padding({ left: Spacing.xxl, right: Spacing.xxl })

      Blank()

      // Footer
      Text('© 2026 Lumina 墨光教育')
        .fontSize(FontSize.xs)
        .fontColor(Colors.ink3)
        .margin({ bottom: 24 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Colors.paper)
  }

  async handleLogin() {
    if (!this.email || !this.password) {
      promptAction.showToast({ message: '请填写邮箱和密码' });
      return;
    }
    this.loading = true;
    try {
      await api.login(this.email, this.password);
      promptAction.showToast({ message: '登录成功' });
      router.replaceUrl({ url: 'pages/Home' });
    } catch (e) {
      const msg = e instanceof Error ? e.message : '登录失败';
      promptAction.showToast({ message: msg });
    } finally {
      this.loading = false;
    }
  }
}
