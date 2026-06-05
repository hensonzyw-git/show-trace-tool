import SwiftUI

struct PreferencesView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var profile: PreferenceProfile?
    @State private var feedback = ""
    @State private var isLoading = false
    @State private var isSubmitting = false
    @State private var message: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("自然语言校准") {
                    TextEditor(text: $feedback)
                        .frame(minHeight: 110)
                    Button {
                        Task { await submitFeedback() }
                    } label: {
                        if isSubmitting {
                            ProgressView()
                        } else {
                            Label("提交反馈", systemImage: "paperplane")
                        }
                    }
                    .disabled(feedback.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting)
                }

                if let profile {
                    Section("关注") {
                        ChipList(items: profile.includeCategories)
                    }
                    Section("暂不关注") {
                        ChipList(items: profile.excludeCategories)
                    }
                    Section("倾向") {
                        ChipList(items: profile.rankingPreferences)
                    }
                    if !profile.positiveSignals.isEmpty {
                        Section("正向信号") {
                            ChipList(items: profile.positiveSignals)
                        }
                    }
                    if !profile.negativeSignals.isEmpty {
                        Section("负向信号") {
                            ChipList(items: profile.negativeSignals)
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
            .navigationTitle("喜好")
            .toolbar {
                ToolbarItem {
                    Button {
                        Task { await load() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(isLoading || isSubmitting)
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
        message = nil
        do {
            profile = try await APIClient(settings: settings).fetchPreferences()
        } catch {
            message = preferenceErrorMessage(error)
        }
        isLoading = false
    }

    @MainActor
    private func submitFeedback() async {
        let text = feedback.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        isSubmitting = true
        message = nil
        do {
            let response = try await APIClient(settings: settings).sendFeedback(
                PreferenceFeedbackRequest(
                    feedback: text,
                    eventId: nil,
                    rescoreExisting: true,
                    rescoreLimit: 500
                )
            )
            if let nextProfile = response.profile {
                profile = nextProfile
            } else {
                profile = try await APIClient(settings: settings).fetchPreferences()
            }
            let refreshed = response.rescoredEvents ?? 0
            message = refreshed > 0 ? "已按新喜好刷新 \(refreshed) 条事件。" : "已保存喜好。"
            feedback = ""
        } catch {
            message = preferenceErrorMessage(error)
        }
        isSubmitting = false
    }

    private func preferenceErrorMessage(_ error: Error) -> String {
        if case APIError.badStatus(404, _) = error {
            return "服务器暂未部署喜好接口。推荐、摘要、订阅和运行记录仍可使用；部署最新后端后这里会自动可用。"
        }
        return error.localizedDescription
    }
}

private struct ChipList: View {
    let items: [String]

    var body: some View {
        if items.isEmpty {
            Text("暂无")
                .foregroundStyle(.secondary)
        } else {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 88), spacing: 8)], alignment: .leading, spacing: 8) {
                ForEach(items, id: \.self) { item in
                    Text(item)
                        .font(.subheadline)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .frame(maxWidth: .infinity)
                        .background(Color.secondary.opacity(0.08), in: Capsule())
                }
            }
        }
    }
}
