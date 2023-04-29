function toggleStatic(paramId, post_url) {
    var isChecked = document.getElementById("static-parameter-switch-" + paramId).checked;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", post_url, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.send(JSON.stringify({ param_id: paramId, static_param: isChecked }));
  }

  function setDefaultValue(paramId, post_url, value) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", post_url, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.send(JSON.stringify({ param_id: paramId, default_value: value }));
  }