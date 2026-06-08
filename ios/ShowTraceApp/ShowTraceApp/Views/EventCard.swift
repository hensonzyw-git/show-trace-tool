import SwiftUI

struct EventCard: View {
    @EnvironmentObject private var settings: AppSettings
    let event: ShowEvent
    let onFeedbackSent: () -> Void

    @State private var feedbackText = ""
    @State private var isSendingFeedback = false
    @State private var feedbackMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 13) {
                poster

                VStack(alignment: .leading, spacing: 6) {
                    HStack(alignment: .center) {
                        Text(category)
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(Color.showRadarAccent)
                            .lineLimit(1)
                        Spacer(minLength: 8)
                        ScoreBadge(
                            score: event.interestMatchScore,
                            decision: event.interestDecision
                        )
                    }

                    Text(event.title)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)

                    metadataRows
                }
            }

            if let reason = event.interestReason, !reason.isEmpty {
                Label(reason, systemImage: "quote.bubble")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let via = event.discoveredVia, !via.isEmpty {
                Label(via, systemImage: "magnifyingglass")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            HStack {
                FeedbackButton(title: "多推荐类似", icon: "hand.thumbsup") {
                    await sendFeedback("多推荐类似：\(event.title)")
                }
                FeedbackButton(title: "不感兴趣", icon: "hand.thumbsdown") {
                    await sendFeedback("不感兴趣：\(event.title)")
                }
                FeedbackButton(title: "屏蔽这类", icon: "nosign") {
                    await sendFeedback("屏蔽这类：\(event.title)")
                }
            }
            .disabled(isSendingFeedback)

            if let feedbackMessage {
                Text(feedbackMessage)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let purchaseURL = event.purchaseURL, let url = URL(string: purchaseURL) {
                Link(destination: url) {
                    Label("打开详情", systemImage: "safari")
                }
                .font(.footnote)
            }
        }
        .padding(12)
        .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.primary.opacity(0.06), lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.05), radius: 16, x: 0, y: 8)
    }

    private var metadataRows: some View {
        VStack(alignment: .leading, spacing: 5) {
            if let date = event.eventDate, !date.isEmpty {
                Label(date, systemImage: "calendar")
                    .font(.system(size: 14))
                    .lineLimit(1)
            }

            HStack(spacing: 8) {
                if let price = event.priceInfo, !price.isEmpty {
                    Text(price)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                }
                Spacer(minLength: 8)
                sourceTag
            }

            let location = [event.city, event.venue].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " / ")
            if !location.isEmpty {
                Text(location)
                    .font(.system(size: 12.5))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .foregroundStyle(.secondary)
    }

    private var poster: some View {
        RoundedRectangle(cornerRadius: 11)
            .fill(
                LinearGradient(
                    colors: EventCategory.posterColors(for: category),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .frame(width: 66, height: 84)
            .overlay {
                Image(systemName: EventCategory.icon(for: category))
                    .font(.system(size: 22, weight: .regular))
                    .foregroundStyle(.primary.opacity(0.45))
            }
    }

    private var sourceTag: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(EventSource.color(for: event.source))
                .frame(width: 6, height: 6)
            Text(EventSource.label(for: event.source) ?? "未知")
                .font(.system(size: 11.5, weight: .semibold))
                .foregroundStyle(.secondary)
        }
    }

    private var category: String {
        EventCategory.resolved(for: event)
    }

    @MainActor
    private func sendFeedback(_ text: String) async {
        isSendingFeedback = true
        feedbackMessage = nil
        do {
            let request = PreferenceFeedbackRequest(
                feedback: text,
                eventId: event.id,
                rescoreExisting: true,
                rescoreLimit: 500
            )
            let response = try await APIClient(settings: settings).sendFeedback(request)
            let refreshed = response.rescoredEvents ?? 0
            feedbackMessage = refreshed > 0 ? "已按新喜好刷新推荐" : "已记录反馈"
            onFeedbackSent()
        } catch {
            feedbackMessage = error.localizedDescription
        }
        isSendingFeedback = false
    }
}

private struct ScoreBadge: View {
    let score: Int?
    let decision: String?

    var body: some View {
        HStack(spacing: 4) {
            if decision == "keep" {
                Image(systemName: "star.fill")
                    .font(.system(size: 10, weight: .semibold))
            }
            Text(label)
            if let score {
                Text("\(score)")
                    .opacity(0.62)
            }
        }
        .font(.system(size: 11.5, weight: .semibold))
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(color.opacity(0.14), in: Capsule())
        .foregroundStyle(color)
    }

    private var color: Color {
        switch decision {
        case "keep":
            return .showRadarAccent
        case "filter":
            return .secondary
        default:
            return .orange
        }
    }

    private var label: String {
        switch decision {
        case "keep":
            return "关注"
        case "filter":
            return "已过滤"
        default:
            return "待定"
        }
    }
}

private struct FeedbackButton: View {
    let title: String
    let icon: String
    let action: () async -> Void

    var body: some View {
        Button {
            Task { await action() }
        } label: {
            Image(systemName: icon)
        }
        .buttonStyle(.bordered)
        .controlSize(.small)
        .accessibilityLabel(title)
    }
}
