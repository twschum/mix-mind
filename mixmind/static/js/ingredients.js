$.fn.dataTable.render.money_fmt = function(data, type, row, meta) {
    if (true) {
        //if (type === "display") {
        var value = (data+0.001).toFixed(2);
        return ret = "$" + " ".repeat(7-value.length) + value;
    }
    return data;
}

function myCallbackFunction (updatedCell, updatedRow, oldValue) {
    console.log("The new value for the cell is: " + updatedCell.data());
    console.log("The values for each cell in that row are: " + updatedRow.data());
}

$(document).ready( function () {
    var barstock_table = $("#barstock-table").DataTable( {
        "paging": false,
        "ajax": "/api/load_ingredients",
        "columns": [
            {data: "Category"}, // TODO use an enum def to sort by caregory
            {data: "Type"},
            {data: "Bottle"},
            {data: "In_Stock"},
            {data: "Proof", className: "text-right monospace", render: function(data, type, row, meta){
                if (type === "display"){
                    if (data == 0) {
                        return "&mdash;"
                    }
                    return ((data / 2.0)+0.01).toFixed(1) + " %";
                }
                return data;
            }},
            {data: "Size_oz", className: "text-right monospace", render: $.fn.dataTable.render.number('','.',1,''," oz")},
            {data: "Price_Paid", className: "text-right monospace", render: $.fn.dataTable.render.money_fmt},
            {data: "Cost_per_oz", className: "text-right monospace", render: $.fn.dataTable.render.money_fmt}
        ]
    });
    // editCell integration
    barstock_table.MakeCellsEditable({
        "onUpdate": myCallbackFunction,
        "confirmationButton": {
            "confirmCss": 'btn btn-sm btn-outline-success btn-icon',
            "cancelCss": 'btn btn-sm btn-outline-danger btn-icon',
            "confirmValue": '<i class="fa fa-check"></i>',
            "cancelValue": '<i class="fa fa-times"></i>'
        },

    })
} );


