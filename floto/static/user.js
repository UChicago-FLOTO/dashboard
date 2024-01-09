const { createApp, ref } = Vue

createApp({
    delimiters: ["[[", "]]"],
    setup() {
        const key_visible = ref(false)
        const projects = ref([])
        const new_user_email = ref("")
        fetch_with_retry(`/api/projects`, callback=function(json){
            projects.value = json
        })

        return {
            key_visible,
            projects,
            new_user_email,
            set_active_project(uuid){
              console.log("click!", uuid)
              const request = new Request(
                url=`/dashboard/set_active_project`,
                {
                  method: 'POST',
                  mode: 'same-origin',
                  body: JSON.stringify({
                    "uuid": uuid,
                  }),
                  headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.getElementsByName("csrfmiddlewaretoken")[0].value,
                  },
                  credentials: 'same-origin',
                }
              );
              fetch(request).then((res) => {
                if (res.ok) {
                  notify("Updated active project")
                } else {
                  return Promise.reject(res);
                }
              }).catch((response) => {
                console.error(response)
                // TODO notify
                notify("Could not update active project", type="negative")
              });
            },
            copy_key(){
                var apiKeyField = document.getElementById('api-key');
                apiKeyField.select();
                window.navigator.clipboard.writeText(apiKeyField.value).then(_ => {
                    notify(`Copied API key to clipboard`)
                }).catch(_ => {
                    notify("Failed to copy API key.", type="negative");
                });        
            },
            async addNewMember(project_uuid) {
                const project = projects.value.find(p => p.uuid === project_uuid)
                const new_members = project.members
                if (new_user_email.value){
                    new_members.push({"email": new_user_email.value})
                }
                const request = new Request(
                  url=`/api/projects/${project_uuid}/`,
                  {
                    method: 'PATCH',
                    mode: 'same-origin',
                    body: JSON.stringify({
                        "members": new_members
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
                  project.members = res.project.members
                  if (res.errors.length > 0){
                    notify(`Problem occured updating members for ${project.name}:\n${res.errors.join('\n')}`, type="negative")
                  } else {
                    notify(`Updated members for ${project.name}`)
                  }
                }).catch((response) => {
                  notify(`Could not update project: ${project.name}`, type="negative")
                  console.error(response)
                })
              },
        }
    }
}).use(Quasar).mount('#app')
