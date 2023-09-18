const { createApp, ref, reactive } = Vue

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
              label: "Name",
              field: "device_name",
              sortable: true,
              name: "device_name",
          },
          {
              label: "UUID",
              field: "uuid",
              sortable: true,
              name: "uuid",
          },
          {
              label: "VPN connected",
              field: "is_connected_to_vpn",
              sortable: true,
              name: "is_connected_to_vpn",
          },
          {
              label: "API heartbeat",
              field: "api_heartbeat_state",
              sortable: true,
              name: "api_heartbeat_state",
          },
          { name: 'action', label: 'Actions', name: "action", field: 'action' },
        ],
        handleClick: function(uuid){
          window.location.href = `/dashboard/devices/${uuid}`
        },
        initialPagination: {
          rowsPerPage: 0,
        },
      }
}}).use(Quasar).mount('#app')
