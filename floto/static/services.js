const { createApp, ref, reactive } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const services = reactive({"value": []})
    let services_loading = ref("primary")
    let services_form_disabled = ref(false)
    let services_loading_error_message = ref(undefined)
    let form_data = ref({
      "is_public": false, 
      container_ref: "",
      created_by_project: get_active_project(),
      peripheral_schemas: [],
      resources: [],
      ports: [],
    })

    fetch_with_retry(`/api/services/`, callback=function(json){
      services.value = json
      services_loading.value = false
      services.value.forEach(process_created_by)
    }, error_callback=function(res){
      services_loading_error_message = "Could not get services"
    })

    let peripheral_schemas = ref([])
    fetch_with_retry(`/api/peripheral_schema/`, callback=function(json){
      peripheral_schemas.value = json
    })

    let resources = ref([])
    fetch_with_retry(`/api/resources/`, callback=function(json){
      resources.value = json
    })

    let new_port_data = ref({
      node_port: "",
      target_port: "",
      protocol: "TCP",
    })
    let add_port = function(){
      if(new_port_data.value.target_port.length > 0 
        && new_port_data.value.node_port .length > 0
        && new_port_data.value.protocol.length > 0
      ){
        form_data.value.ports.push({
          "protocol": new_port_data.value.protocol,
          "target_port": new_port_data.value.target_port,
          "node_port": new_port_data.value.node_port,
        })
        new_port_data.value.target_port = ""
        new_port_data.value.node_port = ""
      }
    }
    return {
      services, services_loading, services_form_disabled, services_loading_error_message,
      peripheral_schemas, new_port_data, resources,
      form_data,
      protocol_options: ['TCP', 'UDP'],
      add_port,
      async submit(e) {
        // We call add_port() to check if someone has a completed entry that
        // might've been missed (easy mistake).
        add_port()
        services_form_disabled = true
        services_loading = true
        const request = new Request(
          url=`/api/services/`,
          {
            method: 'POST',
            mode: 'same-origin',
            body: JSON.stringify({
              "is_public": form_data.value.is_public,
              "container_ref": form_data.value.container_ref,
              "created_by_project": form_data.value.created_by_project,
              "peripheral_schemas": form_data.value.peripheral_schemas.map(ps => {
                return {
                  "peripheral_schema": ps
                }
              }),
              "resources": form_data.value.resources.map(r => {
                return {
                  "resource": r
                }
              }),
              "ports": form_data.value.ports,
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
          services.value.push(res)
          notify(`Created service ${res.container_ref}.`)
        }).catch((response) => {
          notify(`Could not create service.`, type="negative")
          console.error(response)
        }).finally(() => {
          services_form_disabled = false
          services_loading = false
        })
      },
      delete_item(index){
        fetch(`/api/services/${this.services.value[index].uuid}`, {
          method: "DELETE",
          headers: get_headers(),
        }).then((response) => {
          if (response.ok) {
            this.services.value.splice(index, 1);
            notify("Deleted service.")
          } else {
            return Promise.reject(response);
          }
        }).catch((res) => {
          notify(`Could not delete service: ${res.detail}`, type="negative")
        })
      },
      rules: [
        value => {
          if (value) return true
          return 'Value cannot be empty.'
        },
      ],
      headers: [
        { label: "UUID", field: "uuid", name: "uuid", sortable: true, align: "left" },
        { label: "Container Ref", field: "container_ref", name: "container_ref", sortable: true, align: "left" },
        { label: "Created By", field: "created_by", name: "created_by", sortable: true, align: "left" },
        { label: "Project", field: "created_by_project", name: "created_by_project", sortable: true, align: "left" },
        { label: "Created At", field: "created_at", name: "created_at", sortable: true, align: "left" },
        { label: "Public?", field: "is_public", name: "is_public", sortable: true, align: "left" },
        { label: "Peripherals", field: "peripheral_schemas", name: "peripheralschemas", sortable: true, align: "left" },
        { label: "Resources", field: "resources", name: "resources", sortable: true, align: "left" },
        { label: "Ports", field: "ports", name: "ports", sortable: true, align: "left" },
        { name: 'action', label: 'Action', field: 'action' },
      ],
      initialPagination: {
        rowsPerPage: 0,
      }
    }
}}).use(Quasar).mount('#app')
