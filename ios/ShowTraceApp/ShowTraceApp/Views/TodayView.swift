import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var digest: DigestResponse?
    @State private var events: [ShowEvent] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showDigest = false

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
                            soonSection
                            focusSection
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
            .sheet(isPresented: $showDigest) {
                DigestView()
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
                    .foregroundStyle(.primary)
            }
            Spacer()
        }
        .padding(.horizontal, 20)
        .padding(.top, 18)
        .padding(.bottom, 14)
    }

    private var summaryBanner: some View {
        Button {
            showDigest = true
        } label: {
            HStack(alignment: .center, spacing: 14) {
                Text("\(summaryCount)")
                    .font(.system(size: 38, weight: .heavy))
                    .foregroundStyle(Color.showRadarAccent)
                    .monospacedDigit()
                    .minimumScaleFactor(0.75)

                VStack(alignment: .leading, spacing: 5) {
                    Text("条关注演出")
                        .font(.system(size: 17, weight: .bold))
                        .foregroundStyle(.primary)
                    Text(summarySubtitle)
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)
                }
                Spacer(minLength: 0)
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.secondary)
            }
            .padding(16)
            .background(summaryGradient, in: RoundedRectangle(cornerRadius: 18))
            .overlay {
                RoundedRectangle(cornerRadius: 18)
                    .stroke(Color.primary.opacity(0.06), lineWidth: 0.5)
            }
            .padding(.horizontal, 20)
        }
        .buttonStyle(.plain)
    }

    private var soonSection: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text("⚡ 最近就开始")
                .font(.system(size: 19, weight: .bold))
                .padding(.horizontal, 20)
                .padding(.top, 20)

            if topPicks.isEmpty {
                EmptyMiniState(title: "暂无近期关注演出")
                    .padding(.horizontal, 20)
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 11) {
                        ForEach(topPicks) { event in
                            TopPickCard(event: event)
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 2)
                }
            }
        }
    }

    private var focusSection: some View {
        VStack(alignment: .leading, spacing: 11) {
            Text("为你关注")
                .font(.system(size: 19, weight: .bold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 20)
                .padding(.top, 20)

            if events.isEmpty {
                EmptyMiniState(title: "暂无关注演出")
                    .padding(.horizontal, 20)
            } else {
                LazyVStack(spacing: 11) {
                    ForEach(events.prefix(8)) { event in
                        EventCard(event: event) {
                            Task { await load() }
                        }
                    }
                }
                .padding(.horizontal, 20)
            }
        }
    }

    private var topPicks: [ShowEvent] {
        Array(events.sorted(by: compareEventsByDate).prefix(5))
    }

    // Headline number describes the list actually shown below (the keep list),
    // so the count and the "为你关注" section can't contradict each other.
    private var summaryCount: Int {
        events.count
    }

    private var summarySubtitle: String {
        let sources = Set(events.compactMap { EventSource.label(for: $0.source) }).sorted().prefix(3)
        let sourceText = sources.isEmpty ? "多个来源" : sources.joined(separator: " / ")
        if let todayCount = digest?.eventCount {
            return "今日新增 \(todayCount) 条 · 精选自 \(sourceText)"
        }
        return "按你的口味精选 · 来自 \(sourceText)"
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
        let client = APIClient(settings: settings)
        // The digest is optional (it 404s before today's digest is generated),
        // so fetch it best-effort and only treat the events fetch as fatal.
        async let digestResponse = try? client.fetchDigest()
        async let eventsResponse = client.fetchEvents(decision: .keep, limit: 80)
        do {
            let fetchedEvents = try await eventsResponse
            events = fetchedEvents.items
            digest = await digestResponse
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

private struct TopPickCard: View {
    let event: ShowEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            poster

            VStack(alignment: .leading, spacing: 7) {
                HStack(alignment: .center) {
                    Text(category)
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(Color.showRadarAccent)
                    Spacer(minLength: 8)
                    Text(scoreText)
                        .font(.system(size: 11.5, weight: .semibold))
                        .foregroundStyle(Color.showRadarAccent)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.showRadarAccent.opacity(0.12), in: Capsule())
                }

                Text(event.title)
                    .font(.system(size: 14.5, weight: .bold))
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                    .frame(minHeight: 36, alignment: .topLeading)

                Label(event.eventDate ?? "日期待定", systemImage: "calendar")
                    .font(.system(size: 12.5))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            .padding(12)
        }
        .frame(width: 210)
        .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.primary.opacity(0.06), lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.05), radius: 16, x: 0, y: 8)
    }

    private var poster: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(
                LinearGradient(
                    colors: EventCategory.posterColors(for: category),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .frame(height: 112)
            .overlay {
                Image(systemName: EventCategory.icon(for: category))
                    .font(.system(size: 28))
                    .foregroundStyle(.primary.opacity(0.42))
            }
            .padding(6)
    }

    private var category: String {
        EventCategory.resolved(for: event)
    }

    private var scoreText: String {
        if let score = event.interestMatchScore {
            return "\(score)"
        }
        return "关注"
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
