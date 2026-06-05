import SwiftUI

struct EventsView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var selectedSegment: InterestSegment = .keep
    @State private var events: [ShowEvent] = []
    @State private var total = 0
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("列表", selection: $selectedSegment) {
                    ForEach(InterestSegment.allCases) { segment in
                        Text(segment.title).tag(segment)
                    }
                }
                .pickerStyle(.segmented)
                .padding([.horizontal, .top])
                .onChange(of: selectedSegment) { _, _ in
                    Task { await load() }
                }

                Group {
                    if isLoading && events.isEmpty {
                        ProgressView()
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else if let errorMessage {
                        ErrorStateView(message: errorMessage) {
                            Task { await load() }
                        }
                    } else if events.isEmpty {
                        EmptyStateView(title: "暂无\(selectedSegment.title)事件", systemImage: "tray")
                    } else {
                        List(events) { event in
                            EventCard(event: event) {
                                Task { await load() }
                            }
                            .listRowSeparator(.hidden)
                            .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                        }
                        .listStyle(.plain)
                        .refreshable {
                            await load()
                        }
                    }
                }
            }
            .navigationTitle(selectedSegment.title)
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

    @MainActor
    private func load() async {
        guard settings.isConfigured else { return }
        isLoading = true
        errorMessage = nil
        do {
            let response = try await APIClient(settings: settings).fetchEvents(decision: selectedSegment)
            events = response.items
            total = response.total
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
