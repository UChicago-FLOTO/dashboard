const { createApp, ref, reactive } = Vue
const { createVuetify } = Vuetify

const vuetify = createVuetify()

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const services = reactive({"value": []})
    let services_loading = ref("primary")
    let services_form_disabled = ref(false)
    let services_loading_error_message = ref(undefined)
    let form_data = reactive({"is_public": false, container_ref: ""})

    fetch_with_retry(`/api/services/`, callback=function(json){
      services.value = json
      services_loading.value = false

      services.value.forEach((service) => {
        service.is_owned_by_current_user = service.created_by == get_user_email()
      })
    }, error_callback=function(res){
      services_loading_error_message = "Could not get services"
    })
    return {
      services, services_loading, services_form_disabled, services_loading_error_message,
      form_data,
      async submit(e) {
        e.preventDefault()
        services_form_disabled = true
        services_loading = true
        res = await e
        if(res.valid){
          const request = new Request(
            url=`/api/services/`,
            {
              method: 'POST',
              mode: 'same-origin',
              body: JSON.stringify(form_data),
              headers: get_headers(),
            }
          );
          fetch(request).then((res) => {
            if (res.ok) {
              return res.json()
            }
            return Promise.reject(res);  
          }).then( res => {
            services.value.push(res)
          }).catch((response) => {
            services_loading_error_message = "Could not create service"
          }).finally(() => {
            services_form_disabled = false
            services_loading = false
          })
        }
      },
      delete_item(index){
        fetch(`/api/services/${this.services.value[index].uuid}`, {
          method: "DELETE",
          headers: get_headers(),
        }).then((response) => {
          if (response.ok) {
            this.services.value.splice(index, 1);
          } else {
            return Promise.reject(response);
          }
        }).catch((res) => {
          alert(`Could not delete service: ${res.detail}`)
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
        { label: "Image", field: "container_ref", name: "container_ref", sortable: true, align: "left" },
        { label: "Created By", field: "created_by", name: "created_by", sortable: true, align: "left" },
        { label: "Created At", field: "created_at", name: "created_at", sortable: true, align: "left" },
        { label: "Public?", field: "is_public", name: "is_public", sortable: true, align: "left" },
        { name: 'action', label: 'Action', field: 'action' },
      ],
      initialPagination: {
        rowsPerPage: 0,
      }
    }
}}).use(vuetify).use(Quasar).mount('#app')
