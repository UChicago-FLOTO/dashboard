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
        fetch_with_retry("/api/devices", callback = function (json) {
            devices.value = json
            stats.value.online = devices.value.filter(d => {
                return d.api_heartbeat_state == "online"
            }).length
            stats.value.retired = devices.value.filter(d => {
                return d.status == "retired"
            }).length
            stats.value.offline = devices.value.length - stats.value.online - stats.value.retired
            stats.value.ready = devices.value.filter(d => {
                return d.is_ready
            }).length
            stats.value.app_access = devices.value.filter(d => {
                return d.application_access
            }).length

            let from = Quasar.date.addToDate(new Date(), {"days": -7}).toISOString()
            let to = Quasar.date.addToDate(new Date(), {"days": 7}).toISOString()

            let div = document.querySelector("#chart")
            if(div){
                fetch_with_retry(`/api/timeslots?from=${from}&to=${to}`, callback = function (timeslot_json) {
                    create_chart(div, timeslot_json, devices.value)
                })
            }
        }, query_params = "")
        onMounted(() => {
            const tooltip = document.createElement("div")
            tooltip.style.display = "none"
            tooltip.style.position = "fixed"
            tooltip.style["z-index"] = "999"
            tooltip.style.backgroundColor = "white"
            tooltip.style.borderRadius = "3px"
            tooltip.style.border = "1px solid black"
            tooltip.style.padding = "5px"
            document.querySelector("#app").appendChild(tooltip)
            var map = L.map('map', {"maxZoom": 18}).setView([0,0], 1);
            // Initialize a feature group
            var markers = new L.MarkerClusterGroup({
                maxClusterRadius: 30,
                disableClusteringAtZoom: 13,
            })
            markers.on('clustermouseover', function (a) {
                overview = {
                    "online": 0,
                    "offline": 0,
                    "retired": 0,
                }
                a.layer.getAllChildMarkers().forEach(marker => {
                    overview[marker.options.icon.options.status] += 1
                })
                let overviewHTML = ""
                for (const status in overview) {
                    if(overview[status] != 0){
                        overviewHTML += `<div>${overview[status]} ${status}</div>`
                    }
                }
                tooltip.innerHTML = overviewHTML
                tooltip.style.display = "block"
                tooltip.style.left = `${a.originalEvent.x + 10}px`
                tooltip.style.top = `${a.originalEvent.y + 10}px`
            });
            
            markers.on('clustermouseout', function (a) {
                tooltip.style.display = "none"
            });
            
            map.addLayer(markers)
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
                        let status = device.api_heartbeat_state
                        let iconColor = device.api_heartbeat_state == "online" ? 'green' : 'red'
                        let iconExtraHtml = ''
                        if (device.status == 'retired') {
                            iconColor = 'black'
                            iconExtraHtml = '<p>This device is retired, and no longer can be used.</p>'
                            status = "retired"
                        }
                        let iconSize = device.api_heartbeat_state == "online" ? '35px' : '25px';
                        let iconName = 'place';
                        let iconHtml = `<div style="color: ${iconColor}; font-size: ${iconSize};" class="q-icon material-icons">${iconName}</div>`;
                        var customIcon = L.divIcon({
                            html: iconHtml,
                            className: 'my-custom-icon',
                            status,
                        });
                        var marker = L.marker(
                            [device.latitude, device.longitude],
                            { icon: customIcon }
                        ).bindPopup(
                            `<b>${device.device_name}</b>${iconExtraHtml}`
                        );
                        markers.addLayer(marker);
                        addedMarkers = true;
                    }
                });
                // Only adjust bounds if at least one marker was added
                if (addedMarkers) {
                    map.fitBounds(markers.getBounds(), { padding: [1, 1] });
                }
            });
        });
        return {
            devices, stats
        }
    }
}).use(Quasar).mount('#app');


function create_chart(div, timeslot_json, devices) {
    let tasks = []
    Object.keys(timeslot_json).forEach(uuid => {
        timeslot_json[uuid].forEach(ts => {
            tasks.push({
                "uuid": uuid,
                "start": ts["start"],
                "stop": ts["stop"],
                "name": devices.find(d => d.uuid == uuid).device_name
            })
        })
    })
    let devicesWithTimeslots = Object.keys(timeslot_json).length

    plot = Plot.plot({
        marks: [
            Plot.frame(),
            Plot.barX(tasks, {
                y: (d) => d.name,
                x1: (d) => d3.isoParse(d.start),
                x2: (d) => d3.isoParse(d.stop),
                fill: "green",
            }),
        ],
        height: 100 + devicesWithTimeslots * 50,
        width: 2000,
        marginLeft: 150,
        marginBottom: 80,
        x: { grid: true},
        style: "font-size: 16px;",
    })
    div.append(plot);
}