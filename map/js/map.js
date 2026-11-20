(function () {
    "use strict";

    var statusNode = document.getElementById("map-status");
    function report(message) {
        statusNode.textContent = message;
        if (window.caistBridge) {
            window.caistBridge.reportStatus(message);
        }
    }

    if (typeof L === "undefined") {
        var leafletError = "Leaflet lokal tidak termuat. Periksa file map/vendor dan konfigurasi WebEngine.";
        report(leafletError);
        if (typeof QWebChannel !== "undefined" && window.qt && qt.webChannelTransport) {
            new QWebChannel(qt.webChannelTransport, function (channel) {
                channel.objects.caistBridge.reportStatus(leafletError);
            });
        }
        return;
    }

    var map = L.map("map").setView([-6.9175, 107.6191], 10);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    function popupContent(properties, keys) {
        var root = document.createElement("div");
        keys.forEach(function (key) {
            if (properties[key] === null || properties[key] === undefined || properties[key] === "") {
                return;
            }
            var row = document.createElement("div");
            var label = document.createElement("strong");
            label.textContent = key + ": ";
            row.appendChild(label);
            row.appendChild(document.createTextNode(String(properties[key])));
            root.appendChild(row);
        });
        return root;
    }

    var overlays = {};
    var fitLayers = [];
    function addLayer(layer, name, style, popupKeys) {
        if (!layer || layer.status !== "available" || !layer.geojson) {
            return;
        }
        var geoLayer = L.geoJSON(layer.geojson, {
            style: style,
            attribution: "&copy; OpenStreetMap contributors",
            onEachFeature: function (feature, item) {
                item.bindPopup(popupContent(feature.properties || {}, popupKeys));
            }
        });
        geoLayer.addTo(map);
        overlays[name] = geoLayer;
        fitLayers.push(geoLayer);
    }

    function fitToData() {
        if (!fitLayers.length) {
            return;
        }
        var group = L.featureGroup(fitLayers);
        if (group.getBounds().isValid()) {
            map.fitBounds(group.getBounds(), {padding: [18, 18], maxZoom: 12});
        }
    }

    function addLegend() {
        var legend = L.control({position: "bottomleft"});
        legend.onAdd = function () {
            var div = L.DomUtil.create("div", "map-legend");
            [["legend-area", "Batas kecamatan"], ["legend-line", "Jaringan sungai"]]
                .forEach(function (entry) {
                    var row = document.createElement("div");
                    var swatch = document.createElement("span");
                    swatch.className = entry[0];
                    row.appendChild(swatch);
                    row.appendChild(document.createTextNode(entry[1]));
                    div.appendChild(row);
                });
            return div;
        };
        legend.addTo(map);
    }

    function initialize(payload) {
        addLayer(payload.boundaries, "Batas administrasi", {
            color: "#475569", weight: 1, fillColor: "#bfdbfe", fillOpacity: 0.22
        }, ["district_name", "district_code", "parent_name", "parent_code", "source_name"]);
        addLayer(payload.rivers, "Jaringan sungai", {
            color: "#168aad", weight: 1.5, opacity: 0.85
        }, ["name", "waterway", "width", "@id"]);

        if (Object.keys(overlays).length) {
            L.control.layers(null, overlays, {collapsed: false}).addTo(map);
            fitToData();
        }
        addLegend();
        var b = payload.boundaries;
        var r = payload.rivers;
        var boundaryMessage = b.message ? " — " + b.message : "";
        var riverMessage = r.message ? " — " + r.message : "";
        report(
            "Batas: " + (b.count || 0) + " poligon (" + b.status + boundaryMessage + ") | " +
            "Sungai: " + (r.count || 0) + " garis (" + r.status + riverMessage + ") | " +
            payload.coverage_note + " | Basemap OpenStreetMap memerlukan internet."
        );
    }

    var FitControl = L.Control.extend({
        onAdd: function () {
            var button = L.DomUtil.create("button", "fit-map");
            button.type = "button";
            button.textContent = "Fit data";
            button.title = "Sesuaikan tampilan dengan cakupan layer";
            L.DomEvent.disableClickPropagation(button);
            L.DomEvent.on(button, "click", fitToData);
            return button;
        }
    });
    new FitControl({position: "topleft"}).addTo(map);

    if (typeof QWebChannel === "undefined" || !window.qt || !qt.webChannelTransport) {
        report("Bridge data peta desktop tidak tersedia.");
        return;
    }
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.caistBridge = channel.objects.caistBridge;
        window.caistBridge.getMapData(function (serialized) {
            try {
                initialize(JSON.parse(serialized));
            } catch (error) {
                report("Data peta gagal diproses: " + error.message);
            }
        });
    });

    window.caistMap = {map: map, fitToData: fitToData};
})();
