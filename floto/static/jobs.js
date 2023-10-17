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

    let form_data = reactive({
      environment: {},
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
      console.log(res)
      // TODO
    })
    fetch_with_retry(`/api/devices/`, callback=function(json){
      devices.value = json.filter((dev) => {
        return dev["belongs_to__application"]["__id"] == 13
      })
      devices.options = devices.value.map((dev) => {
        return {
          "label": dev.device_name,
          "value": dev.uuid,
        }
      })
    }, error_callback=function(res){
      console.log(res)
      // TODO
    })
    fetch_with_retry(`/api/collections/`, callback=function(json){
      collections.value = json
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

    watch(() => form_data.devices, async function(old_devices, new_devices){
      const request = new Request(
        url=`/api/timeslots/check/`,
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
    })

    return {
      jobs, jobs_loading, jobs_form_disabled, jobs_loading_error_message,
      applications,
      devices,
      collections,
      appFilterFn (val, update) {
        filterFn(applications, val, update)
      },
      deviceFilterFn (val, update) {
        filterFn(devices, val, update)
      },
      continueFn(stepper){
        if(step.value === 1 && form_data.application){
          form_data.environment = form_data.application.parsed_env
        }
        stepper.next()
      },
      select_collection(collection){
        form_data.devices = collection.devices.map(dev_obj => dev_obj.device_uuid)
      },
      form_data,
      async submit(e) {
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
              "environment": JSON.stringify(form_data.environment),
              "devices": form_data.devices.map((uuid) => {
                return {"device_uuid": uuid}
              }),
              "timings": form_data.timings.map((str) => {
                return {"timing": str}
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
          jobs.value.push(res)
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
        { label: "Created At", field: "created_at", name: "created_at", sortable: true, align: "left" },
        { label: "Public?", field: "is_public", name: "is_public", sortable: true, align: "left" },
        { label: "Application", field: "application", name: "application", align: "left" },
        { label: "Devices", field: "Devices", name: "devices", align: "left" },
        { label: "Environment", field: "environment", name: "environment", align: "left" },
        { label: "Timings", field: "timings", name: "timings", align: "left" },
        { label: "Timeslots", field: "timeslots", name: "timeslots", align: "left" },
        { name: 'action', label: 'Action', field: 'action' },
      ],
      table_filter_options,
      selected_table_filter: ref(table_filter_options[0]),
      initialPagination: {
        rowsPerPage: 0,
      },
      step,
      timeslot_conflicts, pending_timeslots,
    }
}}).use(Quasar)
.component("environment-component", EnvironmentComponent)
.component("timing-component", TimingComponent)
.mount('#app')
