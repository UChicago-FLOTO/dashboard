const { createApp, ref, reactive, watch, onMounted, watchEffect } = Vue

createApp({
    delimiters: ["[[", "]]"],
    setup() {
        const devices = reactive({"value": []})
        fetch_with_retry("/api/devices", callback=function(json){
            devices.value = json
        })
        onMounted(() => {
            var map = L.map('map').setView([0,0], 1);
            // Initialize a feature group
            var markers = new L.featureGroup().addTo(map);
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            // Use watchEffect to reactively add markers once the data is available
            watchEffect(() => {
                // Clear existing markers to avoid duplicates
                markers.clearLayers();
                // Track if any markers are added
                let addedMarkers = false;
                devices.value.forEach(device => {
                    if (device.latitude && device.longitude) {
                        let iconColor = device.is_online ? 'green' : 'red';
                        let iconSize = device.is_online ? '35px' : '25px';
                        let iconName = 'place';
                        let iconHtml = `<div style="color: ${iconColor}; font-size: ${iconSize};" class="q-icon material-icons">${iconName}</div>`;
                        var customIcon = L.divIcon({
                            html: iconHtml,
                            className: 'my-custom-icon',
                        });
                        var marker = L.marker(
                            [device.latitude, device.longitude],
                            {icon: customIcon}
                        ).bindPopup(
                            `<b>${device.device_name}</b>`
                        );
                        markers.addLayer(marker);
                        addedMarkers = true;
                    }
                });
                // Only adjust bounds if at least one marker was added
                if (addedMarkers) {
                    map.fitBounds(markers.getBounds(), {padding: [1, 1]});
                }
            });
        });
    }
}).use(Quasar).mount('#app');
