const { createApp, ref, reactive, computed } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const state = reactive({
      device: {},
      logs: [],
      environment: [],
      events: [],
      device_loading: true,
      logs_loading: true,
      environment_loading: true,
      events_loading: true,
    })
    // const device = reactive({"value": {}})
    // const logs = reactive({"value": []})
    // const logs = reactive({"value": []})
    const command_text = reactive({"value": ""})
    // const environment = reactive({"value": []})
    // let device_loading = ref("primary")
    // let logs_loading = ref("primary")

    let tab = ref("overview_tab")
    let command_disabled = ref(false)
    let stdout = ref("")
    let stderr = ref("")

    let uuid = window.location.pathname.split("/")[3]
    fetch_with_retry(`/api/devices/${uuid}`, callback=function(json){
      state.device = json
      state.device.memory_percentage = (state.device["memory_usage"] / state.device["memory_total"]).toFixed(2)
      state.device.storage_percentage = (state.device["storage_usage"] / state.device["storage_total"]).toFixed(2)
      state.device.cpu_temp_percentage = (state.device["cpu_temp"] / 100.0)
      state.device.cpu_usage_percentage = (state.device["cpu_usage"] / 100.0)
      state.device_loading = false

      fetch_with_retry(`/api/devices/${state.device.uuid}/logs/1000`, callback=function(json){
        state.logs = json
        state.logs_loading = false
      })
      fetch_with_retry(`/api/devices/${uuid}/environment`, callback=function(json){
        state.environment = json
        state.environment_loading = false
      })
      fetch_with_retry(`/api/devices/${uuid}/events`, callback=function(json){
        state.events = json
        state.events.sort((a, b) => {
          let val = 0
          if (a.event_time && b.event_time) {
            val = new Date(b.event_time) - new Date(a.event_time)
          } else {
            val = new Date(b.created_at) - new Date(a.created_at)
          }
          // reverse sort
          return val
        })
        state.events = state.events.slice(0, 100)
        state.events_loading = false
      })
    })

    let peripheral_schemas = ref([])
    fetch_with_retry(`/api/peripheral_schema/`, callback=function(json){
      peripheral_schemas.value = json
    })
    let peripherals = ref([])
    fetch_with_retry(`/api/peripheral/`, callback=function(json){
      peripherals.value = json
    })      
    let peripheral_form_data = ref({
      config_items: {},
    })


    return {
      state,
      command_text, command_disabled, stdout, stderr,
      tab, add_peripheral_dialog: ref(false),
      peripheral_schemas, peripherals, peripheral_form_data,
      required_config_items: computed(() => {
        if(peripheral_form_data.value.peripheral_schema){
          return peripheral_form_data.value.peripheral_schema.configuration_items
        } else if (peripheral_form_data.value.peripheral) {
          return peripheral_form_data.value.peripheral.schema.configuration_items
        } else {
          return null
        }
      }),
      add_peripheral: function(e){
        let uuid = window.location.pathname.split("/")[3]
        let body = {}
        if (peripheral_form_data.value.peripheral_schema){
          body["peripheral"] = {}
          body["peripheral"]["name"] = peripheral_form_data.value.name
          body["peripheral"]["documentation_url"] = peripheral_form_data.value.documentation_url
          body["peripheral"]["schema"] = {
            "type": peripheral_form_data.value.peripheral_schema["type"]
          }
          console.log(peripheral_form_data.value.peripheral_schema)
        } else {
          body["peripheral_id"] = peripheral_form_data.value.peripheral["id"]
        }
        body["configuration"] = []
        Object.keys(peripheral_form_data.value.config_items).forEach(key => {
          body["configuration"].push({
            "label": key, 
            "value": peripheral_form_data.value.config_items[key],
          })
        })

        const request = new Request(
          url=`/api/devices/${uuid}/peripherals/`,
          {
            method: 'PATCH',
            mode: 'same-origin',
            body: JSON.stringify(body),
            headers: get_headers(),
          }
        );
        fetch(request).then((res) => {
          if (res.ok) { return res.json() }
          return Promise.reject(res)
        }).then( res => {
          notify(`Created peripheral ${res.peripheral.name}`)
        }).catch((response) => {
          notify("Could not create peripheral!", type="negative")
          console.error(response)
        }).finally(() => {
        })
      },
      delete_peripheral: function(id){
        let uuid = window.location.pathname.split("/")[3]
        fetch(`/api/devices/${uuid}/peripherals/${id}/`, {
          method: "DELETE",
          headers: get_headers(),
        }).then((response) => {
          if (response.ok) {
             // TODO update device object
          } else {
            return Promise.reject(response);
          }
          notify("Deleted peripheral.")
        }).catch((res) => {
          notify(`Could not delete peripheral: ${res.detail}`, type="negative")
        })
      },
      run_command: function(e){
        // Do not submit form actually
        e.preventDefault()

        const form_data = new FormData()
        form_data.append("command", command_text.value)
        const token = get_token()
        const headers = new Headers();
        headers.append("Authorization", `Token ${token}`);
        
        const request = new Request(
            url=`/api/devices/${state.device.uuid}/command/`,
            {
              method: 'POST',
              mode: 'same-origin',
              body: form_data,
              headers: headers,
            }
        );
        command_disabled.value = true
        fetch(request).then((res) => {
          if (res.ok) {
            return res.json()
          }
          return Promise.reject(res);
        }).then( res => {
          stdout.value = res.stdout
          stderr.value = res.stderr
          command_disabled.value = false
        }).catch((response) => {
          console.error(response)
          stderr.value = `Error: ${response.status} ${response.statusText}`
          command_disabled.value = false
          console.log(stderr.value)
        });
      }
    }
}}).use(Quasar).mount('#app')
