$.fn.dataTable.render.money_fmt = function(data, type, row, meta) {
    if (true) {
        //if (type === "display") {
        var value = (data+0.001).toFixed(2);
        return ret = "$" + " ".repeat(7-value.length) + value;
    }
    return data;
}

var column_settings = [
    {data: "Category", name: "Category"}, // TODO use an enum def to sort by caregory
    {data: "Type", name: "Type"},
    {data: "Bottle", name: "Bottle"},
    {data: "In_Stock", name: "In_Stock"},
    {data: "Proof", name: "Proof", className: "text-right monospace", render: function(data, type, row, meta){
        if (type === "display"){
            if (data == 0) {
                return "&mdash;"
            }
            return ((data / 2.0)+0.01).toFixed(1) + " %";
        }
        return data;
    }},
    {data: "Size_oz", name: "Size_oz",
        className: "text-right monospace", render: $.fn.dataTable.render.number('','.',1,''," oz")},
    {data: "Price_Paid", name: "Price_Paid",
        className: "text-right monospace", render: $.fn.dataTable.render.money_fmt},
    {data: "Cost_per_oz", name: "Cost_per_oz",
        className: "text-right monospace", render: $.fn.dataTable.render.money_fmt}
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
