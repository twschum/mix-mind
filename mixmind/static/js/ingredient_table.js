function deleteRow (cell, row) {

};

var categories = {"Spirit": 0, "Liqueur": 1, "Vermouth": 2, "Bitters": 3, "Syrup": 4, "Juice": 5, "Mixer": 6, "Wine": 7, "Beer": 8, "Dry": 9, "Ice": 10}
// NOTE: in datatables 2.0, can use simply api.column(id).name()
var number_col_classes = "text-right monospace"
var column_settings = [
    {data: null, searchable: false, orderable: false, render: function(data, type, row, meta){
        //<i class="fas fa-plus"></i>
        var del_btn = '<button class="btn btn-sm btn-outline-danger" onclick="deleteRow(this)"><i class="far fa-trash-alt"></i></button>';
        return del_btn;
    }},
    {data: "Category", name: "Category", render: function(data, type, row, meta){
        switch (type) {
            case "sort":
            case "type":
                return categories[data];
        };
        return data;
    }},
    {data: "Type", name: "Type"},
    {data: "Bottle", name: "Bottle"},
    {data: "In_Stock", name: "In_Stock", render: function(data, type, row, meta){
        if (type == "display") {
            var input = '<input class="toggle-switch" type="checkbox"';
            input += ' data-toggle="toggle" data-on="&check;" data-off="&times;" data-onstyle="success" data-offstyle="danger" data-size="small"';
            input += ' onchange="$(this).updateEditableCell(this);"';
            input += (data) ? ' value="on" checked' : ' value="off"';
            input += '>';
            return input;
        }
        return data;
    }},
    {data: "ABV", name: "ABV", className: number_col_classes, render: function(data, type, row, meta){
        if (type == "display"){
            if (data == 0 || data == "0") {
                return "&mdash;"
            }
            return ((data/1.0)+0.01).toFixed(1) + " %";
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
        "ajax": "/api/ingredients",
        "columns": column_settings,
        // handles rendering of the toggle switches in the table
        "drawCallback": function() {
            $(".toggle-switch").bootstrapToggle();
        }
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
        "columns": [1,2,3,4,5,6,7,8], // allowed to edit these columns
        "inputTypes": [
            {
                "column": 0,
                "type": "list",
                "options": [
                    {"value":  "Spirit",    "display":  "Spirit"},
                    {"value":  "Liqueur",   "display":  "Liqueur"},
                    {"value":  "Vermouth",  "display":  "Vermouth"},
                    {"value":  "Bitters",   "display":  "Bitters"},
                    {"value":  "Syrup",     "display":  "Syrup"},
                    {"value":  "Juice",     "display":  "Juice"},
                    {"value":  "Mixer",     "display":  "Mixer"},
                    {"value":  "Wine",      "display":  "Wine"},
                    {"value":  "Beer",      "display":  "Beer"},
                    {"value":  "Dry",       "display":  "Dry"},
                    {"value":  "Ice",       "display":  "Ice"},
                ]
            }
        ]
    })
} );

jQuery.each( [ "put", "delete" ], function( i, method ) {
    jQuery[ method ] = function( url, data, callback, type ) {
        if ( jQuery.isFunction( data ) ) {
            type = type || callback;
            callback = data;
            data = undefined;
        }

        return jQuery.ajax({
            url: url,
            type: method,
            dataType: type,
            data: data,
            success: callback
        });
    };
});

function editCell (cell, row, oldValue) {
    if (cell.data() == oldValue) {
        return;
    }
    console.log("The new value for the cell is: " + cell.data());
    var col = column_settings[ cell.index().column ].name
    if (col == "Bottle") {
        bottle = oldValue;
    }
    else {
        bottle = row.data().Bottle;
    }
    if (col == "Type") {
        type_ = oldValue;
    }
    else {
        type_ = row.data().Type;
    }
    $.put("/api/ingredient", { row_index: row.index(), Bottle: bottle, Type: type_,
        field: col, value: cell.data() })
        .done(function(result) {
            if (result.status == "error") {
                alert("Error: " + result.message);
            }
            else if (result.status == "success") {
                barstock_table.row(result.row_index).data(result.data);
                $(".toggle-switch").bootstrapToggle();
            }
            else {
                console.log("Unknown formatted response: " + result);
            }
        });
};
