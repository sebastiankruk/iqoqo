import UIKit
import Capacitor

public struct NextJSRouter: Router {
    public var basePath: String = ""

    public init() {}

    public func route(for path: String) -> String {
        if path.isEmpty || path == "/" {
            return basePath + "/index.html"
        }

        let isStaticAsset = path.hasPrefix("/_next/") ||
            path.hasSuffix(".js") ||
            path.hasSuffix(".css") ||
            path.hasSuffix(".png") ||
            path.hasSuffix(".jpg") ||
            path.hasSuffix(".jpeg") ||
            path.hasSuffix(".svg") ||
            path.hasSuffix(".ico") ||
            path.hasSuffix(".woff") ||
            path.hasSuffix(".woff2") ||
            path.hasSuffix(".json") ||
            path.hasSuffix(".map")

        if !isStaticAsset {
            let dynamicPrefixes = [
                "/item/",
                "/manifestation/",
                "/work/",
                "/expression/",
                "/u/",
                "/share/"
            ]

            for prefix in dynamicPrefixes {
                if path.hasPrefix(prefix) {
                    if path.hasSuffix(".txt") {
                        return basePath + prefix + "_placeholder.txt"
                    } else {
                        return basePath + prefix + "_placeholder.html"
                    }
                }
            }

            if path.hasPrefix("/help/") {
                let staticHelpPaths: Set<String> = [
                    "/help/camera-to-catalog.html",
                    "/help/camera-to-catalog.txt",
                    "/help/curators-handbook.html",
                    "/help/curators-handbook.txt",
                    "/help/federation-architecture.html",
                    "/help/federation-architecture.txt",
                    "/help/frbr-hierarchy.html",
                    "/help/frbr-hierarchy.txt",
                    "/help/privacy-sharing-social.html",
                    "/help/privacy-sharing-social.txt"
                ]

                if !staticHelpPaths.contains(path) {
                    if path.hasSuffix(".txt") {
                        return basePath + "/help/_placeholder.txt"
                    } else {
                        return basePath + "/help/_placeholder.html"
                    }
                }
            }

            let pathUrl = URL(fileURLWithPath: path)
            if pathUrl.pathExtension.isEmpty {
                let htmlPath = basePath + path + ".html"
                if FileManager.default.fileExists(atPath: htmlPath) {
                    return htmlPath
                }
                let nestedIndexPath = basePath + path + "/index.html"
                if FileManager.default.fileExists(atPath: nestedIndexPath) {
                    return nestedIndexPath
                }
                return basePath + "/index.html"
            }
        }

        return basePath + path
    }
}

@objc(ViewController)
class ViewController: CAPBridgeViewController {
    override func router() -> Router {
        return NextJSRouter()
    }
}

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Override point for customization after application launch.
        return true
    }

    func applicationWillResignActive(_ application: UIApplication) {
        // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
        // Use this method to pause ongoing tasks, disable timers, and invalidate graphics rendering callbacks. Games should use this method to pause the game.
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later.
        // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        // Called as part of the transition from the background to the active state; here you can undo many of the changes made on entering the background.
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        // Restart any tasks that were paused (or not yet started) while the application was inactive. If the application was previously in the background, optionally refresh the user interface.
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
    }

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        // Called when the app was launched with a url. Feel free to add additional processing here,
        // but if you want the App API to support tracking app url opens, make sure to keep this call
        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)
    }

    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        // Called when the app was launched with an activity, including Universal Links.
        // Feel free to add additional processing here, but if you want the App API to support
        // tracking app url opens, make sure to keep this call
        return ApplicationDelegateProxy.shared.application(application, continue: userActivity, restorationHandler: restorationHandler)
    }

}
