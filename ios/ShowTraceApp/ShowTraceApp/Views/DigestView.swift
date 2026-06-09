import SwiftUI

struct DigestView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var digests: [DigestResponse] = []
    @State private var expandedDigestIDs: Set<String> = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && digests.isEmpty {
                    ProgressView()
                } else if let errorMessage {
                    ErrorStateView(message: errorMessage) {
                        Task { await load() }
                    }
                } else if !digests.isEmpty {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {
                            ForEach(digests) { digest in
                                DigestCard(
                                    digest: digest,
                                    isExpanded: isExpandedBinding(for: digest)
                                )
                            }
                        }
                        .padding()
                    }
                    .refreshable {
                        await load()
                    }
                } else {
                    EmptyStateView(title: "暂无历史摘要", systemImage: "doc.text")
                }
            }
            .navigationTitle("摘要")
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
            let response = try await APIClient(settings: settings).fetchDigests()
            digests = response.items
            if expandedDigestIDs.isEmpty, let first = response.items.first {
                expandedDigestIDs.insert(first.id)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func isExpandedBinding(for digest: DigestResponse) -> Binding<Bool> {
        Binding {
            expandedDigestIDs.contains(digest.id)
        } set: { isExpanded in
            if isExpanded {
                expandedDigestIDs.insert(digest.id)
            } else {
                expandedDigestIDs.remove(digest.id)
            }
        }
    }
}

private struct DigestCard: View {
    let digest: DigestResponse
    let isExpanded: Binding<Bool>

    var body: some View {
        DisclosureGroup(isExpanded: isExpanded) {
            Text(markdownText(digest.markdown ?? ""))
                .font(.body)
                .textSelection(.enabled)
                .padding(.top, 10)
        } label: {
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
        }
        .padding(14)
        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
    }

    private func markdownText(_ markdown: String) -> AttributedString {
        (try? AttributedString(markdown: markdown)) ?? AttributedString(markdown)
    }
}
