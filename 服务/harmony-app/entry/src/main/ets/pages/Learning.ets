// ============================================
// Lumina 墨光 · 鸿蒙客户端 · 学习广场（D-06）
// pages/Learning · 学习路径 + XP + 打卡 + 徽章
// ============================================
import { router } from '@kit.ArkUI';
import { promptAction } from '@kit.ArkUI';
import { api } from '../model/ApiClient';
import { Colors, FontSize, Spacing, Radius, LearningPath, UserXP, CheckInResult, Badge } from '../common/constants';

@Entry
@Component
struct Learning {
  @State paths: LearningPath[] = [];
  @State xp: UserXP | null = null;
  @State badges: Badge[] = [];
  @State checkedIn: boolean = false;
  @State loading: boolean = true;

  aboutToAppear() {
    this.loadAll();
  }

  build() {
    Column() {
      // 顶部导航
      Row() {
        Text('←')
          .fontSize(FontSize.xl)
          .fontColor(Colors.ink)
          .onClick(() => router.back())
        Text('学习广场')
          .fontSize(FontSize.lg)
          .fontWeight(FontWeight.Bold)
          .fontColor(Colors.ink)
          .margin({ left: Spacing.md })
      }
      .width('100%')
      .padding({ left: Spacing.lg, right: Spacing.lg, top: Spacing.md, bottom: Spacing.md })

      Scroll() {
        Column({ space: Spacing.lg }) {
          // XP + 打卡 卡
          if (this.xp) {
            Column({ space: Spacing.md }) {
              Row() {
                Column({ space: 4 }) {
                  Text(`Lv.${this.xp.level}`)
                    .fontSize(FontSize.xxl)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(Colors.cobalt)
                  Text(`${this.xp.total_xp} XP`)
                    .fontSize(FontSize.sm)
                    .fontColor(Colors.ink2)
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)

                Button(this.checkedIn ? '✓ 已打卡' : '今日打卡 +10XP')
                  .type(ButtonType.Capsule)
                  .height(36)
                  .backgroundColor(this.checkedIn ? Colors.success : Colors.highlighter)
                  .fontColor(this.checkedIn ? Color.White : Colors.ink)
                  .fontSize(FontSize.sm)
                  .onClick(() => this.doCheckIn())
                  .enabled(!this.checkedIn)
              }
              .width('100%')

              Row() {
                Text(`🔥 连续 ${this.xp.streak_days} 天`)
                  .fontSize(FontSize.sm)
                  .fontColor(Colors.ink2)
              }
              .width('100%')
            }
            .width('100%')
            .padding(Spacing.lg)
            .backgroundColor(Colors.cardBg)
            .borderRadius(Radius.lg)
          }

          // 学习路径
          Column({ space: Spacing.md }) {
            Text('学习路径')
              .fontSize(FontSize.md)
              .fontWeight(FontWeight.Medium)
              .fontColor(Colors.ink)

            if (this.loading) {
              LoadingProgress().width(32).height(32).margin({ top: 20 })
            } else if (this.paths.length === 0) {
              Text('暂无学习路径')
                .fontSize(FontSize.sm)
                .fontColor(Colors.ink3)
                .margin({ top: 20 })
            } else {
              ForEach(this.paths, (p: LearningPath) => {
                Column({ space: 6 }) {
                  Row() {
                    Text(p.title)
                      .fontSize(FontSize.md)
                      .fontWeight(FontWeight.Medium)
                      .fontColor(Colors.ink)
                      .layoutWeight(1)
                      .maxLines(1)
                      .textOverflow({ overflow: TextOverflow.Ellipsis })
                    Text(p.category)
                      .fontSize(FontSize.xs)
                      .fontColor(Colors.cobalt)
                      .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                      .backgroundColor(Colors.cobaltLight)
                      .borderRadius(Radius.sm)
                  }
                  .width('100%')
                  if (p.description) {
                    Text(p.description)
                      .fontSize(FontSize.sm)
                      .fontColor(Colors.ink2)
                      .maxLines(2)
                      .textOverflow({ overflow: TextOverflow.Ellipsis })
                  }
                  Text(`${p.node_count ?? 0} 个节点 · 难度 ${p.difficulty}`)
                    .fontSize(FontSize.xs)
                    .fontColor(Colors.ink3)
                }
                .width('100%')
                .padding(Spacing.md)
                .backgroundColor(Colors.paper)
                .borderRadius(Radius.md)
              }, (p: LearningPath) => p.id)
            }
          }
          .width('100%')

          // 徽章墙
          Column({ space: Spacing.md }) {
            Text('我的徽章')
              .fontSize(FontSize.md)
              .fontWeight(FontWeight.Medium)
              .fontColor(Colors.ink)

            if (this.badges.length === 0) {
              Text('还没有徽章，继续加油！')
                .fontSize(FontSize.sm)
                .fontColor(Colors.ink3)
            } else {
              GridRow({ columns: 4, gutter: Spacing.sm }) {
                ForEach(this.badges, (b: Badge) => {
                  GridCol() {
                    Column({ space: 4 }) {
                      Text(b.icon).fontSize(28)
                      Text(b.name)
                        .fontSize(FontSize.xs)
                        .fontColor(Colors.ink)
                        .maxLines(1)
                        .textOverflow({ overflow: TextOverflow.Ellipsis })
                    }
                    .width('100%')
                    .padding(Spacing.sm)
                    .backgroundColor(Colors.paper)
                    .borderRadius(Radius.md)
                    .alignItems(HorizontalAlign.Center)
                  }
                }, (b: Badge) => b.id)
              }
            }
          }
          .width('100%')
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

  async loadAll() {
    this.loading = true;
    try {
      const [paths, xp, badges] = await Promise.all([
        api.listLearningPaths(),
        api.getUserXP(),
        api.listBadges(),
      ]);
      this.paths = paths;
      this.xp = xp;
      this.badges = badges;
    } catch (e) {
      promptAction.showToast({ message: '加载学习数据失败' });
    } finally {
      this.loading = false;
    }
  }

  async doCheckIn() {
    try {
      const res: CheckInResult = await api.checkIn();
      if (res.already_checked_in) {
        promptAction.showToast({ message: '今天已经打过卡啦' });
        this.checkedIn = true;
      } else {
        promptAction.showToast({ message: `打卡成功 +${res.xp_awarded}XP` });
        this.checkedIn = true;
        if (this.xp) {
          this.xp.total_xp += res.xp_awarded;
          this.xp.streak_days = res.new_streak;
        }
      }
    } catch (e) {
      promptAction.showToast({ message: '打卡失败' });
    }
  }
}
