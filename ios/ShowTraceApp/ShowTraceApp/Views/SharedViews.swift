import SwiftUI

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
            return "跳过"
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
            return "演出"
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

    /// Poster gradient for a resolved category.
    static func posterColors(for category: String) -> [Color] {
        switch category {
        case "演唱会":
            return [Color.showRadarAccent.opacity(0.22), Color.pink.opacity(0.40)]
        case "音乐会":
            return [Color.purple.opacity(0.22), Color.indigo.opacity(0.45)]
        case "话剧":
            return [Color.orange.opacity(0.22), Color.brown.opacity(0.34)]
        case "展览":
            return [Color.yellow.opacity(0.24), Color.orange.opacity(0.34)]
        case let c where c.contains("体育"):
            return [Color.green.opacity(0.22), Color.teal.opacity(0.40)]
        case "亲子":
            return [Color.mint.opacity(0.26), Color.green.opacity(0.36)]
        case let c where c.contains("曲艺"):
            return [Color.brown.opacity(0.22), Color.orange.opacity(0.34)]
        default:
            return [Color.showRadarAccent.opacity(0.20), Color.showRadarAccent.opacity(0.42)]
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
