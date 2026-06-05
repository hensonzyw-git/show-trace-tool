import SwiftUI

struct SubscriptionView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var artistsText = ""
    @State private var city = ""
    @State private var keywordsText = ""
    @State private var sources: [String: Bool] = [:]
    @State private var isLoading = false
    @State private var isSaving = false
    @State private var message: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("关注艺人") {
                    TextEditor(text: $artistsText)
                        .frame(minHeight: 90)
                    Text("每行一个艺人，全国巡演都会进入监控。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("本地发现") {
                    TextField("城市", text: $city)
                    TextEditor(text: $keywordsText)
                        .frame(minHeight: 90)
                    Text("关键词每行一个，例如：展览、音乐节、话剧。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("启用来源") {
                    if sources.isEmpty {
                        Text("暂无来源配置")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(sources.keys.sorted(), id: \.self) { key in
                            Toggle(key, isOn: binding(for: key))
                        }
                    }
                }

                if let message {
                    Section {
                        Text(message)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("订阅")
            .toolbar {
                ToolbarItem {
                    Button {
                        Task { await load() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(isLoading || isSaving)
                }
                ToolbarItem {
                    Button {
                        Task { await save() }
                    } label: {
                        if isSaving {
                            ProgressView()
                        } else {
                            Image(systemName: "checkmark")
                        }
                    }
                    .disabled(isLoading || isSaving)
                    .accessibilityLabel("保存订阅")
                }
            }
            .task {
                await load()
            }
        }
    }

    private func binding(for key: String) -> Binding<Bool> {
        Binding(
            get: { sources[key, default: false] },
            set: { sources[key] = $0 }
        )
    }

    @MainActor
    private func load() async {
        guard settings.isConfigured else { return }
        isLoading = true
        message = nil
        do {
            let subscription = try await APIClient(settings: settings).fetchSubscription()
            artistsText = subscription.artists.joined(separator: "\n")
            city = subscription.local.city ?? ""
            keywordsText = subscription.local.keywords.joined(separator: "\n")
            sources = subscription.sources.mapValues { $0.enabled ?? false }
        } catch {
            message = error.localizedDescription
        }
        isLoading = false
    }

    @MainActor
    private func save() async {
        guard settings.isConfigured else { return }
        isSaving = true
        message = nil
        let subscription = Subscription(
            artists: lines(from: artistsText),
            local: LocalSubscription(city: city.trimmingCharacters(in: .whitespacesAndNewlines), keywords: lines(from: keywordsText)),
            sources: sources.mapValues { SourceSubscription(enabled: $0) }
        )
        do {
            _ = try await APIClient(settings: settings).saveSubscription(subscription)
            message = "已保存，下一次 worker 会使用新订阅。"
        } catch {
            message = error.localizedDescription
        }
        isSaving = false
    }

    private func lines(from text: String) -> [String] {
        text
            .split(whereSeparator: \.isNewline)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }
}
