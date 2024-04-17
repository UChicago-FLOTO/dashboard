function fetch_with_retry(url, callback, error_callback=base_error_callback, backoff_count=0, query_params=get_query_params()) {
  url += "?" + query_params
  fetch(url).then((response) => {
    if (response.ok) {
      return response.json();
    }
    return Promise.reject(response);
  }).then(callback).catch((response) => {
    console.error(response)
    if(response.status < 500){
      // Client error, we can't do anything bout it
      console.log("calling error callback")
      error_callback(response)
    } else {
      if(backoff_count > 3){
        console.error("failed after 3 backoff attempts")
        error_callback(response)
      } else {
        new_count = backoff_count + 1
        setTimeout(
          fetch_with_retry(url, callback, error_callback=error_callback, backoff_count=(new_count + 1)),
          new_count * 1000
        )
      }  
    }
  })
}

function get_headers(){
  const token = get_token()
  const headers = new Headers();
  headers.append("Authorization", `Token ${token}`);  
  headers.append("Content-Type", "application/json")
  return headers  
}

function get_query_params(){
  let ap = get_active_project()
  if(ap){
    return new URLSearchParams({
      "active_project": get_active_project(),
    })
  }
  return new URLSearchParams()
}

function get_token(){
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("token="))
    ?.split("=")[1];
}

function process_created_by(obj){
  obj.is_owned_by_current_user = obj.created_by_project == get_active_project()
  if ("environment" in obj){
    obj.parsed_env = JSON.parse(obj.environment)
  }
}

function base_error_callback(response){
  if (response.status == 403){
    Quasar.Notify.create({
      color: 'negative',
      message: 'You are not authorized to do that. Please contact an administrator if you believe this to be a mistake.', 
      icon: 'report_problem',
      multiLine: true,
      timeout: 0,
      actions: [
        { icon: 'close', color: 'white', round: true, handler: () => {} }
      ],
    })
  }
}

function notify(message, type="positive"){
  Quasar.Notify.create({
    type,
    message,
    multiLine: message.length > 30,
    timeout: 0,
    actions: [
      { icon: 'close', color: 'white', round: true, handler: () => {} }
    ],
  })
}

window.onload = function(){
  display_el = document.querySelector("#project_display span")
  form_el = document.querySelector("#project_display form")
  save_el = document.querySelector("#project_display button")
  select_el = document.querySelector("#project_display select")

  if(!(display_el && form_el)){
    return
  }

  form_el.style["display"] = "none"
  if(save_el){
    save_el.onclick = function(){
      form_el.style["display"] = "none"
      display_el.style["display"] = "block"

      const request = new Request(
        url=`/dashboard/set_active_project`,
        {
          method: 'POST',
          mode: 'same-origin',
          body: JSON.stringify({
            "uuid": select_el.value,
          }),
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.getElementsByName("csrfmiddlewaretoken")[0].value,
          },
          credentials: 'same-origin',
        }
      );
      fetch(request).then(() => {location.reload()})
    }
  }

  display_el.onclick = function(){
    form_el.style["display"] = "block"
    display_el.style["display"] = "none"

  }
}