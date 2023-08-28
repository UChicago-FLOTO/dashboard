const { createApp, ref, reactive } = Vue
const { createVuetify } = Vuetify

const vuetify = createVuetify()

createApp({
  delimiters: ["[[", "]]"],
  setup() {
      const devices = reactive({"value": []})
      const fleets = reactive({"value": []})
      const selected_fleets = reactive({"value": []})
      let devices_loading = ref("primary")
      let fleets_loading = ref("primary")

      fetch_with_retry("/api/devices", callback=function(json){
        devices.value = json
        devices_loading.value = false
      })

      fetch_with_retry("/api/fleets", callback=function(json){
        fleets.value = json
        selected_fleets.value = fleets.value.filter(f => f.app_name == FLOTO_CONFIG.default_fleet).map(x => x.id)
        fleets_loading.value = false
      })

      return {
        devices, fleets, selected_fleets, devices_loading, fleets_loading,
        headers: [
          {
              title: "Name",
              key: "device_name",
              sortable: true,
          },
          {
              title: "UUID",
              key: "uuid",
              sortable: true,
          },
          {
              title: "VPN connected",
              key: "is_connected_to_vpn",
              sortable: true,
          },
          {
              title: "API heartbeat",
              key: "api_heartbeat_state",
              sortable: true,
          },
        ],
        handleClick: function(event, item){
          window.location.href = `/dashboard/devices/${item.item.raw.uuid}`
        }
      }
}}).use(vuetify).mount('#app')
