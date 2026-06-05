import Foundation

struct EventsResponse: Decodable {
    let items: [ShowEvent]
    let total: Int
    let limit: Int
    let offset: Int
}

struct ShowEvent: Decodable, Identifiable {
    let id: String
    let type: String?
    let title: String
    let artist: String?
    let city: String?
    let venue: String?
    let eventDate: String?
    let onSaleTime: String?
    let priceInfo: String?
    let purchaseURL: String?
    let source: String?
    let sourceURL: String?
    let rawRef: String?
    let discoveredVia: String?
    let status: String?
    let interestDecision: String?
    let interestMatchScore: Int?
    let interestCategory: String?
    let interestReason: String?
    let interestUncertainty: String?

    enum CodingKeys: String, CodingKey {
        case id
        case type
        case title
        case artist
        case city
        case venue
        case eventDate = "event_date"
        case onSaleTime = "on_sale_time"
        case priceInfo = "price_info"
        case purchaseURL = "purchase_url"
        case source
        case sourceURL = "source_url"
        case rawRef = "raw_ref"
        case discoveredVia = "discovered_via"
        case status
        case interestDecision = "interest_decision"
        case interestMatchScore = "interest_match_score"
        case interestCategory = "interest_category"
        case interestReason = "interest_reason"
        case interestUncertainty = "interest_uncertainty"
    }
}

struct DigestResponse: Decodable {
    let date: String
    let markdown: String
    let path: String
    let eventCount: Int?

    enum CodingKeys: String, CodingKey {
        case date
        case markdown
        case path
        case eventCount = "event_count"
    }
}

struct Subscription: Codable {
    var artists: [String]
    var local: LocalSubscription
    var sources: [String: SourceSubscription]
}

struct LocalSubscription: Codable {
    var city: String?
    var keywords: [String]
}

struct SourceSubscription: Codable {
    var enabled: Bool?
}

struct PreferenceProfile: Decodable {
    var city: String?
    var includeCategories: [String]
    var excludeCategories: [String]
    var rankingPreferences: [String]
    var positiveSignals: [String]
    var negativeSignals: [String]

    enum CodingKeys: String, CodingKey {
        case city
        case includeCategories = "include_categories"
        case excludeCategories = "exclude_categories"
        case rankingPreferences = "ranking_preferences"
        case positiveSignals = "positive_signals"
        case negativeSignals = "negative_signals"
    }
}

struct PreferenceFeedbackRequest: Encodable {
    let feedback: String
    let eventId: String?
    let rescoreExisting: Bool
    let rescoreLimit: Int

    enum CodingKeys: String, CodingKey {
        case feedback
        case eventId = "event_id"
        case rescoreExisting = "rescore_existing"
        case rescoreLimit = "rescore_limit"
    }
}

struct PreferenceFeedbackResponse: Decodable {
    let profile: PreferenceProfile?
    let eventId: String?
    let rescoredEvents: Int?

    enum CodingKeys: String, CodingKey {
        case profile
        case eventId = "event_id"
        case rescoredEvents = "rescored_events"
    }
}

struct RunsResponse: Decodable {
    let items: [RunItem]
    let limit: Int
    let offset: Int
}

struct RunItem: Decodable, Identifiable {
    let id: Int
    let trigger: String
    let fixture: Bool
    let notify: Bool
    let startedAt: String
    let finishedAt: String?
    let status: String
    let totalRawCaptures: Int
    let totalExtractedEvents: Int
    let newEvents: Int
    let notifiedEvents: Int
    let errorSummary: String?

    enum CodingKeys: String, CodingKey {
        case id
        case trigger
        case fixture
        case notify
        case startedAt = "started_at"
        case finishedAt = "finished_at"
        case status
        case totalRawCaptures = "total_raw_captures"
        case totalExtractedEvents = "total_extracted_events"
        case newEvents = "new_events"
        case notifiedEvents = "notified_events"
        case errorSummary = "error_summary"
    }
}

struct RunRequestPayload: Encodable {
    let fixture: Bool
    let notify: Bool
}

struct RunResult: Decodable {
    let runId: Int?
    let status: String
    let totalRawCaptures: Int
    let totalExtractedEvents: Int
    let newEvents: Int
    let notifiedEvents: Int
    let errors: [String]

    enum CodingKeys: String, CodingKey {
        case runId = "run_id"
        case status
        case totalRawCaptures = "total_raw_captures"
        case totalExtractedEvents = "total_extracted_events"
        case newEvents = "new_events"
        case notifiedEvents = "notified_events"
        case errors
    }
}

enum InterestSegment: String, CaseIterable, Identifiable {
    case keep
    case maybe
    case filter

    var id: String { rawValue }

    var title: String {
        switch self {
        case .keep:
            return "推荐"
        case .maybe:
            return "待观察"
        case .filter:
            return "已过滤"
        }
    }
}
