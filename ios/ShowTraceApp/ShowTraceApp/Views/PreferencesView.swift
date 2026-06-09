import SwiftUI

/// 偏好管理（订阅范围 + 偏好二合一）。
/// - 自然语言校准：POST /api/preferences/feedback（LLM 解析），展示 updates 让用户确认。
/// - 结构化：艺人 / 城市（单一来源）/ 数据源，整体 PUT /api/subscriptions。
/// - 画像展示：关注 / 暂不关注 / 倾向（只读，通过自然语言修改）。
struct PreferencesView: View {
    @EnvironmentObject private var settings: AppSettings

    @State private var profile: PreferenceProfile?
    @State private var artistsText = ""
    @State private var city = ""
    @State private var keywords: [String] = []        // 保留 round-trip，PUT 是整体覆盖
    @State private var sources: [String: Bool] = [:]

    @State private var feedback = ""
    @State private var isLoading = false
    @State private var isSubmitting = false
    @State private var isSaving = false
    @State private var feedbackMessage: String?
    @State private var subscriptionMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                feedbackSection
                profileSection
                artistsSection
                citySection
                sourcesSection
                subscriptionSaveSection
            }
            .navigationTitle("偏好管理")
            .toolbar {
                ToolbarItem {
                    Button {
                        Task { await load() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(isLoading || isSubmitting || isSaving)
                }
            }
            .task {
                await load()
            }
        }
    }

    // MARK: 自然语言校准

    private var feedbackSection: some View {
        Section("自然语言校准") {
            TextEditor(text: $feedback)
                .frame(minHeight: 90)
            Text("用一句话告诉它，例如「多推荐 livehouse，不想看亲子剧」。")
                .font(.footnote)
                .foregroundStyle(.secondary)
            Button {
                Task { await submitFeedback() }
            } label: {
                if isSubmitting {
                    ProgressView()
                } else {
                    Label("提交", systemImage: "paperplane")
                }
            }
            .disabled(feedback.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting)

            if let feedbackMessage {
                Text(feedbackMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: 画像展示（只读）

    @ViewBuilder
    private var profileSection: some View {
        if let profile {
            Section("关注的演出范围") {
                ChipList(items: profile.includeCategories + profile.positiveSignals)
            }
            Section("不关注的演出范围") {
                ChipList(items: profile.excludeCategories + profile.negativeSignals)
            }
            Section("倾向") {
                ChipList(items: profile.rankingPreferences)
            }
        }
    }

    // MARK: 艺人 / 城市 / 数据源（结构化）

    private var artistsSection: some View {
        Section("关注艺人") {
            TextEditor(text: $artistsText)
                .frame(minHeight: 80)
            Text("每行一个艺人，全国巡演都会进入监控。")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
    }

    private var citySection: some View {
        Section("城市") {
            TextField("城市，如 上海", text: $city)
                .autocorrectionDisabled()
        }
    }

    private var sourcesSection: some View {
        Section("数据源") {
            if sources.isEmpty {
                Text("暂无数据源配置")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(sources.keys.sorted(), id: \.self) { key in
                    Toggle(EventSource.label(for: key) ?? key, isOn: binding(for: key))
                }
            }
        }
    }

    private var subscriptionSaveSection: some View {
        Section {
            Button {
                Task { await saveSubscription() }
            } label: {
                if isSaving {
                    ProgressView()
                } else {
                    Label("保存艺人 / 城市 / 数据源", systemImage: "checkmark")
                }
            }
            .disabled(isLoading || isSaving)

            if let subscriptionMessage {
                Text(subscriptionMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func binding(for key: String) -> Binding<Bool> {
        Binding(
            get: { sources[key, default: false] },
            set: { sources[key] = $0 }
        )
    }

    // MARK: 数据

    @MainActor
    private func load() async {
        guard settings.isConfigured else { return }
        isLoading = true
        feedbackMessage = nil
        subscriptionMessage = nil
        let client = APIClient(settings: settings)
        // 画像可能 404（后端未部署喜好接口）→ best-effort；订阅失败才算错误。
        async let profileResult = try? client.fetchPreferences()
        do {
            let subscription = try await client.fetchSubscription()
            artistsText = subscription.artists.joined(separator: "\n")
            city = subscription.local.city ?? ""
            keywords = subscription.local.keywords
            sources = subscription.sources.mapValues { $0.enabled ?? false }
            profile = await profileResult
        } catch {
            subscriptionMessage = error.localizedDescription
        }
        isLoading = false
    }

    @MainActor
    private func submitFeedback() async {
        let text = feedback.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        isSubmitting = true
        feedbackMessage = nil
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
            }
            feedbackMessage = feedbackResultText(response)
            feedback = ""
        } catch {
            feedbackMessage = preferenceErrorMessage(error)
        }
        isSubmitting = false
    }

    // 展示后端到底改了什么（PRD 要求：让用户确认，而不是假定改对）。
    private func feedbackResultText(_ response: PreferenceFeedbackResponse) -> String {
        let rescored = response.rescoredEvents ?? 0
        let tail = rescored > 0 ? "，已刷新 \(rescored) 条评分" : ""
        if let updates = response.updates, !updates.isEmpty {
            return "已更新：\(updates.summary)\(tail)"
        }
        return "没有识别到明确改动，可换种说法再试\(tail)"
    }

    @MainActor
    private func saveSubscription() async {
        guard settings.isConfigured else { return }
        isSaving = true
        subscriptionMessage = nil
        let subscription = Subscription(
            artists: lines(from: artistsText),
            local: LocalSubscription(
                city: city.trimmingCharacters(in: .whitespacesAndNewlines),
                keywords: keywords
            ),
            sources: sources.mapValues { SourceSubscription(enabled: $0) }
        )
        do {
            let saved = try await APIClient(settings: settings).saveSubscription(subscription)
            city = saved.local.city ?? city
            subscriptionMessage = "已保存，下一次采集会使用新设置。"
        } catch {
            subscriptionMessage = error.localizedDescription
        }
        isSaving = false
    }

    private func lines(from text: String) -> [String] {
        text
            .split(whereSeparator: \.isNewline)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    private func preferenceErrorMessage(_ error: Error) -> String {
        if case APIError.badStatus(404, _) = error {
            return "服务器暂未部署喜好接口；部署最新后端后这里会自动可用。"
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
