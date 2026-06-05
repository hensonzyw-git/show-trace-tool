import Foundation

enum APIError: LocalizedError {
    case missingBaseURL
    case invalidURL
    case badStatus(Int, String)
    case emptyResponse

    var errorDescription: String? {
        switch self {
        case .missingBaseURL:
            return "请先在设置里填写 API 地址。"
        case .invalidURL:
            return "API 地址格式不正确。"
        case .badStatus(let code, let body):
            return "请求失败 (\(code))：\(body)"
        case .emptyResponse:
            return "服务器没有返回内容。"
        }
    }
}

struct APIClient {
    let baseURL: String
    let token: String
    private let session: URLSession

    init(settings: AppSettings, session: URLSession = .shared) {
        self.baseURL = settings.normalizedBaseURL
        self.token = settings.apiToken.trimmingCharacters(in: .whitespacesAndNewlines)
        self.session = session
    }

    func fetchEvents(decision: InterestSegment, limit: Int = 50) async throws -> EventsResponse {
        try await get(
            "/api/events",
            queryItems: [
                URLQueryItem(name: "interest_decision", value: decision.rawValue),
                URLQueryItem(name: "limit", value: String(limit))
            ]
        )
    }

    func fetchDigest() async throws -> DigestResponse {
        try await get("/api/digests/today")
    }

    func fetchSubscription() async throws -> Subscription {
        try await get("/api/subscriptions")
    }

    func saveSubscription(_ subscription: Subscription) async throws -> Subscription {
        try await send("/api/subscriptions", method: "PUT", body: subscription)
    }

    func fetchPreferences() async throws -> PreferenceProfile {
        try await get("/api/preferences")
    }

    func sendFeedback(_ request: PreferenceFeedbackRequest) async throws -> PreferenceFeedbackResponse {
        try await send("/api/preferences/feedback", method: "POST", body: request)
    }

    func fetchRuns(limit: Int = 5) async throws -> RunsResponse {
        try await get(
            "/api/runs",
            queryItems: [URLQueryItem(name: "limit", value: String(limit))]
        )
    }

    func triggerRun(fixture: Bool = false, notify: Bool = false) async throws -> RunResult {
        try await send(
            "/api/runs",
            method: "POST",
            body: RunRequestPayload(fixture: fixture, notify: notify)
        )
    }

    private func get<T: Decodable>(_ path: String, queryItems: [URLQueryItem] = []) async throws -> T {
        var request = try makeRequest(path: path, queryItems: queryItems)
        request.httpMethod = "GET"
        return try await perform(request)
    }

    private func send<Body: Encodable, Response: Decodable>(
        _ path: String,
        method: String,
        body: Body
    ) async throws -> Response {
        var request = try makeRequest(path: path)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await perform(request)
    }

    private func makeRequest(path: String, queryItems: [URLQueryItem] = []) throws -> URLRequest {
        guard !baseURL.isEmpty else { throw APIError.missingBaseURL }
        guard var components = URLComponents(string: baseURL + path) else { throw APIError.invalidURL }
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        guard let url = components.url else { throw APIError.invalidURL }

        var request = URLRequest(url: url)
        request.timeoutInterval = 15
        if !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.emptyResponse }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.badStatus(http.statusCode, body)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
}
