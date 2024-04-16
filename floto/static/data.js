const { createApp, ref } = Vue

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const datasets = ref([])
    fetch_with_retry(`/api/datasets/`, callback=function(json){
      datasets.value = json
    })


    return {
      datasets,
      headers: [
        { label: "Name", field: "name", name: "name", sortable: true, align: "left" },
        { name: 'description', label: 'Description', field: 'description', align: "left" },
        { name: 'url', label: 'Download', field: 'url' },
      ],
      initialPagination: {
        rowsPerPage: 10,
        sortBy: 'name',
        descending: true,
      }
    }
}}).use(Quasar).mount('#app')
