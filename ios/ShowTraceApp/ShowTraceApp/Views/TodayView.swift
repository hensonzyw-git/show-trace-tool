import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var digest: DigestResponse?
    @State private var events: [ShowEvent] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showMarkdownDigest = false
    @State private var isLiveFallback = false

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && events.isEmpty && digest == nil {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let errorMessage {
                    ErrorStateView(message: errorMessage) {
                        Task { await load() }
                    }
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 0) {
                            header
                            summaryBanner
                            digestFeedSection
                            footerHint
                        }
                        .padding(.bottom, 92)
                    }
                    .refreshable {
                        await load()
                    }
                }
            }
            .background(Color.showRadarScreenBackground)
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(.hidden, for: .navigationBar)
            .sheet(isPresented: $showMarkdownDigest) {
                MarkdownDigestSheet(markdown: digest?.markdown ?? "")
            }
            .task {
                await load()
            }
        }
    }

    private var header: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 5) {
                Text(todayLabel)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Color.showRadarAccent)
                    .tracking(0.3)
                Text("今日雷达")
                    .font(.system(size: 32, weight: .heavy))
                    .tracking(-0.6)
                    .foregroundStyle(.primary)
            }
            Spacer()
        }
        .padding(.horizontal, 20)
        .padding(.top, 18)
        .padding(.bottom, 14)
    }

    private var summaryBanner: some View {
        Group {
            if hasMarkdownDigest {
                Button {
                    showMarkdownDigest = true
                } label: {
                    summaryBannerContent(showsChevron: true)
                }
                .buttonStyle(.plain)
            } else {
                summaryBannerContent(showsChevron: false)
            }
        }
    }

    private func summaryBannerContent(showsChevron: Bool) -> some View {
        HStack(alignment: .center, spacing: 14) {
            Text("\(summaryCount)")
                .font(.system(size: 36, weight: .heavy))
                .foregroundStyle(Color.showRadarAccent)
                .monospacedDigit()
                .minimumScaleFactor(0.75)

            VStack(alignment: .leading, spacing: 5) {
                Text("场高分演出")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(.primary)
                Text(summarySubtitle)
                    .font(.system(size: 12.5))
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
            }
            Spacer(minLength: 0)
            if showsChevron {
                HStack(spacing: 3) {
                    Text("完整摘要")
                    Image(systemName: "chevron.right")
                }
                .font(.system(size: 12.5, weight: .semibold))
                .foregroundStyle(Color.showRadarAccent)
            }
        }
        .padding(16)
        .background(summaryGradient, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.primary.opacity(0.06), lineWidth: 0.5)
        }
        .padding(.horizontal, 20)
    }

    private var digestFeedSection: some View {
        VStack(alignment: .leading, spacing: 11) {
            ShowRadarSectionLabel(title: "今日筛选", trailing: "按兴趣分")

            if digestEvents.isEmpty {
                EmptyMiniState(title: "暂无高分演出")
                    .padding(.horizontal, 20)
            } else {
                LazyVStack(spacing: 11) {
                    ForEach(digestEvents.prefix(8)) { event in
                        EventCard(event: event)
                    }
                }
                .padding(.horizontal, 20)
            }
        }
    }

    private var footerHint: some View {
        Text("下拉刷新 · 每日快照不实时更新")
            .font(.system(size: 12.5))
            .foregroundStyle(.tertiary)
            .frame(maxWidth: .infinity)
            .padding(.top, 16)
    }

    private var digestEvents: [ShowEvent] {
        guard isLiveFallback else { return events }
        return events.sorted { lhs, rhs in
            let leftScore = lhs.interestMatchScore ?? 0
            let rightScore = rhs.interestMatchScore ?? 0
            if leftScore != rightScore {
                return leftScore > rightScore
            }
            return compareEventsByDate(lhs, rhs)
        }
    }

    // Headline number = the snapshot feed shown below, so it never contradicts
    // the "今日筛选" list.
    private var summaryCount: Int {
        digestEvents.count
    }

    private var summarySubtitle: String {
        let sources = Set(digestEvents.compactMap { EventSource.label(for: $0.source) }).sorted().prefix(3)
        let sourceText = sources.isEmpty ? "多个来源" : sources.joined(separator: " / ")
        let generatedAt = digest?.generatedAt?.isEmpty == false ? " · \(digest!.generatedAt!) 快照" : ""
        let prefix = isLiveFallback ? "实时列表" : "今日新增 \(events.count) 条"
        return "\(prefix) · 来源 \(sourceText)\(generatedAt)"
    }

    private var hasMarkdownDigest: Bool {
        guard let markdown = digest?.markdown else { return false }
        return !markdown.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var summaryGradient: LinearGradient {
        LinearGradient(
            colors: [
                Color.showRadarAccent.opacity(0.18),
                Color.showRadarCardBackground,
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    private var todayLabel: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "yyyy.MM.dd EEEE"
        return formatter.string(from: Date())
    }

    @MainActor
    private func load() async {
        guard settings.isConfigured else { return }
        isLoading = true
        errorMessage = nil
        do {
            // 当日摘要是后端每日快照：feed 直接取 digest.events（已按兴趣分降序）。
            let fetched = try await APIClient(settings: settings).fetchDigest()
            digest = fetched
            events = fetched.feedEvents
            isLiveFallback = false
        } catch APIError.badStatus(404, _) {
            // 摘要快照缺失时，不让首页空掉；回退到实时 keep 列表。
            do {
                digest = nil
                events = try await fetchFallbackEvents()
                isLiveFallback = true
            } catch {
                errorMessage = error.localizedDescription
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func fetchFallbackEvents() async throws -> [ShowEvent] {
        let response = try await APIClient(settings: settings).fetchEvents(
            decision: .keep,
            dateFrom: todayQueryString,
            limit: 50
        )
        return response.items
    }

    private var todayQueryString: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: Date())
    }
}

private struct MarkdownDigestSheet: View {
    let markdown: String

    var body: some View {
        NavigationStack {
            ScrollView {
                Text(markdownText(markdown))
                    .font(.body)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
            }
            .navigationTitle("完整摘要")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }

    private func markdownText(_ markdown: String) -> AttributedString {
        (try? AttributedString(markdown: markdown)) ?? AttributedString(markdown)
    }
}

private struct EmptyMiniState: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.system(size: 13))
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(14)
            .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
    }
}

private func compareEventsByDate(_ lhs: ShowEvent, _ rhs: ShowEvent) -> Bool {
    // Sort by the digits of the date (yyyymmdd...), so formats like "2026-06-08",
    // "2026.06.08" and ranges "6.8-6.9" all order by their leading date. Missing
    // dates sort last.
    sortKey(lhs.eventDate) < sortKey(rhs.eventDate)
}

private func sortKey(_ date: String?) -> String {
    let digits = (date ?? "").filter(\.isNumber)
    return digits.isEmpty ? "99999999" : digits
}
