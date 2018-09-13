// NOTE: in datatables 2.0, can use simply api.column(id).name()
var number_col_classes = "text-right monospace"
var column_settings = [
    {data: "Category", name: "Category"}, // TODO use an enum def to sort by caregory
    {data: "Type", name: "Type"},
    {data: "Bottle", name: "Bottle"},
    {data: "In_Stock", name: "In_Stock"},
    {data: "Proof", name: "Proof", className: number_col_classes, render: function(data, type, row, meta){
        if (type === "display"){
            if (data == 0) {
                return "&mdash;"
            }
            return ((data / 2.0)+0.01).toFixed(1) + " %";
        }
        return data;
    }},
    {data: "Size_mL", name: "Size_mL",
        className: number_col_classes, render: $.fn.dataTable.render.number('','.',0,''," mL")},
    {data: "Size_oz", name: "Size_oz",
        className: number_col_classes, render: $.fn.dataTable.render.number('','.',1,''," oz")},
    {data: "Price_Paid", name: "Price_Paid",
        className: number_col_classes, render: $.fn.dataTable.render.number(',','.',2,"$ ")},
    {data: "Cost_per_oz", name: "Cost_per_oz",
        className: number_col_classes, render: $.fn.dataTable.render.number(',','.',3,"$ ")}
]

var barstock_table;
$(document).ready( function () {
    barstock_table = $("#barstock-table").DataTable( {
        "paging": false,
        "ajax": "/api/load_ingredients",
        "columns": column_settings
    });
    // editCell integration
    barstock_table.MakeCellsEditable({
        "onUpdate": editCell,
        "confirmationButton": {
            "confirmCss": 'btn btn-sm btn-outline-success btn-icon',
            "cancelCss": 'btn btn-sm btn-outline-danger btn-icon',
            "confirmValue": '<i class="fa fa-check" style="width:1rem;"></i>',
            "cancelValue": '<i class="fa fa-times" style="width:1rem;"></i>'
        },

    })
} );


function editCell (cell, row, oldValue) {
    console.log("The new value for the cell is: " + cell.data());
    if (cell.data() == oldValue) {
        return null;
    }
}
