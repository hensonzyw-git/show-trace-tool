import Foundation
import Security
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
        didSet { KeychainStore.set(apiToken, account: Keys.apiToken) }
    }

    @Published var themeMode: ThemeMode {
        didSet { UserDefaults.standard.set(themeMode.rawValue, forKey: Keys.themeMode) }
    }

    init() {
        let savedBaseURL = UserDefaults.standard.string(forKey: Keys.baseURL)?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        self.baseURL = savedBaseURL?.isEmpty == false ? savedBaseURL! : Self.productionBaseURL
        if let keychainToken = KeychainStore.get(account: Keys.apiToken) {
            self.apiToken = keychainToken
        } else {
            let legacyToken = UserDefaults.standard.string(forKey: Keys.apiToken) ?? ""
            self.apiToken = legacyToken
            if !legacyToken.isEmpty {
                KeychainStore.set(legacyToken, account: Keys.apiToken)
                UserDefaults.standard.removeObject(forKey: Keys.apiToken)
            }
        }
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

private enum KeychainStore {
    private static let service = "showTrace"

    static func get(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    static func set(_ value: String, account: String) {
        if value.isEmpty {
            delete(account: account)
            return
        }
        let data = Data(value.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let attributes: [String: Any] = [kSecValueData as String: data]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var item = query
            item[kSecValueData as String] = data
            SecItemAdd(item as CFDictionary, nil)
        }
    }

    private static func delete(account: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
    }
}
