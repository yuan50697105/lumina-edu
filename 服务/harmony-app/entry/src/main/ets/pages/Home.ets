// ============================================
// Lumina 墨光 · 鸿蒙客户端 · 主页（底部 TabBar）
// pages/Home · 5 Tab：首页/课程/直播/学习/我的
// ============================================
import { router } from '@kit.ArkUI';
import { api, getUser } from '../model/ApiClient';
import { Colors, FontSize, Spacing, Radius, Course, LiveRoom, LearningPath, UserXP, CheckInResult } from '../common/constants';
import { promptAction } from '@kit.ArkUI';

// ═══════════════════════════════════════════════
// 首页 Tab · 今日概览
// ═══════════════════════════════════════════════
@Component
struct HomePane {
  @State xp: UserXP | null = null;
  @State greeting: string = '';

  aboutToAppear() {
    this.greeting = this.getGreeting();
    this.loadXP();
  }

  build() {
    Scroll() {
      Column({ space: Spacing.xl }) {
        // 欢迎卡
        Column({ space: 4 }) {
          Text(this.greeting)
            .fontSize(FontSize.xl)
            .fontWeight(FontWeight.Bold)
            .fontColor(Colors.ink)
          Text(getUser()?.name ?? '同学')
            .fontSize(FontSize.md)
            .fontColor(Colors.cobalt)
            .fontWeight(FontWeight.Medium)
        }
        .width('100%')
        .alignItems(HorizontalAlign.Start)
        .padding(Spacing.lg)
        .backgroundColor(Colors.cardBg)
        .borderRadius(Radius.lg)

        // XP 卡
        if (this.xp) {
          Row() {
            Column({ space: 4 }) {
              Text('经验值')
                .fontSize(FontSize.sm)
                .fontColor(Colors.ink2)
              Text(`${this.xp.total_xp}`)
                .fontSize(FontSize.xxl)
                .fontWeight(FontWeight.Bold)
                .fontColor(Colors.cobalt)
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)

            Column({ space: 4 }) {
              Text('等级')
                .fontSize(FontSize.sm)
                .fontColor(Colors.ink2)
              Text(`Lv.${this.xp.level}`)
                .fontSize(FontSize.xl)
                .fontWeight(FontWeight.Bold)
                .fontColor(Colors.highlighter)
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)

            Column({ space: 4 }) {
              Text('连续')
                .fontSize(FontSize.sm)
                .fontColor(Colors.ink2)
              Text(`${this.xp.streak_days} 天`)
                .fontSize(FontSize.xl)
                .fontWeight(FontWeight.Bold)
                .fontColor(Colors.success)
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)
          }
          .width('100%')
          .padding(Spacing.lg)
          .backgroundColor(Colors.cardBg)
          .borderRadius(Radius.lg)
        }

        // 快捷入口
        Column({ space: Spacing.md }) {
          Text('快捷入口')
            .fontSize(FontSize.md)
            .fontWeight(FontWeight.Medium)
            .fontColor(Colors.ink)

          GridRow({ columns: 4, gutter: Spacing.md }) {
            ForEach([
              { icon: '📚', label: '课程', page: '' },
              { icon: '📡', label: '直播', page: '' },
              { icon: '🎯', label: '学习', page: '' },
              { icon: '🏆', label: '成就', page: '' },
            ], (item: Record<string, string>) => {
              GridCol() {
                Column({ space: 6 }) {
                  Text(item.icon as string).fontSize(28)
                  Text(item.label as string)
                    .fontSize(FontSize.xs)
                    .fontColor(Colors.ink)
                }
                .width('100%')
                .padding({ top: Spacing.md, bottom: Spacing.md })
                .backgroundColor(Colors.cardBg)
                .borderRadius(Radius.md)
              }
            })
          }
        }
      }
      .padding(Spacing.lg)
      .width('100%')
    }
    .layoutWeight(1)
    .scrollBar(BarState.Off)
  }

  async loadXP() {
    try {
      this.xp = await api.getUserXP();
    } catch (e) { /* ignore */ }
  }

  getGreeting(): string {
    const h = new Date().getHours();
    if (h < 6) return '夜深了';
    if (h < 12) return '早上好';
    if (h < 14) return '中午好';
    if (h < 18) return '下午好';
    return '晚上好';
  }
}

// ═══════════════════════════════════════════════
// 课程 Tab
// ═══════════════════════════════════════════════
@Component
struct CoursePane {
  @State courses: Course[] = [];
  @State loading: boolean = true;

  aboutToAppear() {
    this.loadCourses();
  }

  build() {
    Column() {
      // 标题
      Row() {
        Text('我的')
          .fontSize(FontSize.xl)
          .fontWeight(FontWeight.Bold)
          .fontColor(Colors.ink)
        Text('课程')
          .fontSize(FontSize.xl)
          .fontWeight(FontWeight.Bold)
          .fontColor(Colors.cobalt)
      }
      .width('100%')
      .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.lg })
      .justifyContent(FlexAlign.Start)

      if (this.loading) {
        LoadingProgress()
          .width(48)
          .height(48)
          .margin({ top: 80 })
      } else if (this.courses.length === 0) {
        Column({ space: 12 }) {
          Text('📚').fontSize(48)
          Text('暂无课程')
            .fontSize(FontSize.md)
            .fontColor(Colors.ink2)
        }
        .margin({ top: 80 })
      } else {
        List({ space: Spacing.md }) {
          ForEach(this.courses, (c: Course) => {
            ListItem() {
              Row() {
                Column({ space: 4 }) {
                  Text(c.title)
                    .fontSize(FontSize.md)
                    .fontWeight(FontWeight.Medium)
                    .fontColor(Colors.ink)
                    .maxLines(2)
                    .textOverflow({ overflow: TextOverflow.Ellipsis })
                  Text(c.code)
                    .fontSize(FontSize.sm)
                    .fontColor(Colors.ink2)
                  if (c.teacher_name) {
                    Text(c.teacher_name)
                      .fontSize(FontSize.xs)
                      .fontColor(Colors.ink3)
                  }
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)

                Text('→')
                  .fontSize(FontSize.lg)
                  .fontColor(Colors.cobalt)
              }
              .width('100%')
              .padding(Spacing.lg)
              .backgroundColor(Colors.cardBg)
              .borderRadius(Radius.md)
            }
          }, (c: Course) => c.id)
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

  async loadCourses() {
    this.loading = true;
    try {
      this.courses = await api.listCourses();
    } catch (e) {
      promptAction.showToast({ message: '加载课程失败' });
    } finally {
      this.loading = false;
    }
  }
}

// ═══════════════════════════════════════════════
// 直播 Tab
// ═══════════════════════════════════════════════
@Component
struct LivePane {
  @State rooms: LiveRoom[] = [];
  @State loading: boolean = true;

  build() {
    Column() {
      Row() {
        Text('课程').fontSize(FontSize.xl).fontWeight(FontWeight.Bold).fontColor(Colors.ink)
        Text('直播').fontSize(FontSize.xl).fontWeight(FontWeight.Bold).fontColor(Colors.cobalt)
      }
      .width('100%')
      .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.lg })
      .justifyContent(FlexAlign.Start)

      if (this.loading) {
        LoadingProgress().width(48).height(48).margin({ top: 80 })
      } else {
        List({ space: Spacing.md }) {
          ForEach(this.rooms, (r: LiveRoom) => {
            ListItem() {
              Row() {
                Column({ space: 4 }) {
                  Text(r.title)
                    .fontSize(FontSize.md)
                    .fontWeight(FontWeight.Medium)
                    .fontColor(Colors.ink)
                  Text(r.status === 'live' ? '● 直播中' : r.status === 'ended' ? '已结束' : '未开始')
                    .fontSize(FontSize.sm)
                    .fontColor(r.status === 'live' ? Colors.warning : Colors.ink2)
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)
                Text('进入').fontSize(FontSize.sm).fontColor(Colors.cobalt)
              }
              .width('100%')
              .padding(Spacing.lg)
              .backgroundColor(Colors.cardBg)
              .borderRadius(Radius.md)
              .onClick(() => router.pushUrl({ url: 'pages/LiveRoom', params: { roomId: r.id } }))
            }
          }, (r: LiveRoom) => r.id)
        }
        .width('100%')
        .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.md })
        .layoutWeight(1)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Colors.paper)
  }
}

// ═══════════════════════════════════════════════
// 主容器 · 底部 TabBar
// ═══════════════════════════════════════════════
@Entry
@Component
struct Home {
  @State currentIndex: number = 0;
  private tabController: TabsController = new TabsController();

  build() {
    Column() {
      Tabs({ barPosition: BarPosition.End, controller: this.tabController, index: this.currentIndex }) {
        TabContent() { HomePane() }.tabBar(this.tabItem('首页', '🏠', 0))
        TabContent() { CoursePane() }.tabBar(this.tabItem('课程', '📚', 1))
        TabContent() { LivePane() }.tabBar(this.tabItem('直播', '📡', 2))
        TabContent() {
          Column() {
            Button('进入学习广场')
              .type(ButtonType.Capsule)
              .height(44)
              .backgroundColor(Colors.cobalt)
              .fontColor(Color.White)
              .onClick(() => router.pushUrl({ url: 'pages/Learning' }))
            Button('进入视频库')
              .type(ButtonType.Capsule)
              .height(44)
              .backgroundColor(Colors.ink)
              .fontColor(Color.White)
              .margin({ top: Spacing.md })
              .onClick(() => router.pushUrl({ url: 'pages/Videos' }))
          }
          .width('100%')
          .height('100%')
          .justifyContent(FlexAlign.Center)
        }.tabBar(this.tabItem('学习', '🎯', 3))
        TabContent() {
          Column() {
            Button('进入个人中心')
              .type(ButtonType.Capsule)
              .height(44)
              .backgroundColor(Colors.cobalt)
              .fontColor(Color.White)
              .onClick(() => router.pushUrl({ url: 'pages/Profile' }))
          }
          .width('100%')
          .height('100%')
          .justifyContent(FlexAlign.Center)
        }.tabBar(this.tabItem('我的', '👤', 4))
      }
      .barMode(BarMode.Fixed)
      .scrollable(false)
      .onChange((idx: number) => this.currentIndex = idx)
      .layoutWeight(1)
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Colors.paper)
  }

  @Builder
  tabItem(label: string, icon: string, idx: number) {
    Column({ space: 2 }) {
      Text(icon).fontSize(22)
      Text(label)
        .fontSize(FontSize.xs)
        .fontColor(this.currentIndex === idx ? Colors.cobalt : Colors.ink3)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}
