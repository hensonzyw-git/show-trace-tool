import SwiftUI
#if os(iOS)
import UIKit
#endif

struct ContentView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var selectedTab: AppTab = .today

    var body: some View {
        TabView(selection: $selectedTab) {
            TodayView()
                .tabItem {
                    Label("当日摘要", systemImage: "calendar.badge.clock")
                }
                .tag(AppTab.today)

            EventsView()
                .tabItem {
                    Label("全部演出", systemImage: "list.bullet")
                }
                .tag(AppTab.events)

            PreferencesView()
                .tabItem {
                    Label("偏好管理", systemImage: "slider.horizontal.3")
                }
                .tag(AppTab.preferences)

            SettingsView()
                .tabItem {
                    Label("设置", systemImage: "gearshape")
                }
                .tag(AppTab.settings)
        }
        .preferredColorScheme(settings.themeMode.colorScheme)
        .dismissKeyboardOnBackgroundInteraction()
        .onAppear {
            if !settings.isConfigured {
                selectedTab = .settings
            }
        }
    }
}

private enum AppTab {
    case today
    case events
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
