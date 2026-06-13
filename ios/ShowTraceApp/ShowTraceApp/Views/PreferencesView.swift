import SwiftUI

/// 偏好管理（订阅范围 + 偏好二合一）。
/// 自然语言反馈用于修改画像；艺人、城市、数据源继续通过订阅接口保存。
struct PreferencesView: View {
    @EnvironmentObject private var settings: AppSettings

    @State private var profile: PreferenceProfile?
    @State private var artists: [String] = []
    @State private var newArtist = ""
    @State private var city = ""
    @State private var keywords: [String] = []
    @State private var sources: [String: Bool] = [:]

    @State private var feedback = ""
    @State private var isLoading = false
    @State private var isSubmitting = false
    @State private var isSaving = false
    @State private var savePending = false
    @State private var feedbackResult: FeedbackResult?
    @State private var subscriptionMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    header
                    feedbackCard
                    artistSection
                    cityAndSourceSection
                    profileSection
                    if let subscriptionMessage {
                        Text(subscriptionMessage)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .padding(.horizontal, 20)
                            .padding(.top, 12)
                    }
                }
                .padding(.bottom, 92)
            }
            .background(Color.showRadarScreenBackground)
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(.hidden, for: .navigationBar)
            .refreshable {
                await load()
            }
            .task {
                await load()
            }
        }
    }

    private var header: some View {
        Text("偏好管理")
            .font(.system(size: 32, weight: .heavy))
            .tracking(-0.6)
            .foregroundStyle(.primary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 14)
    }

    private var feedbackCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("用一句话调教雷达", systemImage: "bolt.fill")
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(.primary)
                .labelStyle(.titleAndIcon)
                .symbolRenderingMode(.hierarchical)

            HStack(alignment: .bottom, spacing: 9) {
                TextField("多推荐 livehouse，少看大型晚会", text: $feedback, axis: .vertical)
                    .font(.system(size: 14))
                    .lineLimit(2...4)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 11)
                    .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 12))
                    .overlay {
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.showRadarSeparator, lineWidth: 0.5)
                    }

                Button {
                    Task { await submitFeedback() }
                } label: {
                    if isSubmitting {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Image(systemName: "paperplane")
                            .font(.system(size: 16, weight: .bold))
                    }
                }
                .frame(width: 32, height: 32)
                .foregroundStyle(.white)
                .background(Color.showRadarAccent, in: Circle())
                .disabled(feedback.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting)
            }

            FeedbackResultRow(result: feedbackResult, isSubmitting: isSubmitting)
        }
        .padding(15)
        .background(feedbackGradient, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.showRadarSeparator, lineWidth: 0.5)
        }
        .padding(.horizontal, 20)
    }

    private var artistSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            ShowRadarSectionLabel(title: "关注艺人")
            FlowLayout(spacing: 9) {
                ForEach(artists, id: \.self) { artist in
                    ArtistChip(name: artist) {
                        artists.removeAll { $0 == artist }
                        Task { await saveSubscription(showMessage: false) }
                    }
                }

                HStack(spacing: 7) {
                    TextField("添加", text: $newArtist)
                        .font(.system(size: 13.5, weight: .semibold))
                        .frame(width: 70)
                        .submitLabel(.done)
                        .onSubmit(addArtist)
                    Button(action: addArtist) {
                        Image(systemName: "plus")
                            .font(.system(size: 13, weight: .bold))
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 13)
                .padding(.vertical, 8)
                .overlay {
                    Capsule(style: .continuous)
                        .stroke(Color.primary.opacity(0.10), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3]))
                }
                .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 20)
        }
    }

    private var cityAndSourceSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            ShowRadarSectionLabel(title: "城市与数据源")
            ShowRadarCard {
                HStack(spacing: 11) {
                    Image(systemName: "mappin.and.ellipse")
                        .foregroundStyle(Color.showRadarAccent)
                        .frame(width: 19)
                    Text("城市")
                        .font(.system(size: 15.5))
                    Spacer()
                    TextField("上海", text: $city)
                        .font(.system(size: 15, weight: .semibold))
                        .multilineTextAlignment(.trailing)
                        .frame(width: 96)
                        .submitLabel(.done)
                        .onSubmit {
                            Task { await saveSubscription(showMessage: true) }
                        }
                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.tertiary)
                }
                .padding(.horizontal, 15)
                .padding(.vertical, 13)

                Divider()
                    .padding(.leading, 45)

                ForEach(sourceKeys, id: \.self) { key in
                    SourceToggleRow(
                        key: key,
                        isOn: binding(for: key)
                    )
                    if key != sourceKeys.last {
                        Divider()
                            .padding(.leading, 30)
                    }
                }
            }
            .padding(.horizontal, 20)
        }
    }

    @ViewBuilder
    private var profileSection: some View {
        if let profile {
            VStack(alignment: .leading, spacing: 0) {
                ShowRadarSectionLabel(title: "兴趣画像", trailing: "自然语言可改")
                ShowRadarCard {
                    VStack(alignment: .leading, spacing: 12) {
                        ProfileBlock(
                            label: "关注的演出范围",
                            items: profile.includeCategories + profile.positiveSignals,
                            tone: .keep
                        )
                        ProfileBlock(
                            label: "不关注的演出范围",
                            items: profile.excludeCategories + profile.negativeSignals,
                            tone: .filter
                        )
                        PreferenceRanking(items: profile.rankingPreferences)
                    }
                    .padding(15)
                }
                .padding(.horizontal, 20)
            }
        }
    }

    private var sourceKeys: [String] {
        let preferred = ["damai", "showstart", "motianlun"]
        let extras = sources.keys.filter { !preferred.contains($0) }.sorted()
        return preferred + extras
    }

    private var feedbackGradient: LinearGradient {
        LinearGradient(
            colors: [
                Color.showRadarAccent.opacity(0.16),
                Color.showRadarCardBackground,
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    private func binding(for key: String) -> Binding<Bool> {
        Binding(
            get: { sources[key, default: false] },
            set: {
                sources[key] = $0
                Task { await saveSubscription(showMessage: false) }
            }
        )
    }

    private func addArtist() {
        let name = newArtist.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty, !artists.contains(name) else { return }
        artists.append(name)
        newArtist = ""
        Task { await saveSubscription(showMessage: false) }
    }

    @MainActor
    private func load() async {
        guard settings.isConfigured else { return }
        isLoading = true
        subscriptionMessage = nil
        let client = APIClient(settings: settings)
        async let profileResult = try? client.fetchPreferences()
        do {
            let subscription = try await client.fetchSubscription()
            artists = subscription.artists
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
        feedbackResult = nil
        do {
            let response = try await APIClient(settings: settings).sendFeedback(
                PreferenceFeedbackRequest(
                    feedback: text,
                    eventId: nil,
                    rescoreExisting: false,
                    rescoreLimit: 0
                )
            )
            if let nextProfile = response.profile {
                profile = nextProfile
            }
            feedbackResult = FeedbackResult(
                updates: response.updates,
                rescoredEvents: response.rescoredEvents ?? 0,
                fallbackMessage: nil
            )
            feedback = ""
        } catch {
            feedbackResult = FeedbackResult(
                updates: nil,
                rescoredEvents: 0,
                fallbackMessage: preferenceErrorMessage(error)
            )
        }
        isSubmitting = false
    }

    @MainActor
    private func saveSubscription(showMessage: Bool) async {
        guard settings.isConfigured else { return }
        // 已有保存在途时不并发发起，只记下「还需再保存一次」，由在途任务结束后补发，
        // 既避免并发 PUT 竞争，又不会丢掉途中产生的改动。
        guard !isSaving else {
            savePending = true
            return
        }
        isSaving = true
        if showMessage {
            subscriptionMessage = nil
        }
        let subscription = Subscription(
            artists: artists,
            local: LocalSubscription(
                city: city.trimmingCharacters(in: .whitespacesAndNewlines),
                keywords: keywords
            ),
            sources: sources.mapValues { SourceSubscription(enabled: $0) }
        )
        do {
            let saved = try await APIClient(settings: settings).saveSubscription(subscription)
            // 仅在用户主动保存（城市提交）时回写，避免后台开关保存把正在编辑的城市字段替换掉。
            if showMessage {
                city = saved.local.city ?? city
                subscriptionMessage = "已保存，下一次采集会使用新设置。"
            }
        } catch {
            subscriptionMessage = error.localizedDescription
        }
        isSaving = false
        if savePending {
            savePending = false
            await saveSubscription(showMessage: false)
        }
    }

    private func preferenceErrorMessage(_ error: Error) -> String {
        if case APIError.badStatus(404, _) = error {
            return "服务器暂未部署喜好接口；部署最新后端后这里会自动可用。"
        }
        return error.localizedDescription
    }
}

private struct FeedbackResult {
    let updates: PreferenceUpdates?
    let rescoredEvents: Int
    let fallbackMessage: String?
}

private struct FeedbackResultRow: View {
    let result: FeedbackResult?
    let isSubmitting: Bool

    var body: some View {
        FlowLayout(spacing: 7) {
            if isSubmitting {
                Text("正在更新")
                    .foregroundStyle(.secondary)
            } else if let result {
                if let fallbackMessage = result.fallbackMessage {
                    Text(fallbackMessage)
                        .foregroundStyle(.secondary)
                } else if let updates = result.updates, !updates.isEmpty {
                    Text("已更新")
                        .foregroundStyle(.secondary)
                    ForEach(updates.includeCategories + updates.positiveSignals, id: \.self) { item in
                        UpdateChip(prefix: "+", text: item, tone: .keep)
                    }
                    ForEach(updates.excludeCategories + updates.negativeSignals, id: \.self) { item in
                        UpdateChip(prefix: "-", text: item, tone: .filter)
                    }
                    if result.rescoredEvents > 0 {
                        Text("已重打分 \(result.rescoredEvents) 条")
                            .foregroundStyle(.tertiary)
                    } else {
                        Text("偏好已保存")
                            .foregroundStyle(.tertiary)
                    }
                } else {
                    Text("没有识别到明确改动，可换种说法再试")
                        .foregroundStyle(.secondary)
                }
            } else {
                Text("已更新的规则会在这里回显")
                    .foregroundStyle(.tertiary)
            }
        }
        .font(.system(size: 12))
    }
}

private struct UpdateChip: View {
    let prefix: String
    let text: String
    let tone: ProfileTone

    var body: some View {
        Text("\(prefix) \(text)")
            .font(.system(size: 12.5, weight: .semibold))
            .foregroundStyle(tone.foreground)
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(tone.background, in: RoundedRectangle(cornerRadius: 7))
    }
}

private struct ArtistChip: View {
    let name: String
    let remove: () -> Void

    var body: some View {
        HStack(spacing: 7) {
            Text(String(name.prefix(1)))
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(.white)
                .frame(width: 23, height: 23)
                .background(Color.showRadarAccent, in: Circle())
            Text(name)
                .font(.system(size: 14, weight: .semibold))
                .lineLimit(1)
            Button(action: remove) {
                Image(systemName: "xmark")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(.tertiary)
            }
            .buttonStyle(.plain)
        }
        .padding(.leading, 8)
        .padding(.trailing, 12)
        .padding(.vertical, 7)
        .background(Color.showRadarCardBackground, in: Capsule())
        .overlay {
            Capsule()
                .stroke(Color.showRadarSeparator, lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.04), radius: 12, x: 0, y: 6)
    }
}

private struct SourceToggleRow: View {
    let key: String
    @Binding var isOn: Bool

    var body: some View {
        HStack(spacing: 11) {
            Circle()
                .fill(EventSource.color(for: key))
                .frame(width: 9, height: 9)
                .padding(.leading, 5)
            HStack(alignment: .firstTextBaseline, spacing: 7) {
                Text(EventSource.label(for: key) ?? key)
                    .font(.system(size: 15.5))
                Text(key)
                    .font(.system(size: 11.5, design: .monospaced))
                    .foregroundStyle(.tertiary)
            }
            Spacer()
            Toggle("", isOn: $isOn)
                .labelsHidden()
                .tint(Color.showRadarAccent)
        }
        .padding(.horizontal, 15)
        .padding(.vertical, 12)
    }
}

private enum ProfileTone {
    case keep
    case filter

    var foreground: Color {
        switch self {
        case .keep:
            return DecisionStyle.foreground("keep")
        case .filter:
            return DecisionStyle.foreground("filter")
        }
    }

    var background: Color {
        switch self {
        case .keep:
            return DecisionStyle.background("keep")
        case .filter:
            return DecisionStyle.background("filter")
        }
    }
}

private struct ProfileBlock: View {
    let label: String
    let items: [String]
    let tone: ProfileTone

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label)
                .font(.system(size: 12.5, weight: .semibold))
                .foregroundStyle(.secondary)
            FlowLayout(spacing: 7) {
                if items.isEmpty {
                    Text("暂无")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(items, id: \.self) { item in
                        Text(item)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(tone.foreground)
                            .strikethrough(tone == .filter, color: .secondary)
                            .padding(.horizontal, 11)
                            .padding(.vertical, 5)
                            .background(tone.background, in: RoundedRectangle(cornerRadius: 8))
                    }
                }
            }
        }
    }
}

private struct PreferenceRanking: View {
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("倾向")
                .font(.system(size: 12.5, weight: .semibold))
                .foregroundStyle(.secondary)
            if items.isEmpty {
                Text("暂无")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                    HStack(spacing: 8) {
                        Text("\(index + 1)")
                            .font(.system(size: 14, weight: .heavy))
                            .foregroundStyle(Color.showRadarAccent)
                        Text(item)
                            .font(.system(size: 14))
                    }
                }
            }
        }
    }
}

private struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    init(spacing: CGFloat = 8) {
        self.spacing = spacing
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? 0
        var x: CGFloat = 0
        var y: CGFloat = 0
        var lineHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if maxWidth > 0, x > 0, x + size.width > maxWidth {
                x = 0
                y += lineHeight + spacing
                lineHeight = 0
            }
            x += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }
        return CGSize(width: maxWidth, height: y + lineHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var lineHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x > bounds.minX, x + size.width > bounds.maxX {
                x = bounds.minX
                y += lineHeight + spacing
                lineHeight = 0
            }
            subview.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }
    }
}
