// ============================================
// Lumina 墨光 · 鸿蒙客户端 · 直播观看页
// pages/LiveRoom · HLS 拉流 + 举手/聊天/答题
// ============================================
import { router } from '@kit.ArkUI';
import { promptAction } from '@kit.ArkUI';
import { api } from '../model/ApiClient';
import { Colors, FontSize, Spacing, Radius, LiveRoom } from '../common/constants';

@Entry
@Component
struct LiveRoom {
  @State room: LiveRoom | null = null;
  @State messages: Array<Record<string, string>> = [];
  @State chatInput: string = '';
  @State handRaised: boolean = false;
  @State loading: boolean = true;
  private roomId: string = '';

  aboutToAppear() {
    const params = router.getParams() as Record<string, string>;
    this.roomId = params?.roomId ?? '';
    this.loadRoom();
  }

  build() {
    Column() {
      // 顶部导航
      Row() {
        Text('←')
          .fontSize(FontSize.xl)
          .fontColor(Colors.ink)
          .onClick(() => router.back())
        Text(this.room?.title ?? '直播间')
          .fontSize(FontSize.md)
          .fontWeight(FontWeight.Medium)
          .fontColor(Colors.ink)
          .layoutWeight(1)
          .margin({ left: Spacing.md })
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        if (this.room?.status === 'live') {
          Text('● LIVE')
            .fontSize(FontSize.sm)
            .fontColor(Colors.warning)
            .fontWeight(FontWeight.Bold)
        }
      }
      .width('100%')
      .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.md, bottom: Spacing.md })

      // 视频播放区（占位符，实际接入 AVPlayer）
      Column() {
        if (this.loading) {
          LoadingProgress().width(48).height(48)
        } else if (this.room?.status === 'live') {
          Text('📺')
            .fontSize(64)
          Text('直播画面')
            .fontSize(FontSize.md)
            .fontColor(Color.White)
            .margin({ top: Spacing.md })
          Text(this.room.attendee_count ? `${this.room.attendee_count} 人在线` : '')
            .fontSize(FontSize.sm)
            .fontColor(Color.White)
            .opacity(0.8)
        } else {
          Text('🎬')
            .fontSize(64)
          Text('直播未开始')
            .fontSize(FontSize.md)
            .fontColor(Color.White)
            .margin({ top: Spacing.md })
        }
      }
      .width('100%')
      .height(240)
      .backgroundColor(Colors.ink)
      .justifyContent(FlexAlign.Center)
      .alignItems(HorizontalAlign.Center)
      .borderRadius({ bottomLeft: Radius.lg, bottomRight: Radius.lg })

      // 控制条
      Row({ space: Spacing.md }) {
        Button(this.handRaised ? '放下手 ✋' : '举手 ✋')
          .type(ButtonType.Capsule)
          .height(36)
          .layoutWeight(1)
          .backgroundColor(this.handRaised ? Colors.warning : Colors.cobalt)
          .fontColor(Color.White)
          .fontSize(FontSize.sm)
          .onClick(() => this.toggleHand())
        Button('答题')
          .type(ButtonType.Capsule)
          .height(36)
          .layoutWeight(1)
          .backgroundColor(Colors.success)
          .fontColor(Color.White)
          .fontSize(FontSize.sm)
          .onClick(() => promptAction.showToast({ message: '答题功能（待接入）' }))
      }
      .width('100%')
      .padding(Spacing.lg)

      // 聊天区
      Column() {
        Text('聊天')
          .fontSize(FontSize.md)
          .fontWeight(FontWeight.Medium)
          .fontColor(Colors.ink)
          .margin({ bottom: Spacing.md })

        List({ space: Spacing.sm }) {
          ForEach(this.messages, (m: Record<string, string>) => {
            ListItem() {
              Row() {
                Text(m.name ?? '匿名')
                  .fontSize(FontSize.sm)
                  .fontColor(Colors.cobalt)
                  .fontWeight(FontWeight.Medium)
                Text(m.text ?? '')
                  .fontSize(FontSize.sm)
                  .fontColor(Colors.ink)
                  .margin({ left: Spacing.sm })
                  .layoutWeight(1)
              }
              .width('100%')
            }
          }, (_m: Record<string, string>, idx: number) => idx.toString())
        }
        .layoutWeight(1)
        .width('100%')

        // 输入框
        Row({ space: Spacing.sm }) {
          TextInput({ placeholder: '说点什么...', text: this.chatInput })
            .onChange((v: string) => this.chatInput = v)
            .height(36)
            .layoutWeight(1)
            .backgroundColor(Colors.paper)
            .borderRadius(Radius.md)
            .fontSize(FontSize.sm)
            .padding({ left: 12, right: 12 })
          Button('发送')
            .type(ButtonType.Capsule)
            .height(36)
            .backgroundColor(Colors.cobalt)
            .fontColor(Color.White)
            .fontSize(FontSize.sm)
            .onClick(() => this.sendChat())
        }
        .width('100%')
        .margin({ top: Spacing.md })
      }
      .layoutWeight(1)
      .width('100%')
      .padding(Spacing.lg)
      .backgroundColor(Colors.cardBg)
      .borderRadius({ topLeft: Radius.lg, topRight: Radius.lg })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Colors.paper)
  }

  async loadRoom() {
    try {
      // 简化：仅显示占位信息
      this.room = {
        id: this.roomId,
        course_id: '',
        title: '直播间 ' + this.roomId.slice(0, 8),
        status: 'live',
        attendee_count: 42,
      };
      this.messages = [
        { name: '老师', text: '大家好，开始上课' },
        { name: '张三', text: '老师好！' },
        { name: '李四', text: '今天讲什么内容？' },
      ];
    } finally {
      this.loading = false;
    }
  }

  toggleHand() {
    this.handRaised = !this.handRaised;
    promptAction.showToast({ message: this.handRaised ? '已举手' : '已放下' });
  }

  sendChat() {
    if (!this.chatInput.trim()) return;
    this.messages.push({ name: '我', text: this.chatInput });
    this.chatInput = '';
  }
}
