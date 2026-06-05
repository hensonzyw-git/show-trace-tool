import SwiftUI
#if os(iOS)
import UIKit
#endif

struct ContentView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var selectedTab: AppTab = .events

    var body: some View {
        TabView(selection: $selectedTab) {
            EventsView()
                .tabItem {
                    Label("推荐", systemImage: "sparkles")
                }
                .tag(AppTab.events)

            DigestView()
                .tabItem {
                    Label("摘要", systemImage: "doc.text")
                }
                .tag(AppTab.digest)

            SubscriptionView()
                .tabItem {
                    Label("订阅", systemImage: "slider.horizontal.3")
                }
                .tag(AppTab.subscription)

            PreferencesView()
                .tabItem {
                    Label("喜好", systemImage: "person.crop.circle.badge.checkmark")
                }
                .tag(AppTab.preferences)

            SettingsView()
                .tabItem {
                    Label("设置", systemImage: "gearshape")
                }
                .tag(AppTab.settings)
        }
        .dismissKeyboardOnBackgroundInteraction()
        .onAppear {
            if !settings.isConfigured {
                selectedTab = .settings
            }
        }
    }
}

private enum AppTab {
    case events
    case digest
    case subscription
    case preferences
    case settings
}

private extension View {
    func dismissKeyboardOnBackgroundInteraction() -> some View {
        #if os(iOS)
        self
            .simultaneousGesture(
                DragGesture(minimumDistance: 8).onChanged { _ in
                    UIApplication.shared.dismissKeyboard()
                }
            )
        #else
        self
        #endif
    }
}

#if os(iOS)
private extension UIApplication {
    func dismissKeyboard() {
        sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
}
#endif
