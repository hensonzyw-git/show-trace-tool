import SwiftUI

struct DigestView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var digest: DigestResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && digest == nil {
                    ProgressView()
                } else if let errorMessage {
                    ErrorStateView(message: errorMessage) {
                        Task { await load() }
                    }
                } else if let digest {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            HStack {
                                Text(digest.date)
                                    .font(.headline)
                                Spacer()
                                if let count = digest.eventCount {
                                    Text("\(count) 条")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            Text(markdownText(digest.markdown))
                                .font(.body)
                                .textSelection(.enabled)
                        }
                        .padding()
                    }
                    .refreshable {
                        await load()
                    }
                } else {
                    EmptyStateView(title: "暂无今日摘要", systemImage: "doc.text")
                }
            }
            .navigationTitle("今日摘要")
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
            digest = try await APIClient(settings: settings).fetchDigest()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func markdownText(_ markdown: String) -> AttributedString {
        (try? AttributedString(markdown: markdown)) ?? AttributedString(markdown)
    }
}
