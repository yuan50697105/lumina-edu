// ============================================
// Lumina 墨光 · 鸿蒙客户端 · 视频库（D-08）
// pages/Videos · 视频列表 + 观看历史
// ============================================
import { router } from '@kit.ArkUI';
import { promptAction } from '@kit.ArkUI';
import { api } from '../model/ApiClient';
import { Colors, FontSize, Spacing, Radius, Video } from '../common/constants';

@Entry
@Component
struct Videos {
  @State videos: Video[] = [];
  @State loading: boolean = true;
  @State searchKeyword: string = '';

  aboutToAppear() {
    this.loadVideos();
  }

  get filteredVideos(): Video[] {
    if (!this.searchKeyword) return this.videos;
    const kw = this.searchKeyword.toLowerCase();
    return this.videos.filter(v => v.title.toLowerCase().includes(kw));
  }

  build() {
    Column() {
      // 顶部导航
      Row() {
        Text('←')
          .fontSize(FontSize.xl)
          .fontColor(Colors.ink)
          .onClick(() => router.back())
        Text('视频库')
          .fontSize(FontSize.lg)
          .fontWeight(FontWeight.Bold)
          .fontColor(Colors.ink)
          .margin({ left: Spacing.md })
      }
      .width('100%')
      .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.md, bottom: Spacing.md })

      // 搜索框
      TextInput({ placeholder: '搜索视频...', text: this.searchKeyword })
        .onChange((v: string) => this.searchKeyword = v)
        .height(40)
        .backgroundColor(Colors.cardBg)
        .borderRadius(Radius.md)
        .margin({ left: Spacing.lg, right: Spacing.lg })
        .fontSize(FontSize.sm)
        .padding({ left: 16, right: 16 })

      if (this.loading) {
        LoadingProgress()
          .width(48)
          .height(48)
          .margin({ top: 80 })
      } else if (this.filteredVideos.length === 0) {
        Column({ space: 12 }) {
          Text('🎬').fontSize(48)
          Text(this.searchKeyword ? '没有匹配的视频' : '暂无视频')
            .fontSize(FontSize.md)
            .fontColor(Colors.ink2)
        }
        .margin({ top: 80 })
      } else {
        List({ space: Spacing.md }) {
          ForEach(this.filteredVideos, (v: Video) => {
            ListItem() {
              Row() {
                // 封面占位
                Column() {
                  Text('▶').fontSize(24).fontColor(Color.White)
                }
                .width(100)
                .height(64)
                .backgroundColor(Colors.ink)
                .borderRadius(Radius.sm)
                .justifyContent(FlexAlign.Center)

                Column({ space: 4 }) {
                  Text(v.title)
                    .fontSize(FontSize.md)
                    .fontWeight(FontWeight.Medium)
                    .fontColor(Colors.ink)
                    .maxLines(2)
                    .textOverflow({ overflow: TextOverflow.Ellipsis })
                  Row({ space: Spacing.md }) {
                    Text(this.formatDuration(v.duration_sec))
                      .fontSize(FontSize.xs)
                      .fontColor(Colors.ink2)
                    Text(`👁 ${v.view_count}`)
                      .fontSize(FontSize.xs)
                      .fontColor(Colors.ink3)
                  }
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)
                .margin({ left: Spacing.md })
              }
              .width('100%')
              .padding(Spacing.md)
              .backgroundColor(Colors.cardBg)
              .borderRadius(Radius.md)
              .onClick(() => {
                promptAction.showToast({ message: `播放: ${v.title}` });
              })
            }
          }, (v: Video) => v.id)
        }
        .width('100%')
        .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.md, bottom: Spacing.lg })
        .layoutWeight(1)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Colors.paper)
  }

  async loadVideos() {
    this.loading = true;
    try {
      this.videos = await api.listVideos();
    } catch (e) {
      promptAction.showToast({ message: '加载视频失败' });
    } finally {
      this.loading = false;
    }
  }

  formatDuration(sec: number): string {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
}
