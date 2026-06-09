import SwiftUI

struct EventsView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var selectedSegment: InterestSegment = .keep
    @State private var selectedCategory = "全部"
    @State private var searchText = ""
    @State private var events: [ShowEvent] = []
    @State private var total = 0
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                header
                categoryFilter
                tasteFilter

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
                        List(filteredEvents) { event in
                            EventCard(event: event) {
                                Task { await load() }
                            }
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                            .listRowInsets(EdgeInsets(top: 6, leading: 20, bottom: 6, trailing: 20))
                        }
                        .listStyle(.plain)
                        .scrollContentBackground(.hidden)
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
            .toolbar {
                ToolbarItem {
                    Button {
                        Task { await load() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(isLoading)
                }
            }
            .safeAreaInset(edge: .bottom) {
                if total > 0 {
                    Text("共 \(total) 条")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 6)
                        .background(.bar)
                }
            }
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
            .padding(.vertical, 8)
        }
    }

    private var tasteFilter: some View {
        HStack(spacing: 8) {
            Text("口味")
                .font(.system(size: 12.5))
                .foregroundStyle(.secondary)
            ForEach(InterestSegment.allCases) { segment in
                FilterPill(title: segment.title, isSelected: selectedSegment == segment, accentFill: false) {
                    selectedSegment = segment
                    Task { await load() }
                }
            }
            Spacer(minLength: 8)
            Text("\(filteredEvents.count) 场 · 按日期")
                .font(.system(size: 12.5))
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 8)
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
            total = response.total
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
