function fetch_with_retry(url, callback, error_callback=function(r){}, backoff_count=0) {
  fetch(url).then((response) => {
    if (response.ok) {
      return response.json();
    }
    return Promise.reject(response);
  }).then(callback).catch((response) => {
    console.error(response)
    if(backoff_count > 3){
      console.error("failed after 3 backoff attempts")
      error_callback(response)
    } else {
      backoff_count++
      console.log(`retrying number ${backoff_count}`)
      setTimeout(
        fetch_with_retry(url, callback, backoff_count=backoff_count),
        backoff_count * 1000
      )
    }
  })
}

