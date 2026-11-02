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
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getBridge().setRouteProcessor(new RouteProcessor() {
            @Override
            public ProcessedRoute process(String basePath, String path) {
                ProcessedRoute route = new ProcessedRoute();
                String targetPath = path;

                if (path != null) {
                    if (path.startsWith("/item/")) {
                        targetPath = "/item/_placeholder.html";
                    } else if (path.startsWith("/manifestation/")) {
                        targetPath = "/manifestation/_placeholder.html";
                    } else if (path.startsWith("/work/")) {
                        targetPath = "/work/_placeholder.html";
                    } else if (path.startsWith("/expression/")) {
                        targetPath = "/expression/_placeholder.html";
                    } else if (path.startsWith("/u/")) {
                        targetPath = "/u/_placeholder.html";
                    } else if (path.startsWith("/share/")) {
                        targetPath = "/share/_placeholder.html";
                    } else if (path.startsWith("/help/") && !path.endsWith(".html") && !path.endsWith(".js") && !path.endsWith(".css") && !path.endsWith(".png") && !path.endsWith(".svg") && !path.endsWith(".jpg")) {
                        targetPath = "/help/_placeholder.html";
                    }
                }

                route.setPath(basePath + targetPath);
                route.setAsset(true);
                return route;
            }
        });
    }
}
