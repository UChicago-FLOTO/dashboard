const { createApp, ref, reactive } = Vue
const { createVuetify } = Vuetify

const vuetify = createVuetify()

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const applications = reactive({"value": []})
    let applications_loading = ref("primary")
    let applications_form_disabled = ref(false)
    let applications_loading_error_message = ref(undefined)
    let form_data = reactive({})

    fetch_with_retry(`/api/applications/`, callback=function(json){
      console.log(json)
      services.value = json
      services_loading.value = false
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
          const token = get_token()
          const headers = new Headers();
          headers.append("Authorization", `Token ${token}`);  
          headers.append("Content-Type", "application/json")
          const request = new Request(
            url=`/api/services/`,
            {
              method: 'POST',
              mode: 'same-origin',
              body: JSON.stringify(form_data),
              headers: headers,
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
            console.log(response)
            services_loading_error_message = "Could not create service"
          }).finally(() => {
            services_form_disabled = false
            services_loading = false
          })
        }
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
      ],
      initialPagination: {
        rowsPerPage: 0,
      }
    }
}}).use(vuetify).use(Quasar).mount('#app')
