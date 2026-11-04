/*
 * Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>
 */

package cc.iqoqo.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.ProcessedRoute;
import com.getcapacitor.RouteProcessor;

public class MainActivity extends BridgeActivity {
    @Override
    protected void load() {
        bridgeBuilder.setRouteProcessor(new RouteProcessor() {
            @Override
            public ProcessedRoute process(String basePath, String path) {
                ProcessedRoute route = new ProcessedRoute();
                String targetPath = path;

                if (path != null) {
                    boolean isStaticAsset = path.startsWith("/_next/") ||
                        path.endsWith(".js") ||
                        path.endsWith(".css") ||
                        path.endsWith(".png") ||
                        path.endsWith(".jpg") ||
                        path.endsWith(".jpeg") ||
                        path.endsWith(".svg") ||
                        path.endsWith(".ico") ||
                        path.endsWith(".woff") ||
                        path.endsWith(".woff2") ||
                        path.endsWith(".json") ||
                        path.endsWith(".map");

                    if (!isStaticAsset) {
                        String[] dynamicPrefixes = new String[] {
                            "/item/",
                            "/manifestation/",
                            "/work/",
                            "/expression/",
                            "/u/",
                            "/share/"
                        };

                        for (String prefix : dynamicPrefixes) {
                            if (path.startsWith(prefix)) {
                                if (path.endsWith(".txt")) {
                                    targetPath = prefix + "_placeholder.txt";
                                } else {
                                    targetPath = prefix + "_placeholder.html";
                                }
                                break;
                            }
                        }

                        if (path.startsWith("/help/")) {
                            String trimmed = path.endsWith(".html") ? path.substring(0, path.length() - 5) : path;
                            boolean isStaticHelp = trimmed.equals("/help/camera-to-catalog") ||
                                trimmed.equals("/help/curators-handbook") ||
                                trimmed.equals("/help/federation-architecture") ||
                                trimmed.equals("/help/frbr-hierarchy") ||
                                trimmed.equals("/help/privacy-sharing-social");

                            if (isStaticHelp) {
                                if (path.endsWith(".txt")) {
                                    targetPath = trimmed + ".txt";
                                } else {
                                    targetPath = trimmed + ".html";
                                }
                            } else {
                                if (path.endsWith(".txt")) {
                                    targetPath = "/help/_placeholder.txt";
                                } else {
                                    targetPath = "/help/_placeholder.html";
                                }
                            }
                        }
                    }
                }

                route.setPath(basePath + targetPath);
                route.setAsset(true);
                return route;
            }
        });
        super.load();
    }
}
