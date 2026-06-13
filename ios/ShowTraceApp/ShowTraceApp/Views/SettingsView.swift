import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings

    @State private var runs: [RunItem] = []
    @State private var testMessage: String?
    @State private var isTesting = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    header
                    settingsSection("外观") {
                        SettingsCard {
                            themePicker
                                .padding(.horizontal, 15)
                                .padding(.vertical, 13)
                        }
                    }
                    settingsSection("数据采集") {
                        SettingsCard {
                            NavigationLink {
                                RunsView()
                            } label: {
                                SettingsRow(
                                    icon: "chart.xyaxis.line",
                                    title: "采集记录",
                                    subtitle: latestRunSubtitle,
                                    accentIcon: true,
                                    trailing: AnyView(runStatusView)
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    settingsSection("连接") {
                        SettingsCard {
                            TextField("https://example.com", text: $settings.baseURL)
                                .font(.system(size: 15))
                                .autocorrectionDisabled()
                                .textInputAutocapitalization(.never)
                                .padding(.horizontal, 15)
                                .padding(.top, 13)
                            SettingsDivider(hasIcon: false)
                            SecureField("API token", text: $settings.apiToken)
                                .font(.system(size: 15))
                                .autocorrectionDisabled()
                                .textInputAutocapitalization(.never)
                                .padding(.horizontal, 15)
                                .padding(.vertical, 13)
                            SettingsDivider(hasIcon: false)
                            HStack {
                                Button {
                                    settings.useProductionServer()
                                } label: {
                                    Label("使用生产地址", systemImage: "server.rack")
                                }
                                Spacer()
                                Button {
                                    Task { await testConnection() }
                                } label: {
                                    if isTesting {
                                        ProgressView()
                                    } else {
                                        Text("测试连接")
                                    }
                                }
                                .disabled(isTesting)
                            }
                            .font(.system(size: 14, weight: .semibold))
                            .padding(.horizontal, 15)
                            .padding(.vertical, 12)
                        }
                        if let testMessage {
                            Text(testMessage)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                                .padding(.horizontal, 20)
                                .padding(.top, 8)
                        }
                    }
                    settingsSection("关于") {
                        SettingsCard {
                            SettingsRow(
                                title: "版本",
                                trailing: AnyView(Text(appVersion).font(.system(size: 14)).foregroundStyle(.secondary))
                            )
                        }
                    }
                    Text("版本号读自 Bundle · 个人工具 · 无账号体系")
                        .font(.system(size: 11.5))
                        .foregroundStyle(.tertiary)
                        .frame(maxWidth: .infinity)
                        .padding(.top, 18)
                }
                .padding(.bottom, 92)
            }
            .background(Color.showRadarScreenBackground)
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(.hidden, for: .navigationBar)
            .task {
                await loadRuns()
            }
        }
    }

    private var header: some View {
        Text("设置")
            .font(.system(size: 32, weight: .heavy))
            .foregroundStyle(.primary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 14)
    }

    private var themePicker: some View {
        Picker("主题", selection: $settings.themeMode) {
            ForEach(ThemeMode.allCases) { mode in
                Text(mode.title).tag(mode)
            }
        }
        .pickerStyle(.segmented)
    }

    private var runStatusView: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(RunStatus.color(latestRun?.status))
                .frame(width: 7, height: 7)
            Text(RunStatus.label(latestRun?.status))
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(RunStatus.color(latestRun?.status))
        }
    }

    @ViewBuilder
    private func settingsSection<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        Text(title)
            .font(.system(size: 19, weight: .bold))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 20)
            .padding(.top, 20)
            .padding(.bottom, 9)
        content()
    }

    @MainActor
    private func loadRuns() async {
        guard settings.isConfigured else { return }
        // This only powers the latest-run status preview; fail silently so it
        // can't clobber the connection-test message shown in the 连接 section.
        runs = (try? await APIClient(settings: settings).fetchRuns(limit: 5).items) ?? runs
    }

    @MainActor
    private func testConnection() async {
        isTesting = true
        testMessage = "正在测试 \(settings.normalizedBaseURL) ..."
        do {
            _ = try await APIClient(settings: settings).fetchEvents(decision: .keep, limit: 1)
            testMessage = "连接成功。"
            await loadRuns()
        } catch {
            testMessage = error.localizedDescription
        }
        isTesting = false
    }

    private var latestRun: RunItem? {
        runs.first
    }

    private var latestRunSubtitle: String {
        guard let latestRun else { return "暂无运行记录" }
        return "最近一次 \(latestRun.startedAt)"
    }

    private var appVersion: String {
        let info = Bundle.main.infoDictionary
        let version = info?["CFBundleShortVersionString"] as? String ?? "—"
        let build = info?["CFBundleVersion"] as? String ?? "—"
        return "\(version) (\(build))"
    }
}

private struct SettingsCard<Content: View>: View {
    private let content: () -> Content

    init(@ViewBuilder content: @escaping () -> Content) {
        self.content = content
    }

    var body: some View {
        VStack(spacing: 0) {
            content()
        }
        .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.primary.opacity(0.06), lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.05), radius: 16, x: 0, y: 8)
        .padding(.horizontal, 20)
    }
}

private struct SettingsRow: View {
    var icon: String? = nil
    let title: String
    var subtitle: String? = nil
    var accentIcon = false
    var trailing: AnyView? = nil

    var body: some View {
        HStack(spacing: 12) {
            if let icon {
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .medium))
                    .foregroundStyle(accentIcon ? Color.showRadarAccent : Color.secondary)
                    .frame(width: 19)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 15.5, weight: .semibold))
                    .foregroundStyle(.primary)
                if let subtitle {
                    Text(subtitle)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 8)
            if let trailing {
                trailing
            } else {
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.horizontal, 15)
        .padding(.vertical, 13)
    }
}

private struct SettingsDivider: View {
    let hasIcon: Bool

    var body: some View {
        Rectangle()
            .fill(Color.primary.opacity(0.07))
            .frame(height: 0.5)
            .padding(.leading, hasIcon ? 46 : 15)
    }
}
