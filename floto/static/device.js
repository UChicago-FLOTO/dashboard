const { createApp, ref, reactive } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const device = reactive({"value": {}})
    const logs = reactive({"value": []})
    const command_text = reactive({"value": ""})
    let device_loading = ref("primary")
    let logs_loading = ref("primary")
    let tab = ref("overview_tab")
    let command_disabled = ref(false)
    let stdout = ref("")
    let stderr = ref("")

    fetch_with_retry(`/api/devices/${window.location.pathname.split("/")[3]}`, callback=function(json){
      device.value = json
      device.value.memory_percentage = (device.value["memory_usage"] / device.value["memory_total"]).toFixed(2)
      device.value.storage_percentage = (device.value["storage_usage"] / device.value["storage_total"]).toFixed(2)
      device.value.cpu_temp_percentage = (device.value["cpu_temp"] / 100.0)
      device.value.cpu_usage_percentage = (device.value["cpu_usage"] / 100.0)
      device.value.split_mac = device.value.mac_address.split(/[ ,]+/)
      device.value.split_ip = device.value.ip_address.split(/[ ,]+/)
      device_loading.value = false

      fetch_with_retry(`/api/devices/${device.value.uuid}/logs/1000`, callback=function(json){
        logs.value = json
        logs_loading.value = false
      })
    })
    return {
      device, logs, tab, device_loading, logs_loading,
      command_text, command_disabled, stdout, stderr,
      run_command: function(e){
        // Do not submit form actually
        e.preventDefault()
        console.log("running command")

        const form_data = new FormData()
        form_data.append("command", command_text.value)
        const token = get_token()
        const headers = new Headers();
        headers.append("Authorization", `Token ${token}`);
        
        const request = new Request(
            url=`/api/devices/${device.value.uuid}/command/`,
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
