const { createApp, ref, watch, onMounted, watchEffect } = Vue

createApp({
    delimiters: ["[[", "]]"],
    setup() {
        const devices = ref([])
        const stats = ref({
            "online": 0,
            "offline": 0,
            "ready": 0,
            "app_access": 0,
            "retired": 0,
        })
        fetch_with_retry("/api/devices", callback=function(json){
            devices.value = json
            stats.value.online = devices.value.filter(d => {
                return d.api_heartbeat_state == "online" } ).length
            stats.value.retired = devices.value.filter(d => {
                return d.status == "retired" } ).length        
            stats.value.offline = devices.value.length - stats.value.online - stats.value.retired
            stats.value.ready = devices.value.filter(d => {
                return d.is_ready } ).length
            stats.value.app_access = devices.value.filter(d => {
                return d.application_access } ).length            
        }, query_params="")
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
                        let iconColor = device.is_online ? 'green' : 'red'
                        let iconExtraHtml = ''
                        if (device.status == 'retired') {
                            iconColor = 'black'
                            iconExtraHtml = '<p>This device is retired, and no longer can be used.</p>'
                        }
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
                            `<b>${device.device_name}</b>${iconExtraHtml}`
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
        return {
            devices, stats
        }
    }
}).use(Quasar).mount('#app');
