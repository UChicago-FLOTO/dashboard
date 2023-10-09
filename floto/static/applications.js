const { createApp, ref, reactive } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const applications = reactive({"value": []})
    const services = reactive({"value": []})
    let applications_loading = ref("primary")
    let applications_form_disabled = ref(false)
    let applications_loading_error_message = ref(undefined)
    let form_data = reactive({
      name: "",
      description: "",
      environment: {},
      is_public: false,
      services: [],
    })
    let step = ref(1)

    fetch_with_retry(`/api/applications/`, callback=function(json){
      applications.value = json
      applications_loading.value = false

      applications.value.forEach(process_created_by)

      fetch_with_retry(`/api/services/`, callback=function(json){
        services.value = json
        try {
          applications.value.forEach((app) => {
            app.services.forEach((wrapper) => {
              let full_service = services.value.find((service) => {
                return wrapper.service == service.uuid
              })
              wrapper.container_ref = full_service.container_ref
            })
          })
        } catch (e){
          console.error(e)
          // TODO
        }
      }, error_callback=function(res){
        // TODO
      })
    }, error_callback=function(res){
      applications_loading_error_message = "Could not get applications"
    })

    return {
      applications, applications_loading, applications_form_disabled, applications_loading_error_message,
      services,
      form_data,
      step,
      continueFn(stepper){
        console.log(this.$refs)
        if(step.value === 1 && form_data.application){
          form_data.environment = form_data.application.parsed_env
        }
        stepper.next()
      },
      async submit(e) {
        console.log(JSON.stringify(form_data))
        applications_form_disabled = true
        applications_loading = true
        const request = new Request(
          url=`/api/applications/`,
          {
            method: 'POST',
            mode: 'same-origin',
            body: JSON.stringify({
              "name": form_data.name,
              "description": form_data.description,
              "environment": JSON.stringify(form_data.environment),
              "is_public": form_data.is_public,
              "services": form_data.services.map((uuid) => {
                return {"service": uuid}
              }),
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
          applications.value.push(res)
          notify(`Created application ${res.name}`)
        }).catch((response) => {
          notify("Could not create application!", type="negative")
          console.error(response)
        }).finally(() => {
          applications_form_disabled = false
          applications_loading = false
        })
      },
      delete_item(index){
        fetch(`/api/applications/${this.applications.value[index].uuid}`, {
          method: "DELETE",
          headers: get_headers(),
        }).then((response) => {
          if (response.ok) {
            this.applications.value.splice(index, 1);
          } else {
            return Promise.reject(response);
          }
          notify("Deleted application.")
        }).catch((res) => {
          notify(`Could not delete application: ${res.detail}`, type="negative")
        })
      },
      not_empty: [
        value => {
          if (value) return true
          return 'Value cannot be empty.'
        },
      ],
      headers: [
        { label: "Name", field: "name", name: "name", sortable: true, align: "left" },
        { label: "Created By", field: "created_by", name: "created_by", sortable: true, align: "left" },
        { label: "Created At", field: "created_at", name: "created_at", sortable: true, align: "left" },
        { label: "Public?", field: "is_public", name: "is_public", sortable: true, align: "left" },
        { label: "Description", field: "description", name: "description", sortable: true, align: "left" },
        { label: "Services", field: "services", name: "services", align: "left" },
        { label: "Environment", field: "environment", name: "environment", align: "left" },
        { name: 'action', label: 'Action', field: 'action' },
      ],
      initialPagination: {
        rowsPerPage: 0,
      }
    }
}}).use(Quasar)
.component("environment-component", EnvironmentComponent)
.mount('#app')
