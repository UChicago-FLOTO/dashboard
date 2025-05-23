const { createApp, ref, reactive, watch } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const jobs = reactive({"value": []})
    let jobs_loading = ref("primary")
    let jobs_form_disabled = ref(false)
    let jobs_loading_error_message = ref(undefined)
    let step = ref(1)
    let table_filter_options = [
      { name: "My Jobs", value: (val) => { return val.is_owned_by_current_user } },
      { name: "Public Jobs", value: (val) => { return val.is_public } },
    ]
    let timeslot_conflicts = ref({})
    let pending_timeslots = ref({})

    const applications = reactive({
      "value": [], 
      "options": [],
      "options_filter": [],
    })

    const devices = reactive({"value": []})
    const device_filters = ref({
      "ready": true,
      "match_peripherals": true,
      "search": "",
    })

    let form_data = reactive({
      environment_component_obj: {},
      is_public: false,
      application: undefined,
      devices: [],
      timings: [],
    })

    let collections = ref([])

    fetch_with_retry(`/api/jobs/`, callback=function(json){
      jobs.value = json
      jobs_loading.value = false

      jobs.value.forEach(process_created_by)
    }, error_callback=function(res){
      jobs_loading_error_message = "Could not get jobs"
    })
    fetch_with_retry(`/api/applications/`, callback=function(json){
      applications.value = json
      applications.value.forEach(process_created_by)
      applications.options = applications.value.map((app) => {
        return {
          "label": `${app.name} (${app.uuid})` ,
          "value": app,
        }
      })
    }, error_callback=function(res){
      console.error(res)
    })
    fetch_with_retry(`/api/devices/`, callback=function(json){
      devices.value = json
      devices.options = devices.value.map((dev) => {
        return {
          "label": dev.device_name,
          "value": dev.uuid,
        }
      })
    }, error_callback=function(res){
      console.error(res)
    })
    fetch_with_retry(`/api/collections/`, callback=function(json){
      collections.value = json
    })

    let services = ref([])
    fetch_with_retry(`/api/services/`, callback=function(json){
      services.value = json
    })

    function filterFn(list, val, update){
      update(() => {
        if (val === "") {
          list.options_filter = list.options
        } else {
          const needle = val.toLocaleLowerCase()
          list.options_filter = list.options.filter((obj) => {
            return obj.value.name.toLocaleLowerCase().indexOf(needle) > -1 ||
              obj.value.uuid.toLocaleLowerCase().indexOf(needle) > -1
          })  
        }
      })
    }
    function check_conflicts(old_devices, new_devices){
      const request = new Request(
        url=`/api/jobs/check/`,
        {
          method: 'POST',
          mode: 'same-origin',
          body: JSON.stringify({
            "devices": form_data.devices.map((uuid) => {
              return {"device_uuid": uuid}
            }),
            "timings": form_data.timings.map((str) => {
              return {"timing": str}
            }),
            "application": form_data.application,
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
        timeslot_conflicts.value = res["conflicts"]
        pending_timeslots.value = res["timeslots"]
      }).catch((response) => {
        console.error(response)
      }).finally(() => {
        jobs_form_disabled = false
        jobs_loading = false
      })
    }


    watch(() => form_data.devices, check_conflicts)
    function deviceFilterFn (val, update) {
      // Calculate required peripheral list.
      required_periph = []
      form_data.application.services.forEach(s => {
        let app_serv = services.value.find(serv => s.service == serv.uuid)
        app_serv.peripheral_schemas.forEach(ps => {
          required_periph.push(ps.peripheral_schema)
        })
      })

      return devices.value.filter(dev => dev.application_access
        ).filter(dev => { // Filter peripherals
        if(!device_filters.value.match_peripherals || required_periph.length == 0){
          return true
        } else {
          return required_periph.every(rp => {
            return dev.peripherals.some(p => {
              return p.peripheral.schema.type == rp
            })
          })
        }
      }).filter(dev => { // Filter ready status
        return !device_filters.value.ready || dev["is_ready"]
      }).filter(dev => { // Filter search text
        return device_filters.value.search.length == 0 || 
          dev.device_name.includes(device_filters.value.search) ||
          dev.uuid.includes(device_filters.value.search)
      })
    }

    return {
      jobs, jobs_loading, jobs_form_disabled, jobs_loading_error_message,
      applications,
      devices, device_filters,
      collections,
      appFilterFn (val, update) {
        filterFn(applications, val, update)
      },
      deviceFilterFn,
      continueFn(stepper){
        if(step.value === 1 && form_data.application){
          form_data.environment_component_obj.environment = form_data.application.parsed_env
        }
        stepper.next()
      },
      select_collection(collection){
        let filtered_devices = deviceFilterFn()
        collection.devices.map(dev_obj => dev_obj.device_uuid)
          .filter(uuid => { // UUIDs in the collection & matching filters
            return filtered_devices.some(fd => {
              return fd.uuid == uuid
            })
          })
          .filter( uuid => { // UUID not already selected
            return form_data.devices.indexOf(uuid) == -1
          }).forEach(uuid => {
            form_data.devices.push(uuid)
          })
        check_conflicts()
      },
      form_data,
      async submit(e) {
        // automatically get a partially filled in env
        if(form_data.environment_component_obj.new_key){
          form_data.environment_component_obj.environment[form_data.environment_component_obj.new_key] = form_data.environment_component_obj.new_value
        }
        jobs_form_disabled = true
        jobs_loading = true
        const request = new Request(
          url=`/api/jobs/`,
          {
            method: 'POST',
            mode: 'same-origin',
            body: JSON.stringify({
              "is_public": form_data.is_public,
              "application": form_data.application.uuid,
              "environment": JSON.stringify(form_data.environment_component_obj.environment),
              "devices": form_data.devices.map((uuid) => {
                return {"device_uuid": uuid}
              }),
              "timings": form_data.timings.map((str) => {
                return {"timing": str}
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
          jobs.value.unshift(res)
          notify(`Created job ${res.uuid}`)
        }).catch((response) => {
          notify("Could not create job!", type="negative")
          console.error(response)
        }).finally(() => {
          jobs_form_disabled = false
          jobs_loading = false
        })
      },
      delete_item(index){
        fetch(`/api/jobs/${this.jobs.value[index].uuid}`, {
          method: "DELETE",
          headers: get_headers(),
        }).then((response) => {
          if (response.ok) {
            this.jobs.value.splice(index, 1);
          } else {
            return Promise.reject(response);
          }
          notify("Deleted job.")
        }).catch((res) => {
          notify(`Could not delete job: ${res.detail}`, type="negative")
        })
      },
      not_empty: [
        value => {
          if (value) return true
          return 'Value cannot be empty.'
        },
      ],
      headers: [
        { label: "Created By", field: "created_by", name: "created_by", sortable: true, align: "left" },
        { label: "Created At", field: "created_at", name: "created_at", sortable: true, align: "left"},
        { label: "Public?", field: "is_public", name: "is_public", sortable: true, align: "left" },
        { label: "Application", field: "application", name: "application", align: "left" },
        { label: "Devices", field: "Devices", name: "devices", align: "left" },
        { label: "Timings", field: "timings", name: "timings", align: "left" },
        { name: 'action', label: 'Action', field: 'action' },
      ],
      table_filter_options,
      selected_table_filter: ref(table_filter_options[0]),
      initialPagination: {
        rowsPerPage: 0,
        descending: true,
        sortBy: 'created_at',
      },
      step,
      timeslot_conflicts, pending_timeslots,
    }
}}).use(Quasar)
.component("environment-component", EnvironmentComponent)
.component("timing-component", TimingComponent)
.mount('#app')
