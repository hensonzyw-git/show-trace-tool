import SwiftUI

struct EventsView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var selectedSegment: InterestSegment = .keep
    @State private var selectedCategory = "全部"
    @State private var searchText = ""
    @State private var events: [ShowEvent] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                header
                tasteFilter
                categoryFilter
                countLine

                Group {
                    if isLoading && events.isEmpty {
                        ProgressView()
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else if let errorMessage {
                        ErrorStateView(message: errorMessage) {
                            Task { await load() }
                        }
                    } else if filteredEvents.isEmpty {
                        EmptyStateView(title: emptyStateTitle, systemImage: "tray")
                    } else {
                        ScrollView {
                            LazyVStack(spacing: 11) {
                                ForEach(filteredEvents) { event in
                                    EventCard(event: event)
                                }
                            }
                            .padding(.horizontal, 20)
                            .padding(.top, 8)
                            .padding(.bottom, 92)
                        }
                        .background(Color.showRadarScreenBackground)
                        .refreshable {
                            await load()
                        }
                    }
                }
            }
            .background(Color.showRadarScreenBackground)
            // The large title lives in the custom `header`; keep the nav bar
            // chromeless so it isn't shown twice.
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(.hidden, for: .navigationBar)
            .task {
                await load()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("全部演出")
                    .font(.system(size: 32, weight: .heavy))
                    .tracking(-0.6)
                Spacer()
            }

            HStack(spacing: 7) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("搜索演出、艺人、场馆", text: $searchText)
                    .font(.system(size: 16))
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .submitLabel(.search)
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .frame(height: 38)
            .padding(.horizontal, 11)
            .background(Color.secondary.opacity(0.10), in: RoundedRectangle(cornerRadius: 11))
        }
        .padding(.horizontal, 20)
        .padding(.top, 14)
        .padding(.bottom, 6)
    }

    private var tasteFilter: some View {
        Picker("兴趣", selection: $selectedSegment) {
            ForEach(InterestSegment.allCases) { segment in
                Text(segment.title).tag(segment)
            }
        }
        .pickerStyle(.segmented)
        .padding(.horizontal, 20)
        .padding(.top, 6)
        .onChange(of: selectedSegment) {
            Task { await load() }
        }
    }

    private var categoryFilter: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(EventCategory.filters, id: \.self) { category in
                    FilterPill(title: category, isSelected: selectedCategory == category, accentFill: true) {
                        selectedCategory = category
                    }
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 2)
        }
    }

    private var countLine: some View {
        HStack {
            Text("\(filteredEvents.count) 场 · 按日期")
                .font(.system(size: 12.5))
                .foregroundStyle(.secondary)
                .lineLimit(1)
            Spacer()
            Text("仅未过期")
                .font(.system(size: 12.5))
                .foregroundStyle(.tertiary)
        }
        .padding(.horizontal, 20)
        .padding(.top, 10)
        .padding(.bottom, 2)
    }

    private var filteredEvents: [ShowEvent] {
        events.filter { event in
            EventCategory.matches(selectedCategory, event: event) && matchesSearch(event)
        }
    }

    private func matchesSearch(_ event: ShowEvent) -> Bool {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return true }
        let haystack = [event.title, event.artist, event.venue, event.city]
            .compactMap { $0 }
            .joined(separator: " ")
        return haystack.localizedCaseInsensitiveContains(query)
    }

    private var emptyStateTitle: String {
        if !searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return "没有匹配「\(searchText)」的演出"
        }
        if selectedCategory != "全部" {
            return "「\(selectedCategory)」分类下暂无\(selectedSegment.title)演出"
        }
        return "暂无\(selectedSegment.title)演出"
    }

    @MainActor
    private func load() async {
        guard settings.isConfigured else { return }
        isLoading = true
        errorMessage = nil
        do {
            // 未过期由服务端过滤（date_from=今天，含日期待定）；类目/搜索在客户端做，
            // 故拉一个较大窗口供本地筛选。
            let response = try await APIClient(settings: settings).fetchEvents(
                decision: selectedSegment,
                dateFrom: todayString,
                limit: 200
            )
            events = response.items
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private var todayString: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: Date())
    }
}

private struct FilterPill: View {
    let title: String
    let isSelected: Bool
    let accentFill: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 13, weight: isSelected ? .semibold : .medium))
                .foregroundStyle(foreground)
                .padding(.horizontal, 13)
                .padding(.vertical, 7)
                .background(pillBackground, in: Capsule())
                .overlay {
                    if !isSelected {
                        Capsule()
                            .stroke(Color.primary.opacity(0.07), lineWidth: 1)
                    }
                }
        }
        .buttonStyle(.plain)
    }

    private var foreground: Color {
        if isSelected {
            return accentFill ? .white : Color.showRadarScreenBackground
        }
        return .secondary
    }

    private var pillBackground: Color {
        if isSelected {
            return accentFill ? .showRadarAccent : .primary
        }
        return Color.showRadarCardBackground
    }
}
