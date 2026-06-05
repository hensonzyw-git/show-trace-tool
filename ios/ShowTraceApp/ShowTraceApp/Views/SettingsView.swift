import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var testMessage: String?
    @State private var isTesting = false
    @State private var runs: [RunItem] = []
    @State private var isLoadingRuns = false
    @State private var isTriggeringRun = false
    @State private var runMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("API") {
                    TextField("https://example.com", text: $settings.baseURL)
                        .autocorrectionDisabled()
                    SecureField("API token", text: $settings.apiToken)
                        .autocorrectionDisabled()
                    Button {
                        settings.useProductionServer()
                    } label: {
                        Label("使用服务器地址", systemImage: "server.rack")
                    }
                }

                Section {
                    Button {
                        Task { await testConnection() }
                    } label: {
                        if isTesting {
                            ProgressView()
                        } else {
                            Label("测试连接", systemImage: "network")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(isTesting)

                    if let testMessage {
                        Text(testMessage)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("运行") {
                    HStack {
                        Button {
                            Task { await loadRuns() }
                        } label: {
                            if isLoadingRuns {
                                ProgressView()
                            } else {
                                Label("刷新记录", systemImage: "clock.arrow.circlepath")
                            }
                        }
                        .disabled(isLoadingRuns || !settings.isConfigured)

                        Button {
                            Task { await triggerRun() }
                        } label: {
                            if isTriggeringRun {
                                ProgressView()
                            } else {
                                Label("手动采集", systemImage: "play")
                            }
                        }
                        .disabled(isTriggeringRun || !settings.isConfigured)
                    }

                    if let runMessage {
                        Text(runMessage)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }

                    if runs.isEmpty {
                        Text("暂无运行记录")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(runs) { run in
                            RunRow(run: run)
                        }
                    }
                }

                Section("说明") {
                    Text("API token 只保存在本机。开发时可以填本地地址；真机访问本机服务时需要使用局域网 IP。若 Xcode 真机调试连接异常，先关闭 VPN 或系统代理。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("设置")
            .task {
                await loadRuns()
            }
        }
    }

    @MainActor
    private func testConnection() async {
        isTesting = true
        testMessage = "正在测试 \(settings.normalizedBaseURL) ..."
        do {
            _ = try await APIClient(settings: settings).fetchEvents(decision: .keep, limit: 1)
            testMessage = "连接成功。"
        } catch {
            testMessage = error.localizedDescription
        }
        isTesting = false
    }

    @MainActor
    private func loadRuns() async {
        guard settings.isConfigured else { return }
        isLoadingRuns = true
        runMessage = nil
        do {
            runs = try await APIClient(settings: settings).fetchRuns(limit: 5).items
        } catch {
            runMessage = error.localizedDescription
        }
        isLoadingRuns = false
    }

    @MainActor
    private func triggerRun() async {
        guard settings.isConfigured else { return }
        isTriggeringRun = true
        runMessage = nil
        do {
            let result = try await APIClient(settings: settings).triggerRun(fixture: false, notify: false)
            runMessage = "运行 \(result.status)：新增 \(result.newEvents) 条，抽取 \(result.totalExtractedEvents) 条。"
            await loadRuns()
        } catch {
            runMessage = error.localizedDescription
        }
        isTriggeringRun = false
    }
}

private struct RunRow: View {
    let run: RunItem

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(run.status)
                    .font(.subheadline.bold())
                    .foregroundStyle(statusColor)
                Spacer()
                Text("#\(run.id)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text("\(run.trigger) · \(run.startedAt)")
                .font(.caption)
                .foregroundStyle(.secondary)

            Text("抽取 \(run.totalExtractedEvents) · 新增 \(run.newEvents) · 通知 \(run.notifiedEvents)")
                .font(.caption)
                .foregroundStyle(.secondary)

            if let error = run.errorSummary, !error.isEmpty {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }

    private var statusColor: Color {
        switch run.status {
        case "success":
            return .green
        case "partial_success", "skipped":
            return .orange
        case "failed":
            return .red
        default:
            return .secondary
        }
    }
}
