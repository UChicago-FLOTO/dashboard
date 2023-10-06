const { createApp, ref, reactive, watch } = Vue

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
        const route_params = new URLSearchParams(window.location.search);
        if (route_params.get("selected_fleets")){
          selected_fleets.value = route_params.get(
            "selected_fleets").split(",").map((i) => parseInt(i, 10))
        } else {
          selected_fleets.value = fleets.value.filter(
            f => f.app_name == FLOTO_CONFIG.default_fleet).map(x => x.id)
        }
        watch(selected_fleets, async function(old_selected, new_selected){
          console.log(selected_fleets.value)
          route_params.set("selected_fleets", selected_fleets.value)
          // window.location.search = route_params
          window.history.replaceState(null, null, `?${route_params}`)
        })
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
