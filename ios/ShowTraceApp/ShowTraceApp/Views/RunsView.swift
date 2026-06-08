import SwiftUI

struct RunsView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var runs: [RunItem] = []
    @State private var isLoadingRuns = false
    @State private var isTriggeringRun = false
    @State private var runMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                statStrip
                    .padding(.top, 8)

                Text("运行历史")
                    .font(.system(size: 19, weight: .bold))
                    .padding(.horizontal, 20)
                    .padding(.top, 20)
                    .padding(.bottom, 9)

                if runs.isEmpty {
                    RunsEmptyState(title: "暂无运行记录")
                        .padding(.horizontal, 20)
                } else {
                    LazyVStack(spacing: 11) {
                        ForEach(runs) { run in
                            RunRow(run: run)
                        }
                    }
                    .padding(.horizontal, 20)
                }

                if let runMessage {
                    Text(runMessage)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 20)
                        .padding(.top, 12)
                }
            }
            .padding(.bottom, 30)
        }
        .background(Color.showRadarScreenBackground)
        .navigationTitle("采集记录")
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button {
                    Task { await loadRuns() }
                } label: {
                    if isLoadingRuns {
                        ProgressView()
                    } else {
                        Image(systemName: "arrow.clockwise")
                    }
                }
                .disabled(isLoadingRuns || !settings.isConfigured)

                Button {
                    Task { await triggerRun() }
                } label: {
                    if isTriggeringRun {
                        ProgressView()
                    } else {
                        Image(systemName: "play.fill")
                    }
                }
                .disabled(isTriggeringRun || !settings.isConfigured)
            }
        }
        .task {
            await loadRuns()
        }
    }

    private var statStrip: some View {
        HStack(spacing: 11) {
            RunStatTile(title: "今日新增", value: "\(todayNewEvents)", tint: .showRadarAccent)
            RunStatTile(title: "近7天采集", value: "\(weeklyExtractedEvents)", tint: .secondary)
            RunStatTile(title: "近7天通知", value: "\(weeklyNotifiedEvents)", tint: .green)
        }
        .padding(.horizontal, 20)
    }

    @MainActor
    private func loadRuns() async {
        guard settings.isConfigured else { return }
        isLoadingRuns = true
        runMessage = nil
        do {
            runs = try await APIClient(settings: settings).fetchRuns(limit: 20).items
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
            if result.status == "running" {
                runMessage = "已开始采集，稍后刷新记录查看结果。"
            } else {
                runMessage = "运行 \(result.status)：新增 \(result.newEvents) 条，抽取 \(result.totalExtractedEvents) 条。"
            }
            await loadRuns()
        } catch {
            runMessage = error.localizedDescription
        }
        isTriggeringRun = false
    }

    // NOTE: run.startedAt is the server's local wall-clock time, compared against
    // the device's local date. "today" / "近7天" are only accurate when the device
    // and server share a timezone. Fine for a single CN user; revisit if the API
    // ever returns timezone-aware timestamps.
    private var todayNewEvents: Int {
        runs
            .filter { $0.startedAt.hasPrefix(todayPrefix) }
            .reduce(0) { $0 + $1.newEvents }
    }

    private var recentRuns: [RunItem] {
        runs.filter { String($0.startedAt.prefix(10)) >= sevenDaysAgoPrefix }
    }

    private var weeklyExtractedEvents: Int {
        recentRuns.reduce(0) { $0 + $1.totalExtractedEvents }
    }

    private var weeklyNotifiedEvents: Int {
        recentRuns.reduce(0) { $0 + $1.notifiedEvents }
    }

    private var todayPrefix: String {
        dateString(daysAgo: 0)
    }

    private var sevenDaysAgoPrefix: String {
        dateString(daysAgo: 6)
    }

    private func dateString(daysAgo: Int) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let date = Calendar.current.date(byAdding: .day, value: -daysAgo, to: Date()) ?? Date()
        return formatter.string(from: date)
    }
}

private struct RunsEmptyState: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.system(size: 13))
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(14)
            .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
    }
}

private struct RunStatTile: View {
    let title: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            Text(value)
                .font(.system(size: 22, weight: .heavy))
                .foregroundStyle(tint)
                .monospacedDigit()
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 14))
    }
}

private struct RunRow: View {
    let run: RunItem

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                HStack(spacing: 7) {
                    Circle()
                        .fill(RunStatus.color(run.status))
                        .frame(width: 8, height: 8)
                    Text(run.startedAt)
                        .font(.system(size: 14, weight: .semibold))
                }
                Spacer()
                Text(run.trigger.uppercased())
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 10) {
                RunMetric(title: "抓取", value: run.totalRawCaptures)
                RunMetric(title: "抽取", value: run.totalExtractedEvents)
                RunMetric(title: "新增", value: run.newEvents, tint: run.newEvents > 0 ? .showRadarAccent : .secondary)
                RunMetric(title: "通知", value: run.notifiedEvents)
            }

            if let error = run.errorSummary, !error.isEmpty {
                Text(error)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(.red)
                    .lineLimit(3)
                    .padding(9)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.red.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
            }
        }
        .padding(14)
        .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.primary.opacity(0.06), lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.05), radius: 16, x: 0, y: 8)
    }
}

private struct RunMetric: View {
    let title: String
    let value: Int
    var tint: Color = .secondary

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text("\(value)")
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(tint)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
