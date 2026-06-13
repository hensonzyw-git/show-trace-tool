import SwiftUI
#if canImport(UIKit)
import UIKit
#endif
#if canImport(SafariServices)
import SafariServices
#endif

// MARK: - Design tokens
// Single source of truth for ShowRadar colors. Do not redefine these locally.

extension Color {
    static let showRadarAccent = Color(red: 224 / 255, green: 83 / 255, blue: 61 / 255)
    static let showRadarScreenBackground = Color(
        light: Color(red: 244 / 255, green: 241 / 255, blue: 238 / 255),
        dark: Color(red: 12 / 255, green: 11 / 255, blue: 10 / 255)
    )
    static let showRadarCardBackground = Color(
        light: .white,
        dark: Color(red: 26 / 255, green: 24 / 255, blue: 22 / 255)
    )
    static let showRadarInsetBackground = Color(
        light: Color(red: 244 / 255, green: 241 / 255, blue: 236 / 255),
        dark: Color(red: 35 / 255, green: 31 / 255, blue: 28 / 255)
    )
    static let showRadarSeparator = Color(
        light: Color(red: 28 / 255, green: 23 / 255, blue: 21 / 255).opacity(0.07),
        dark: .white.opacity(0.08)
    )

    init(light: Color, dark: Color) {
        self.init(UIColor { traits in
            traits.userInterfaceStyle == .dark ? UIColor(dark) : UIColor(light)
        })
    }
}

// MARK: - Source taxonomy
// Single source of truth for mapping a backend `source` slug to its display
// label and accent color. Used by every card so the mapping never drifts.

enum EventSource {
    static func label(for source: String?) -> String? {
        switch source?.lowercased() {
        case "damai":
            return "大麦"
        case "showstart":
            return "秀动"
        case "motianlun":
            return "摩天轮"
        case let value? where !value.isEmpty:
            return value
        default:
            return nil
        }
    }

    static func color(for source: String?) -> Color {
        switch label(for: source) {
        case "大麦":
            return .showRadarAccent
        case "秀动":
            return .blue
        case "摩天轮":
            return .teal
        default:
            return .secondary
        }
    }
}

// MARK: - Run status taxonomy
// Single source of truth for a pipeline run's status string (mirrors
// PipelineStats.status / the API). Used by Settings and Runs views.

enum RunStatus {
    static func label(_ status: String?) -> String {
        switch status {
        case "success":
            return "成功"
        case "partial_success":
            return "部分成功"
        case "failed":
            return "失败"
        case "running":
            return "运行中"
        case "skipped":
            return "已跳过"
        default:
            return "未知"
        }
    }

    static func color(_ status: String?) -> Color {
        switch status {
        case "success":
            return .green
        case "partial_success", "running", "skipped":
            return .orange
        case "failed":
            return .red
        default:
            return .secondary
        }
    }
}

// MARK: - Category taxonomy
// Mirrors the backend `interest_category` values produced in app/preferences.py
// (体育比赛 / 演唱会 / 音乐会 / 话剧 / 展览 / 亲子 / 曲艺杂谈 / 其他). Both the card
// display and the list filter resolve categories through this enum so the label a
// user sees and the label the filter matches against can never diverge.

enum EventCategory {
    /// Resolve an event's display category. Prefers the backend `interest_category`,
    /// falling back to the raw event `type` when scoring hasn't produced one.
    static func resolved(for event: ShowEvent) -> String {
        if let category = event.interestCategory, !category.isEmpty {
            return category
        }
        switch event.type {
        case "concert":
            return "演唱会"
        case "exhibition":
            return "展览"
        case "activity":
            return "活动"
        default:
            return "其他"
        }
    }

    /// Filter chips shown above the list. "全部" means no filtering.
    static let filters: [String] = ["全部", "演唱会", "音乐会", "话剧", "展览", "体育", "亲子", "曲艺"]

    /// Whether an event matches the selected filter chip. Uses `contains` for the
    /// chips whose label is a shortened form of the backend value (体育→体育比赛,
    /// 曲艺→曲艺杂谈).
    static func matches(_ filter: String, event: ShowEvent) -> Bool {
        guard filter != "全部" else { return true }
        let category = resolved(for: event)
        switch filter {
        case "体育":
            return category.contains("体育")
        case "曲艺":
            return category.contains("曲艺")
        default:
            return category.localizedCaseInsensitiveContains(filter)
        }
    }

    /// Category icon-chip gradient. Posters are intentionally out of scope for v2.
    static func chipColors(for category: String) -> [Color] {
        switch category {
        case "演唱会":
            return [Color.showRadarAccent.opacity(0.74), Color.red.opacity(0.70)]
        case "音乐会":
            return [Color.purple.opacity(0.72), Color.indigo.opacity(0.78)]
        case "话剧":
            return [Color.orange.opacity(0.78), Color.brown.opacity(0.58)]
        case "展览":
            return [Color.green.opacity(0.68), Color.yellow.opacity(0.66)]
        case let c where c.contains("体育"):
            return [Color.teal.opacity(0.72), Color.green.opacity(0.78)]
        case "亲子":
            return [Color.cyan.opacity(0.70), Color.mint.opacity(0.72)]
        case let c where c.contains("曲艺"):
            return [Color.pink.opacity(0.72), Color.purple.opacity(0.64)]
        default:
            return [Color.showRadarAccent.opacity(0.70), Color.orange.opacity(0.62)]
        }
    }

    /// SF Symbol used on the poster placeholder while real artwork is unavailable.
    static func icon(for category: String) -> String {
        switch category {
        case "演唱会":
            return "music.mic"
        case "音乐会":
            return "music.note"
        case "话剧":
            return "theatermasks.fill"
        case "展览":
            return "photo.fill"
        case let c where c.contains("体育"):
            return "sportscourt.fill"
        case "亲子":
            return "person.2.fill"
        case let c where c.contains("曲艺"):
            return "mic.fill"
        default:
            return "ticket.fill"
        }
    }
}

enum DecisionStyle {
    static func label(_ decision: String?) -> String {
        switch decision {
        case "keep":
            return "关注"
        case "maybe":
            return "待观察"
        case "filter":
            return "已过滤"
        default:
            return "待观察"
        }
    }

    static func foreground(_ decision: String?) -> Color {
        switch decision {
        case "keep":
            return Color(light: Color(red: 192 / 255, green: 67 / 255, blue: 47 / 255), dark: Color(red: 1, green: 138 / 255, blue: 114 / 255))
        case "filter":
            return .secondary
        default:
            return Color(light: Color(red: 154 / 255, green: 107 / 255, blue: 23 / 255), dark: Color(red: 232 / 255, green: 192 / 255, blue: 107 / 255))
        }
    }

    static func background(_ decision: String?) -> Color {
        switch decision {
        case "keep":
            return Color.showRadarAccent.opacity(0.12)
        case "filter":
            return Color.secondary.opacity(0.08)
        default:
            return Color.orange.opacity(0.13)
        }
    }
}

struct ShowRadarCard<Content: View>: View {
    let content: () -> Content

    init(@ViewBuilder content: @escaping () -> Content) {
        self.content = content
    }

    var body: some View {
        VStack(spacing: 0) {
            content()
        }
        .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.showRadarSeparator, lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.05), radius: 16, x: 0, y: 8)
    }
}

struct ShowRadarSectionLabel: View {
    let title: String
    var trailing: String?

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title)
                .font(.system(size: 18, weight: .bold))
                .tracking(-0.3)
            Spacer()
            if let trailing {
                Text(trailing)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 20)
        .padding(.bottom, 9)
    }
}

struct CategoryIconChip: View {
    let category: String

    var body: some View {
        RoundedRectangle(cornerRadius: 10)
            .fill(
                LinearGradient(
                    colors: EventCategory.chipColors(for: category),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .frame(width: 34, height: 34)
            .overlay {
                Image(systemName: EventCategory.icon(for: category))
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.96))
            }
    }
}

#if os(iOS)
struct SafariSheet: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        SFSafariViewController(url: url)
    }

    func updateUIViewController(_ uiViewController: SFSafariViewController, context: Context) {}
}
#endif

struct ErrorStateView: View {
    let message: String
    let retry: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 30))
                .foregroundStyle(.orange)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button {
                retry()
            } label: {
                Label("重试", systemImage: "arrow.clockwise")
            }
            .buttonStyle(.bordered)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct EmptyStateView: View {
    let title: String
    let systemImage: String

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.system(size: 30))
                .foregroundStyle(.secondary)
            Text(title)
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
