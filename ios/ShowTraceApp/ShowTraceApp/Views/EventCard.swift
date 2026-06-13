import SwiftUI

struct EventCard: View {
    let event: ShowEvent

    @State private var safariURL: IdentifiedURL?

    var body: some View {
        Button {
            if let url = purchaseURL {
                safariURL = IdentifiedURL(url: url)
            }
        } label: {
            VStack(alignment: .leading, spacing: 9) {
                header
                title
                metadataRows
                if event.interestDecision == "keep", let reason = event.interestReason, !reason.isEmpty {
                    reasonBox(reason)
                }
                footer
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .frame(maxWidth: .infinity, alignment: .leading)
            .contentShape(RoundedRectangle(cornerRadius: 18))
        }
        .buttonStyle(.plain)
        .disabled(purchaseURL == nil)
        .opacity(purchaseURL == nil ? 0.9 : 1)
        .background(Color.showRadarCardBackground, in: RoundedRectangle(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color.showRadarSeparator, lineWidth: 0.5)
        }
        .shadow(color: .black.opacity(0.05), radius: 16, x: 0, y: 8)
        #if os(iOS)
        .sheet(item: $safariURL) { item in
            SafariSheet(url: item.url)
                .ignoresSafeArea()
        }
        #endif
    }

    private var header: some View {
        HStack(alignment: .center, spacing: 10) {
            CategoryIconChip(category: category)
            VStack(alignment: .leading, spacing: 2) {
                Text(category)
                    .font(.system(size: 11.5, weight: .bold))
                    .foregroundStyle(Color.showRadarAccent)
                    .tracking(0.2)
                HStack(spacing: 6) {
                    sourceTag
                    Text("·")
                        .foregroundStyle(.tertiary)
                    Text(event.onSaleTime?.isEmpty == false ? event.onSaleTime! : "开票待定")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 8)
            ScoreBadge(score: event.interestMatchScore, decision: event.interestDecision)
        }
    }

    private var title: some View {
        Text(event.title)
            .font(.system(size: 15.5, weight: .bold))
            .tracking(-0.2)
            .foregroundStyle(.primary)
            .lineLimit(2)
            .fixedSize(horizontal: false, vertical: true)
    }

    private var metadataRows: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let date = event.eventDate, !date.isEmpty {
                Label(date, systemImage: "calendar")
                    .font(.system(size: 13))
                    .lineLimit(1)
            }

            let location = [event.city, event.venue, event.artist].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · ")
            if !location.isEmpty {
                Label(location, systemImage: "mappin.and.ellipse")
                    .font(.system(size: 13))
                    .lineLimit(1)
            }
        }
        .foregroundStyle(.secondary)
    }

    private func reasonBox(_ reason: String) -> some View {
        Label(reason, systemImage: "bolt.fill")
            .font(.system(size: 11.5))
            .foregroundStyle(.secondary)
            .lineLimit(3)
            .padding(.horizontal, 9)
            .padding(.vertical, 7)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.primary.opacity(0.025), in: RoundedRectangle(cornerRadius: 8))
    }

    private var footer: some View {
        HStack(alignment: .center) {
            Text(event.priceInfo?.isEmpty == false ? event.priceInfo! : "价格待定")
                .font(.system(size: 16, weight: .heavy))
                .tracking(-0.3)
                .foregroundStyle(.primary)
                .lineLimit(1)
            Spacer(minLength: 8)
            if purchaseURL != nil {
                Label("去\(EventSource.label(for: event.source) ?? "购票")", systemImage: "arrow.up.right.square")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Color.showRadarAccent)
                    .labelStyle(.titleAndIcon)
            }
        }
        .padding(.top, 10)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(Color.showRadarSeparator)
                .frame(height: 0.5)
        }
    }

    private var sourceTag: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(EventSource.color(for: event.source))
                .frame(width: 6, height: 6)
            Text(EventSource.label(for: event.source) ?? "未知")
                .font(.system(size: 11.5, weight: .semibold))
                .foregroundStyle(.secondary)
        }
    }

    private var purchaseURL: URL? {
        guard let purchaseURL = event.purchaseURL else { return nil }
        return URL(string: purchaseURL)
    }

    private var category: String {
        EventCategory.resolved(for: event)
    }

}

private struct IdentifiedURL: Identifiable {
    let url: URL
    var id: String { url.absoluteString }
}

private struct ScoreBadge: View {
    let score: Int?
    let decision: String?

    var body: some View {
        HStack(spacing: 4) {
            if decision == "keep" {
                Image(systemName: "star.fill")
                    .font(.system(size: 10, weight: .semibold))
            }
            Text(DecisionStyle.label(decision))
            if let score {
                Text("\(score)")
                    .opacity(0.62)
            }
        }
        .font(.system(size: 11.5, weight: .semibold))
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(DecisionStyle.background(decision), in: Capsule())
        .foregroundStyle(DecisionStyle.foreground(decision))
    }
}
