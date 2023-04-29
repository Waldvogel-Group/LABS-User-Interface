export class Plot_manager {
  constructor(url, experiment_url) {
    this.current_experiment = "";
    this.source_first_message = true;
    this.source = new EventSource(url);
    console.log(experiment_url);
    this.experiment_url = experiment_url;
    this.charts = [];
    this.generate_DOM_header();
    this.source.onmessage = (event) => this.on_source_event_function(event);
  }

  on_source_event_function(event) {
    const data = JSON.parse(event.data);

    // If first message switch true, set current experiment
    if (this.source_first_message) {
      this.current_experiment = data.current_experiment;
      this.set_current_experiment(data.current_experiment);
      this.source_first_message = false;
    }

    // If the experiment remains, update or create plots, otherwise destroy plots
    if (this.current_experiment === data.current_experiment) {
      this.create_or_update_plots(data);
    } else {
      if (this.charts.length > 0) {
        for (const device of this.charts) {
          for (const plot of device.plots) {
            plot.plot.on_delete();
          }
        }
        // empty charts object list
        this.charts = [];
        // set new current experiment and create new plots from data.update
        this.current_experiment = data.current_experiment;
        this.set_current_experiment(this.current_experiment);
        this.create_or_update_plots(data);
      }
    }
  }

  create_or_update_plots(data) {
    // Iterate over all devices in update
    for (const [device, device_values] of Object.entries(data.updates)) {
      // check if device is allready registerd in decive object list
      const charts_index = this.charts.findIndex((device_group) => {
        return device_group.device === device;
      });

      // check will return -1 if not found, in that case, prepare new entry for new device
      if (charts_index == -1) {
        var device_group = {
          device: device,
          plots: [],
        };
        this.charts.push(device_group);
      }

      // Iterate over all observabes for device
      for (const [observable, observable_values] of Object.entries(
        device_values
      )) {
        // If there is an observable without updates, skip this one
        if (observable_values.length == 0) {
          continue;
        }

        if (charts_index >= 0) {
          // console.log(this.charts[charts_index])
          const plot_index = this.charts[charts_index].plots.findIndex(
            (plot) => {
              return plot.observable === observable;
            }
          );

          if (plot_index > -1) {
            this.charts[charts_index].plots[
              plot_index
            ].plot.update_data_storage(observable_values);
            this.charts[charts_index].plots[plot_index].plot.update_plot_data();
          } else {
            var device_div = this.append_device_to_dom(device);

            var charts_dict = {
              observable: observable,
              plot: this.create_plot(
                device,
                observable,
                observable_values,
                device_div
              ),
            };
            this.charts[charts_index].plots.push(charts_dict);
          }
        }
      }
    }
  }

  get_plot(plot_id) {}

  set_current_experiment(current_experiment) {
    // console.log("set_current_experiment")
    const h2_experiment = document.getElementById("subtitle");
    h2_experiment.innerText = `Current experiment: ${current_experiment}`;
  }

  generate_DOM_header() {
    const header_anchor = document.getElementById("device_information_header");

    const header = document.createElement("div");
    header.setAttribute("id", "header");

    const headline = document.createElement("h1");
    headline.innerHTML = "Detailed Run Information";

    const subtitle = document.createElement("h2");
    subtitle.setAttribute("id", "subtitle");
    subtitle.innerHTML = `Current experiment:`;

    header.appendChild(headline);
    header.appendChild(subtitle);
    this.append_experiment_overview_to_dom();
    header_anchor.appendChild(header);
  }
  get_active_experiment_json(path, success, error) {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          success(JSON.parse(xhr.responseText));
        } else {
          error(xhr);
        }
      }
    };
    xhr.open("GET", path, true);
    xhr.send();
  }

  append_experiment_overview_to_dom() {
    const header_anchor = document.getElementById("device_information_header");
    const header = document.createElement("div");
    header.setAttribute("id", "run_overview");
    header_anchor.appendChild(header);
  }

  append_device_to_dom(device) {
    if (!document.getElementById(device)) {
      // console.log("Appended to DOM")
      const devices_anchor = document.getElementById("devices");
      const device_div = document.createElement("div");
      device_div.setAttribute("id", String(device));
      devices_anchor.appendChild(device_div);
      return device_div;
    } else {
      return document.getElementById(device);
    }
  }

  create_plot(device, observable, observable_data, device_div) {
    if (observable == "remaining_time" || observable == "amount of charge") {
      var type = "progressBar";
      var plot = new ProgressBar(
        device,
        device_div,
        type,
        observable,
        observable_data,
        this.experiment_url
      );
    } else if (observable == "position") {
      var type = "progressBar";
      var plot = new TextInfo(
        device,
        device_div,
        type,
        observable,
        observable_data,
        this.experiment_url
      );
    } else {
      var type = "line";
      var plot = new LinePlot(
        device,
        device_div,
        type,
        observable,
        observable_data,
        this.experiment_url
      );
    }
    return plot;
  }
}

class PlotObject {
  constructor(
    id,
    anchor_div,
    canvas_needed,
    observable_data,
    observable,
    div_class,
    type,
    experiment_url
  ) {
    this.anchor_div = anchor_div;
    this.id = id + "_" + observable;
    this.observable = observable;
    this.average_chunk_size = 10;
    this.maximum_plot_data_length = 200;
    this.history_average_percentage = 0.8;
    this.limit_index = 0;
    this.plot_data = [];
    this.plot_div = this.set_plot_div(canvas_needed, div_class);
    this.all_data = [];
    this.experimental_parameter_value = [];
    this.get_observable_parameter_value(experiment_url);
    this.experiment_url = experiment_url;
    this.averaged_data = [];
    this.fist_timestamp = new Date(observable_data[0][0] * 1000);
    this.type = type;

    this.update_data_storage(observable_data);
  }

  get_readable_date(timestamp) {
    var date = new Date(timestamp);
    var readable_date = date.toLocaleTimeString("de-DE");
    return readable_date;
  }

  get_observable_parameter_value(path) {
    // var xhr = new XMLHttpRequest();
    // xhr.onreadystatechange = function () {
    //   if (xhr.readyState === 4) {
    //     if (xhr.status === 200) {
    //       this.set_experimental_parameter_value(JSON.parse(xhr.responseText));
    //     } else {
    //       this.set_experimental_parameter_value("N/A");
    //     }
    //   }
    // };
    // // add payload to get request
    // const parameter_name = "parameter_name";
    // const payload = `parameter_name=${this.observable}`;
    // console.log(path);

    // xhr.open("POST", path, true);
    // xhr.send(payload);
    console.log(this.observable);
    fetch(path, {
      method: "POST",
      body: JSON.stringify({
        parameter_name: this.observable,
      }),
      headers: {
        "Content-type": "application/json; charset=UTF-8",
      },
    })
      .then((response) => response.json())
      .then((json) => console.log(json));
  }

  set_experimental_parameter_value(experimental_parameter_value) {
    this.experimental_parameter_value = experimental_parameter_value;
    console.log(this.experimental_parameter_value);
    console.log("set_experimental_parameter_value");
  }

  set_plot_div(canvas_needed, div_class) {
    if (!document.getElementById(this.id)) {
      const parameter_and_observation_div = document.createElement("div");
      parameter_and_observation_div.setAttribute(
        "id",
        this.id + "-parameter_and_observation"
      );
      parameter_and_observation_div.setAttribute(
        "class",
        "parameter_and_observation"
      );
      const data_strin = document.createElement("p");
      data_strin.setAttribute("id", this.id + "-data_string");
      data_strin.setAttribute("class", "data_string");
      data_strin.innerHTML = this.observable + ": ";
      this.anchor_div.appendChild(parameter_and_observation_div);

      const newDiv = document.createElement("div");
      newDiv.setAttribute("class", div_class);
      if (canvas_needed) {
        const newCanvas = document.createElement("canvas");
        newCanvas.setAttribute("id", this.id);
        newDiv.appendChild(newCanvas);
      } else {
        newDiv.setAttribute("class", div_class);
        // wenn kein canvas benötigt wird (Progressbar oder Ventilanzeige, bekommt das übergeordnete Div die ID vom plot)
        newDiv.setAttribute("id", this.id);
      }
      // console.log(this.anchor_div_id)
      this.anchor_div.appendChild(newDiv);
      return newDiv;
    } else {
      // console.log("Div allready exists")
      return document.getElementById(this.id);
    }
  }

  on_delete() {
    while (this.plot_div.firstChild) {
      this.plot_div.removeChild(this.plot_div.firstChild);
    }
    this.plot_div.remove();
    this.anchor_div.remove();
  }

  readable_times(data) {
    // Get first timestamp
    console.log(typeof this.plot_data[0].timestamp);

    // Loop over data array
    for (const item of data) {
      // Calculate time passed since first timestamp
      const timePassed =
        new Date(item.timestamp).getTime() - this.fist_timestamp.getTime();

      // Calculate hours, minutes, and seconds from time passed
      const hours = Math.floor(timePassed / (1000 * 60 * 60));
      const minutes = Math.floor((timePassed % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timePassed % (1000 * 60)) / 1000);

      // Add new keys to item
      item.time = `${hours}:${minutes}:${seconds}`;
      item.timePassed = timePassed;
    }

    return data;
  }

  reduceArray(arr, int_dec) {
    // Split the array into two parts

    var firstPart = arr.slice(0, Math.floor(arr.length * 0.6));
    const secondPart = arr.slice(Math.floor(arr.length * 0.6));
    // If the first part is longer than 20, decimate it by averaging the values and timestamps
    //
    if (arr.length > this.maximum_plot_data_length) {
      const decimated = [];
      decimated.push(arr[0]);
      for (let i = 0; i < firstPart.length; i += int_dec) {
        const group = firstPart.slice(i, i + int_dec);
        const avgValue =
          group.reduce((sum, { value }) => sum + value, 0) / group.length;
        const avgTimestamp =
          group.reduce(
            (sum, { timestamp }) => sum + new Date(timestamp).getTime(),
            0
          ) / group.length;
        decimated.push({ value: avgValue, timestamp: new Date(avgTimestamp) });
      }
      firstPart = decimated;
      console.log(firstPart);
    }

    // Merge the two parts and return the result
    return [...firstPart, ...secondPart];
  }

  average_updates_within_one_secound(arrayOfArrays) {
    // IF the array is of lenght one then just push the object to the result array, otherwise check  the timestamps of all array entries and average over those that are eqal regarding a resolution of one secound.
    if (arrayOfArrays.length == 1) {
      // Don't iterate over arrayOfArrays, use it directly to make obj
      const [timestamp, value] = arrayOfArrays[0];
      const obj = {
        timestamp: new Date(timestamp * 1000),
        value: parseFloat(value),
      };
      return obj;
    } else {
      // Iterate over arrayOfArrays and create a new object for each array
      let result = [];
      let temp_array = [];
      let temp_timestamp = 0;
      for (const [timestamp, value] of arrayOfArrays) {
        // Create a new object for the current array
        const obj = {
          timestamp: new Date(timestamp * 1000),
          value: parseFloat(value),
        };

        // Find the matching object in the result array by comparing the timestamps
        if (temp_timestamp == 0) {
          temp_timestamp = timestamp;
          temp_array.push(obj);
        } else if (temp_timestamp == timestamp) {
          temp_array.push(obj);
        } else {
          // console.log(temp_array)
          const avgValue =
            temp_array.reduce((sum, { value }) => sum + value, 0) /
            temp_array.length;
          const avgTimestamp =
            temp_array.reduce(
              (sum, { timestamp }) => sum + new Date(timestamp).getTime(),
              0
            ) / temp_array.length;
          const averaged_obj = {
            timestamp: new Date(avgTimestamp),
            value: avgValue,
          };
          result.push(averaged_obj);
          temp_timestamp = timestamp;
          temp_array = [];
          temp_array.push(obj);
        }
      }
      return result;
    }
  }

  merge_and_reduce_raw_input(arrayOfArrays) {
    // Initialize the result array
    const result = [];

    if (arrayOfArrays.length == 1) {
      // Don't iterate over arrayOfArrays, use it directly to make obj
      const [timestamp, value] = arrayOfArrays[0];
      const obj = {
        timestamp: new Date(timestamp * 1000),
        value: parseFloat(value),
      };
      result.push(obj);
    } else {
      // Iterate over arrayOfArrays and create a new object for each array
      for (const [timestamp, value] of arrayOfArrays) {
        // Create a new object for the current array
        const obj = {
          timestamp: new Date(timestamp * 1000),
          value: parseFloat(value),
        };

        // Find the matching object in the result array by comparing the timestamps
        const matchingIndex = result.findIndex(
          (o) => Math.floor(o.timestamp / 1000) === Math.floor(timestamp / 1000)
        );

        // If a matching object is found, update its value by taking the average
        if (matchingIndex !== -1) {
          result[matchingIndex].value =
            (result[matchingIndex].value + value) / 2;
        }
        // Otherwise, add the new object to the result array
        else {
          result.push(obj);
        }
      }
    }

    // Iterate over the array of arrays

    // Check for overlap between the new data and the old data
    const earliestTimestamp = result[0].timestamp;
    const lastIndex = this.plot_data.length - 1;
    if (
      this.plot_data.length > 0 &&
      Math.floor(this.plot_data[lastIndex].timestamp / 1000) ===
        Math.floor(earliestTimestamp / 1000)
    ) {
      // Update the value of the last object in the this.plot_data array by taking the average
      this.plot_data[lastIndex].value =
        (this.plot_data[lastIndex].value + result[0].value) / 2;
      // Remove the first object from the result array
      result.shift();
    }

    // Append the result array to the this.plot_data array
    this.plot_data.push(...result);
    //   console.log(this.plot_data)
    // Calculate the number of new elements in the arrayOfArrays

    this.plot_data = this.reduceArray(this.plot_data, 2);
    console.log(this.plot_data);
    return result;
  }

  update_data_storage(observable_data) {
    // this.merge_and_reduce_raw_input(observable_data);
    console.log(observable_data);
    this.update_plot_data(observable_data);
    //
  }

  update_plot_data(observable_data) {
    // placeholder if not estalished in child class
  }
}

class LinePlot extends PlotObject {
  constructor(
    id,
    anchor_div_id,
    type,
    observable,
    observable_data,
    experiment_url
  ) {
    var canvas = true;
    super(
      id,
      anchor_div_id,
      canvas,
      observable_data,
      observable,
      "plot",
      type,
      experiment_url
    );
    this.observable = observable;
    this.type = type;
    this.point_color = "rgb(193 , 0 , 42)";
    this.borderColor = "rgb(193 , 0 , 42)"; //'rgb(181, 0, 0)'
    this.config = this.get_plot_config();
  }

  get_plot_config() {
    const config = {
      type: this.type,
      data: {
        datasets: [
          {
            data: [],
            label: this.observable,
            borderColor: this.borderColor,
            fill: false,
          },
        ],
      },
      options: {
        spanGaps: true,
        animation: true,
        responsive: true,
        parsing: {
          xAxisKey: "time",
          yAxisKey: "value",
        },
        datasets: {
          line: {
            pointRadius: 0, // disable for all `'line'` datasets
          },
        },
        elements: {
          point: {
            radius: 0, // default to disabled in all datasets
          },
        },
        plugins: {
          legend: {
            position: "top",
          },
          title: {
            display: true,
            text: this.observable,
          },
        },
      },
    };
    return config;
  }

  get_plot_context() {
    const context = document.getElementById(this.id).getContext("2d");
    return context;
  }

  set_plot_object() {
    const config = this.get_plot_config();
    const context = this.get_plot_context();
    console.log(config);
    const chart = new Chart(context, config);
    return chart;
  }

  addData(data) {
    // this.removeData()

    for (const datapoint of data) {
      this.plot.config.data.datasets[0].data.push(datapoint);
    }

    this.plot.update();
  }

  removeData() {
    // console.log("popped")

    this.plot.config.data.labels = [];
    for (const datapoint of this.plot.config.data.datasets[0].data) {
      this.plot.config.data.datasets[0].data.pop();
    }
    // this.plot.update();
  }

  readable_times(data) {
    // Get first timestamp
    console.log(typeof this.plot_data[0].timestamp);

    // Loop over data array
    for (const item of data) {
      // Calculate time passed since first timestamp
      const timePassed =
        new Date(item.timestamp).getTime() - this.fist_timestamp.getTime();

      // Calculate hours, minutes, and seconds from time passed
      const hours = Math.floor(timePassed / (1000 * 60 * 60));
      const minutes = Math.floor((timePassed % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timePassed % (1000 * 60)) / 1000);

      // Add new keys to item
      item.time = `${hours}:${minutes}:${seconds}`;
      item.timePassed = timePassed;
    }

    return data;
  }

  update_plot_data(observable_data) {
    console.log("update_plot_data");
    console.log(observable_data);
    if (this.plot == undefined) {
      this.plot = this.set_plot_object();
    }

    // Check if observable_data is empty or contains only one data point
    if (observable_data === undefined) {
      return; // Do nothing if empty
    } else if (observable_data.length === 0) {
      return; // Do nothing if empty
    }
    // else if (observable_data.length === 1) {
    //   const [timestamp, value] = observable_data[0];
    //   // Submit only one data point
    //   this.plot.data.labels.push(timestamp);
    //   this.plot.data.datasets.forEach((dataset) => {
    //     dataset.data.push(value);
    //   });
    // }
    else {
      // Iterate through each data point in the observable_data array
      observable_data.forEach((data_point) => {
        const [timestamp, value] = data_point; // Destructure the [timestamp, value] pair

        // Check if the plot data already contains a data point with the same timestamp
        const existing_data_point_index =
          this.plot.data.labels.indexOf(timestamp);
        if (existing_data_point_index > -1) {
          // If a data point with the same timestamp already exists, update its value
          this.plot.data.datasets.forEach((dataset) => {
            dataset.data[existing_data_point_index] = value;
          });
        } else {
          // If a data point with the same timestamp does not exist, add a new data point
          this.plot.data.labels.push(timestamp);
          this.plot.data.datasets.forEach((dataset) => {
            dataset.data.push(value);
          });
        }

        // Check if the plot data contains more than 600 entries
        if (this.plot.data.labels.length > 600) {
          // Shift the first data point off the data arrays
          this.plot.data.labels.shift();
          this.plot.data.datasets.forEach((dataset) => {
            dataset.data.shift();
          });
        }
      });
    }

    // Update the plot with the new data
    this.plot.update();
  }
}

class ProgressBar extends PlotObject {
  constructor(
    id,
    anchor_div,
    type,
    observable,
    observable_data,
    experiment_url
  ) {
    var canvas = false;
    super(
      id,
      anchor_div,
      canvas,
      observable_data,
      observable,
      "progress",
      type,
      experiment_url
    );
    this.observable = observable;
    this.type = type;
    console.log("constructor");
    this.progressBar = this.add_progress_bar();
    this.start_value = observable_data[0][1];
    this.latest_value = observable_data[observable_data.length - 1][1];
  }

  update_data_storage(observable_data) {
    console.log(observable_data.length);
    console.log(observable_data[observable_data.length - 1][1]);
    this.latest_value = observable_data[observable_data.length - 1][1];
    // this.update_plot_data();
    //
  }

  add_progress_bar() {
    console.log("adding progress bar");
    const progressBarWrapper = document.getElementById(this.id);
    const progressBar = document.createElement("div");
    progressBar.setAttribute("class", "progress-bar");
    progressBar.setAttribute("role", "progressbar");
    progressBar.setAttribute("aria-valuenow", "0");
    progressBar.setAttribute("aria-valuemin", "0");
    progressBar.setAttribute("aria-valuemax", "100");
    progressBarWrapper.appendChild(progressBar);
    return progressBar;
  }

  update_plot_data() {
    if (this.observable == "amount of charge") {
      var percentage_done = (
        ((parseFloat(this.start_value) - parseFloat(this.latest_value)) * 100) /
        parseFloat(this.start_value)
      ).toFixed(2);
    }
    var percentage_done = (
      ((parseFloat(this.start_value) - parseFloat(this.latest_value)) * 100) /
      parseFloat(this.start_value)
    ).toFixed(2);
    console.log(this.progressBar);
    this.progressBar.setAttribute("aria-valuenow", String(percentage_done));
    this.progressBar.setAttribute(
      "style",
      `width: ${String(percentage_done)}%`
    );
    this.progressBar.innerText = `${this.observable} `;
  }
}

class TextInfo extends PlotObject {
  constructor(
    id,
    anchor_div,
    type,
    observable,
    observable_data,
    experiment_url
  ) {
    var canvas = false;
    super(
      id,
      anchor_div,
      canvas,
      observable_data,
      observable,
      "text",
      type,
      experiment_url
    );
    this.observable = observable;
    console.log("Add TextInfo");
    this.type = type;
    this.position_history = [];
    this.current_value = false;
    this.last_change_time = new Date();
    this.add_html_view();
    this.update_data_storage(observable_data);
  }

  update_data_storage(observable_data) {
    if (this.position_history == undefined) {
      this.position_history = [];
    }
    if (observable_data.length >= 1) {
      for (const [timestamp, value] of observable_data) {
        console.log("Update data storage");
        console.log(timestamp);
        console.log(value);
        console.log(this.position_history);
        console.log(observable_data);
        this.position_history.push([timestamp, value]);
      }
    }
  }

  add_html_view() {
    const text_info_element_wrapper = document.getElementById(this.id);
    this.text_info_element = document.createElement("div");
    this.text_info_element.setAttribute("id", this.id + "_text_info");
    this.text_info_element.appendChild(this.add_text_info_html_element());
    this.text_info_element.appendChild(this.add_text_info_html_table());
    text_info_element_wrapper.appendChild(this.text_info_element);
  }

  add_text_info_html_table() {
    const text_info_table = document.createElement("div");
    text_info_table.setAttribute("id", this.id + "_text_table");
    const information_table = document.createElement("table");
    information_table.setAttribute("class", "table");
    information_table.setAttribute("id", this.id + "_information_table");

    const thead = document.createElement("thead");
    const th = document.createElement("th");
    th.innerHTML = `<th scope="col">Time</th>
                    <th scope="col">Value</th>`;
    thead.appendChild(th);
    information_table.appendChild(thead);
    text_info_table.appendChild(information_table);
    return text_info_table;
  }

  add_text_info_html_element() {
    const text_info_element_wrapper = document.getElementById(this.id);
    const text_info_element = document.createElement("div");
    text_info_element.setAttribute("id", this.id + "_text_recent");
    text_info_element_wrapper.appendChild(text_info_element);
    return text_info_element;
  }

  update_text_info_html_element(timestamp, value) {
    const text_info_element = document.getElementById(this.id + "_text_recent");
    text_info_element.innerHTML = `<p>${
      this.observable
    }: ${value} (last update: ${this.get_readable_date(timestamp)})</p>`;
  }

  append_row_to_table(timestamp, value) {
    const table = document.getElementById(this.id + "_information_table");
    const row = document.createElement("tr");
    row.innerHTML = `<td>${timestamp}</td>
                         <td>${value}</td>`;
    table.appendChild(row);
  }

  update_plot_data() {
    for (const [timestamp, value] of this.position_history) {
      this.last_change_time = this.get_readable_date(timestamp);
      this.current_value = value;
      this.append_row_to_table(this.last_change_time, value);
    }
    this.update_text_info_html_element(
      this.last_change_time,
      this.current_value
    );
    this.position_history = [];
  }
}
