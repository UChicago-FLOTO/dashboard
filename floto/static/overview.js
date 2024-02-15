const { createApp, ref, reactive, watch, onMounted, watchEffect } = Vue

createApp({
    delimiters: ["[[", "]]"],
    setup() {
        const devices = reactive({"value": []})
        let devices_loading = ref("primary")
        fetch_with_retry("/api/devices", callback=function(json){
        devices.value = json
        devices_loading.value = false
        })
        onMounted(() => {
            var map = L.map('map').setView([38.178318, -101.0093573], 4);
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            // watchEffect to reactively add markers once the data is available.
            watchEffect(() => {
                devices.value.forEach(device => {
                    if (device.latitude && device.longitude && device.latitude !== 0.0 && device.longitude !== 0.0) {
                    L.marker([device.latitude, device.longitude]).addTo(map)
                        .bindPopup(`<b>${device.device_name}</b>`);
                    }
                });
            });
    });
}}).use(Quasar).mount('#app')
