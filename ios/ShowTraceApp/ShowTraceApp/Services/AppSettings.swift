import Foundation
import SwiftUI

enum ThemeMode: String, CaseIterable, Identifiable {
    case system
    case light
    case dark

    var id: String { rawValue }

    var title: String {
        switch self {
        case .system:
            return "跟随系统"
        case .light:
            return "浅色"
        case .dark:
            return "深色"
        }
    }

    var colorScheme: ColorScheme? {
        switch self {
        case .system:
            return nil
        case .light:
            return .light
        case .dark:
            return .dark
        }
    }
}

final class AppSettings: ObservableObject {
    static let productionBaseURL = "http://8.153.84.10"

    @Published var baseURL: String {
        didSet { UserDefaults.standard.set(baseURL, forKey: Keys.baseURL) }
    }

    @Published var apiToken: String {
        didSet { UserDefaults.standard.set(apiToken, forKey: Keys.apiToken) }
    }

    @Published var themeMode: ThemeMode {
        didSet { UserDefaults.standard.set(themeMode.rawValue, forKey: Keys.themeMode) }
    }

    init() {
        let savedBaseURL = UserDefaults.standard.string(forKey: Keys.baseURL)?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        self.baseURL = savedBaseURL?.isEmpty == false ? savedBaseURL! : Self.productionBaseURL
        self.apiToken = UserDefaults.standard.string(forKey: Keys.apiToken) ?? ""
        let savedThemeMode = UserDefaults.standard.string(forKey: Keys.themeMode)
        self.themeMode = ThemeMode(rawValue: savedThemeMode ?? "") ?? .system
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
        static let themeMode = "showTrace.themeMode"
    }
}
