const { createApp, ref, reactive, watch } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
      const devices = reactive({"value": []})
      const fleets = reactive({"value": []})
      const selected_fleets = reactive({"value": []})
      let devices_loading = ref("primary")
      let fleets_loading = ref("primary")
      let selected_devices = ref([])
      let create_collection_dialog = ref(false)
      let collection_form_data = ref({
        "is_public": false, name: "", description: "",
        created_by_project: get_active_project(),
      })
      let collections = ref([])
      let table_filter_options = [
        { name: "My Collections", value: (val) => { return val.is_owned_by_current_user } },
        { name: "Public Collections", value: (val) => { return val.is_public } },
      ]  
      filter_application_access = ref(true)
      filter_is_ready = ref(true)
      filter_management_access = ref(false)

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

      fetch_with_retry(`/api/collections/`, callback=function(json){
        collections.value = json
        collections.value.forEach(process_created_by)
      })

      return {
        devices, selected_devices, device_overview_dialog: ref(false),
        device_overview: ref(null),
        fleets, selected_fleets, devices_loading, fleets_loading,
        collections, create_collection_dialog, collection_form_data,
        filter_management_access, filter_application_access, filter_is_ready,
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
              label: "Management Access",
              field: "management_access",
              sortable: true,
              name: "management_access",
          },
          {
            label: "Application Access",
            field: "application_access",
            sortable: true,
            name: "application_access",
          },
          {
              label: "Is Online",
              field: "api_heartbeat_state",
              sortable: true,
              name: "api_heartbeat_state",
          },
          {
            label: "Ready for Apps",
            field: "is_ready",
            sortable: true,
            name: "is_ready",
          },
          { name: 'action', label: 'Actions', name: "action", field: 'action' },
        ],
        handleClick: function(uuid){
          window.location.href = `/dashboard/devices/${uuid}`
        },
        initialPagination: {
          rowsPerPage: 0,
        },
        device_rows(){
          return devices.value.filter((d) => {
            // if a filter is set, ensure device has that filter
            return (!filter_is_ready.value || d.is_ready) &&
            (!filter_application_access.value || d.application_access) &&
            (!filter_management_access.value || d.management_access)
          })
        },
        is_device_manager: function(){
          return devices.value.some(dev => dev.management_access)
        },
        async submit(e) {
          const request = new Request(
            url=`/api/collections/`,
            {
              method: 'POST',
              mode: 'same-origin',
              body: JSON.stringify({
                "is_public": collection_form_data.value.is_public,
                "name": collection_form_data.value.name,
                "description": collection_form_data.value.description,
                "devices": selected_devices.value.map((device) => {
                  return {"device_uuid": device.uuid}
                }),
                created_by_project: get_active_project(),
              }),
              headers: get_headers(),
            }
          );
          fetch(request).then((res) => {
            if (res.ok) {
              return res.json()
            }
            return Promise.reject(res);  
          }).then( res => {
            process_created_by(res)
            notify(`Created collection ${res.name}`)
          }).catch((response) => {
            notify("Could not create collection!", type="negative")
            console.error(response)
          }).finally(() => {
            create_collection_dialog = false
            // jobs_form_disabled = false
            // jobs_loading = false
          })
        },
        options: [
          { label: 'Management Access', value: 'management_access' },
          { label: 'Application Access', value: 'application_access', },
          { label: 'Ready', value: 'is_ready' }
        ],  
        table_filter_options,
        selected_table_filter: ref(table_filter_options[0]),  
        collections_headers: [
          {
            label: "UUID",
            field: "uuid",
            sortable: true,
            name: "uuid",
          },
          {
              label: "Name",
              field: "name",
              sortable: true,
              name: "name",
          },
          {
            label: "Description",
            field: "description",
            sortable: true,
            name: "description",
          },
          { name: 'action', label: 'Action', field: 'action' },
        ],
        delete_item(index){
          fetch(`/api/collections/${collections.value[index].uuid}`, {
            method: "DELETE",
            headers: get_headers(),
          }).then((response) => {
            if (response.ok) {
              collections.value.splice(index, 1);
            } else {
              return Promise.reject(response);
            }
            notify("Deleted collection.")
          }).catch((res) => {
            notify(`Could not delete collections: ${res.detail}`, type="negative")
          })
        },
      }
}}).use(Quasar).mount('#app')
