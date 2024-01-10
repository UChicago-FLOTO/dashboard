const { createApp, ref } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const job = ref({})
    const application = ref({})
    const devices = ref([])
    const services = ref([])

    let uuid = window.location.pathname.split("/")[3]
    fetch_with_retry(`/api/jobs/${uuid}`, callback=function(json){
      job.value = json
      process_created_by(job.value)

      fetch_with_retry(`/api/applications/${job.value.application}`, callback=function(json){
        application.value = json
      })

      job.value.computed_timings = job.value.timings.map(t => {
        return {
          "string": t.timing,
          "timeslots": job.value.timeslots.filter(ts => ts.note === t.timing)
        }
      })

      fetch_with_retry(`/api/jobs/${uuid}/events`, callback=function(json){
        job.value.events = json
      })

      fetch_with_retry(`/api/jobs/${uuid}/logs`, callback=function(json){
        job.value.logs = json
      })
    })
    fetch_with_retry(`/api/devices/`, callback=function(json){
      devices.value = json
    })
    fetch_with_retry(`/api/services`, callback=function(json){
      services.value = json
    })

    return {
      job, application, devices, services,
    }
}}).use(Quasar).mount('#app')
