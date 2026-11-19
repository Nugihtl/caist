(function () {
    "use strict";

    var center = [-6.9175, 107.6191];
    var zoom = 11;

    var map = L.map("map").setView(center, zoom);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    var risikoLayer = L.layerGroup().addTo(map);

    window.caistMap = {
        map: map,
        risikoLayer: risikoLayer,
        setRisiko: function (fitur) {
            risikoLayer.clearLayers();
            // fitur: daftar objek {geometry, properti, risiko}
            // Implementasi rendering risiko akan ditambahkan di tahapan selanjutnya.
        },
    };
})();
