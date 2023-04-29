export class Experiment_table {
  div_name;
  columns;
  data;
  gridJS;

  constructor(experiment_name, columns) {
      this.anchor_div_id = "experiment_tables";
      this.experiment_name = experiment_name;
      this.columns = columns;
      this.div_name = experiment_name;
      this.addTableDiv()
  }

  colums_with_additional_infos() {
      const additional_colums = ['name', 'type']
      return additional_colums.concat(this.columns)
  }

  generate_row_wise_data() {
      var rows = []
      for (const [counter, run_data] of Object.entries(this.data)) {
          var row = [run_data.name, run_data.type]
          for (const [parameter, parameter_data] of Object.entries(run_data.parameters)) {

              row.push(parameter_data[0])
          }
          rows.push(row)
      }
      return rows
  }

  addTableDiv() {

      if (!document.getElementById(this.div_name)) {
          const newDiv = document.createElement('div');
          newDiv.setAttribute('id', this.div_name)
          var parentDiv = document.getElementById(this.anchor_div_id);
          parentDiv.appendChild(newDiv);

      }
  }

  createGridJSTable() {
      this.gridJS = new gridjs.Grid({
          columns: this.colums_with_additional_infos(),
          data: this.generate_row_wise_data(),
          sort: true,
          className: {
            table: "table",
          },
      }).render(document.getElementById(this.div_name));

  }

  updateGridJSTable() {
      this.gridJS.updateConfig({
          data: this.generate_row_wise_data(),
      }).forceRender();
  }

}