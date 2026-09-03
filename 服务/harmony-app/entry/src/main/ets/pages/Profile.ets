// ============================================
// Lumina 墨光 · 鸿蒙客户端 · 个人中心
// pages/Profile · 用户信息 + 功能列表 + 登出
// ============================================
import { router } from '@kit.ArkUI';
import { promptAction } from '@kit.ArkUI';
import { api, getUser, setToken, setUser } from '../model/ApiClient';
import { Colors, FontSize, Spacing, Radius, User } from '../common/constants';

@Entry
@Component
struct Profile {
  @State user: User | null = null;

  aboutToAppear() {
    this.user = getUser();
    this.loadUser();
  }

  build() {
    Column() {
      // 顶部导航
      Row() {
        Text('←')
          .fontSize(FontSize.xl)
          .fontColor(Colors.ink)
          .onClick(() => router.back())
        Text('我的')
          .fontSize(FontSize.lg)
          .fontWeight(FontWeight.Bold)
          .fontColor(Colors.ink)
          .margin({ left: Spacing.md })
      }
      .width('100%')
      .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.md, bottom: Spacing.md })

      Scroll() {
        Column({ space: Spacing.lg }) {
          // 用户信息卡
          Row() {
            // 头像
            Column() {
              Text((this.user?.name ?? '?').charAt(0))
                .fontSize(28)
                .fontWeight(FontWeight.Bold)
                .fontColor(Color.White)
            }
            .width(64)
            .height(64)
            .borderRadius(32)
            .backgroundColor(Colors.cobalt)
            .justifyContent(FlexAlign.Center)

            Column({ space: 4 }) {
              Text(this.user?.name ?? '未登录')
                .fontSize(FontSize.lg)
                .fontWeight(FontWeight.Bold)
                .fontColor(Colors.ink)
              Text(this.user?.email ?? '')
                .fontSize(FontSize.sm)
                .fontColor(Colors.ink2)
              if (this.user?.role) {
                Text(this.user.role === 'teacher' ? '教师' : this.user.role === 'admin' ? '管理员' : '学生')
                  .fontSize(FontSize.xs)
                  .fontColor(Colors.cobalt)
                  .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                  .backgroundColor(Colors.cobaltLight)
                  .borderRadius(Radius.sm)
              }
            }
            .alignItems(HorizontalAlign.Start)
            .margin({ left: Spacing.md })
            .layoutWeight(1)
          }
          .width('100%')
          .padding(Spacing.lg)
          .backgroundColor(Colors.cardBg)
          .borderRadius(Radius.lg)

          // 功能列表
          Column() {
            ForEach([
              { icon: '📚', label: '我的课程', action: 'course' },
              { icon: '📝', label: '我的作业', action: 'assignment' },
              { icon: '📊', label: '我的成绩', action: 'grade' },
              { icon: '🏆', label: '我的成就', action: 'achievement' },
              { icon: '🔔', label: '消息通知', action: 'notification' },
              { icon: '📺', label: '观看历史', action: 'history' },
              { icon: '⚙️', label: '系统设置', action: 'settings' },
              { icon: 'ℹ️', label: '关于墨光', action: 'about' },
            ], (item: Record<string, string>) => {
              Row() {
                Text(item.icon as string).fontSize(22)
                Text(item.label as string)
                  .fontSize(FontSize.md)
                  .fontColor(Colors.ink)
                  .margin({ left: Spacing.md })
                  .layoutWeight(1)
                Text('›')
                  .fontSize(FontSize.lg)
                  .fontColor(Colors.ink3)
              }
              .width('100%')
              .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.md, bottom: Spacing.md })
              .onClick(() => this.handleAction(item.action as string))
              .divider({
                strokeWidth: 0.5,
                color: Colors.divider,
                startMargin: 48,
              })
            })
          }
          .width('100%')
          .backgroundColor(Colors.cardBg)
          .borderRadius(Radius.lg)

          // 登出按钮
          Button('退出登录')
            .type(ButtonType.Capsule)
            .width('100%')
            .height(44)
            .backgroundColor(Color.White)
            .fontColor(Colors.warning)
            .fontSize(FontSize.md)
            .border({ width: 1, color: Colors.warning })
            .margin({ top: Spacing.xl })
            .onClick(() => this.handleLogout())

          // 版本信息
          Text('墨光 v1.0.0 · Lumina Education')
            .fontSize(FontSize.xs)
            .fontColor(Colors.ink3)
            .margin({ top: Spacing.xxl, bottom: Spacing.xxl })
        }
        .padding(Spacing.lg)
        .width('100%')
      }
      .layoutWeight(1)
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Colors.paper)
  }

  async loadUser() {
    try {
      const u = await api.getMe();
      this.user = u;
      setUser(u);
    } catch (e) { /* ignore */ }
  }

  handleAction(action: string) {
    if (action === 'history') {
      router.pushUrl({ url: 'pages/Videos' });
    } else if (action === 'achievement') {
      router.pushUrl({ url: 'pages/Learning' });
    } else {
      promptAction.showToast({ message: `${action} 功能待开发` });
    }
  }

  handleLogout() {
    promptAction.showDialog({
      title: '退出登录',
      message: '确定要退出当前账号吗？',
      buttons: [
        { text: '取消', color: Colors.ink2 },
        { text: '确定', color: Colors.warning },
      ],
    }).then((result) => {
      if (result.index === 1) {
        api.logout();
        promptAction.showToast({ message: '已退出' });
        router.replaceUrl({ url: 'pages/Index' });
      }
    });
  }
}
