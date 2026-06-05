import SwiftUI

struct EventCard: View {
    @EnvironmentObject private var settings: AppSettings
    let event: ShowEvent
    let onFeedbackSent: () -> Void

    @State private var feedbackText = ""
    @State private var isSendingFeedback = false
    @State private var feedbackMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                HStack(alignment: .top) {
                    Text(event.title)
                        .font(.headline)
                        .lineLimit(3)
                    Spacer()
                    if let score = event.interestMatchScore {
                        ScoreBadge(score: score)
                    }
                }

                metadataRows
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
        .padding(14)
        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
    }

    private var metadataRows: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let artist = event.artist, !artist.isEmpty {
                Label(artist, systemImage: "music.mic")
                    .font(.subheadline)
            }
            if let date = event.eventDate, !date.isEmpty {
                Label(date, systemImage: "calendar")
                    .font(.subheadline)
            }
            let location = [event.city, event.venue].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " / ")
            if !location.isEmpty {
                Label(location, systemImage: "mappin.and.ellipse")
                    .font(.subheadline)
            }
            if let price = event.priceInfo, !price.isEmpty {
                Label(price, systemImage: "ticket")
                    .font(.subheadline)
            }
            if let category = event.interestCategory, !category.isEmpty {
                Label(category, systemImage: "tag")
                    .font(.subheadline)
            }
        }
        .foregroundStyle(.secondary)
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
    let score: Int

    var body: some View {
        Text("\(score)")
            .font(.caption.bold())
            .monospacedDigit()
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.15), in: Capsule())
            .foregroundStyle(color)
    }

    private var color: Color {
        if score >= 75 { return .green }
        if score >= 45 { return .orange }
        return .red
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
