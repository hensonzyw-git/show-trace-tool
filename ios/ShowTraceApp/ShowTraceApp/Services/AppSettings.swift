import Foundation

final class AppSettings: ObservableObject {
    static let productionBaseURL = "http://8.153.84.10"

    @Published var baseURL: String {
        didSet { UserDefaults.standard.set(baseURL, forKey: Keys.baseURL) }
    }

    @Published var apiToken: String {
        didSet { UserDefaults.standard.set(apiToken, forKey: Keys.apiToken) }
    }

    init() {
        let savedBaseURL = UserDefaults.standard.string(forKey: Keys.baseURL)?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        self.baseURL = savedBaseURL?.isEmpty == false ? savedBaseURL! : Self.productionBaseURL
        self.apiToken = UserDefaults.standard.string(forKey: Keys.apiToken) ?? ""
    }

    var isConfigured: Bool {
        URL(string: normalizedBaseURL) != nil
    }

    var normalizedBaseURL: String {
        baseURL.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    }

    func useProductionServer() {
        baseURL = Self.productionBaseURL
    }

    private enum Keys {
        static let baseURL = "showTrace.baseURL"
        static let apiToken = "showTrace.apiToken"
    }
}
