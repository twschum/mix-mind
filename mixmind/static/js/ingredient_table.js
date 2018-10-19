var categories = {"Spirit": 0, "Liqueur": 1, "Vermouth": 2, "Bitters": 3, "Syrup": 4, "Juice": 5, "Mixer": 6, "Wine": 7, "Beer": 8, "Dry": 9, "Ice": 10}
// NOTE: in datatables 2.0, can use simply api.column(id).name()
var number_col_classes = "text-right monospace"
var column_settings = [
    {data: null, searchable: false, orderable: false, render: function(data, type, row, meta){
        var clone_btn = '<button type="button" class="close" onclick="cloneIngredient(this)" title="Add new ingreadient starting with a copy of this ingredient"><i class="far fa-clone"></i></button>';
        return clone_btn;
    }},
    {data: null, searchable: false, orderable: false, render: function(data, type, row, meta){
        var del_btn = '<button type="button" class="close" onclick="deleteConfirm(this)" title="Delete this ingredient"><i class="far fa-trash-alt"></i></button>';
        return del_btn;
    }},
    {data: "In_Stock", name: "In_Stock", render: function(data, type, row, meta){
        if (type == "display") {
            var input = '<input class="toggle-switch" type="checkbox"';
            input += ' data-toggle="toggle" data-on="&lt;i class=&quot;fas fa-check toggle-icon&quot;&gt;&lt;/i&gt;" data-off="&lt;i class=&quot;fas fa-times toggle-icon&quot;&gt;&lt;/i&gt;" data-onstyle="success" data-offstyle="secondary" data-height="1.75rem;" data-width="2.5rem;"';
            input += ' onchange="$(this).updateEditableCell(this);"';
            input += (data) ? ' value="on" checked' : ' value="off"';
            input += '>';
            return input;
        }
        return data;
    }},
    {data: "Kind", name: "Kind"},
    {data: "Type", name: "Type"},
    {data: "Category", name: "Category", render: function(data, type, row, meta){
        switch (type) {
            case "sort":
            case "type":
                return categories[data];
        };
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
        "ajax": "/api/ingredients",
        "paging": true,
        "lengthChange": false,
        "pageLength": 20,
        "dom": "<'row no-gutters'<'col-sm-12 col-md-4 order-3 order-md-1'<'#toolbar.row no-gutters'>><'col-md-5 order-2'><'col-sm-12 col-md-3 order-1 order-md-3'f>>" +
               "<'row'<'col-sm-12'tr>>" +
               "<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
        "language": {
            "search": "",
            "searchPlaceholder": "Search...",
        },
        "rowId": "iid",
        "columns": column_settings,
        // sort by the Category column
        "order": [[ 5, 'asc' ]],
        // handles rendering of the toggle switches in the table
        "drawCallback": function() {
            $(".toggle-switch").bootstrapToggle();
        }
    });
    // copy the content of the controls div into the toolbar area
    $('#toolbar').html($('#controls').html());
    $('#barstock-table_filter > label').addClass('w-100');
    $('#barstock-table_filter > label > input').addClass('ml-0 w-100').removeClass('form-control-sm');
    // editCell integration
    barstock_table.MakeCellsEditable({
        "onUpdate": editCell,
        "onDelete": deleteRow,
        "confirmationButton": {
            //"confirmCss": 'btn btn-sm btn-outline-success btn-icon',
            "confirmCss": 'close close-color',
            "cancelCss": 'close close-color',
            "confirmValue": '<i class="fa fa-check text-success line-200"></i>',
            "cancelValue": '<i class="fa fa-times text-danger line-200"></i>'
        },
        "inputCss": '',
        "columns": [2,3,4,5,6,7,8,9], // allowed to edit these columns
        "inputTypes": [
            {
                "column": 5,
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

function editCell(cell, row, oldValue) {
    var data, col, row_iid;
    data = cell.data().trim();
    if (data == oldValue) {
        return;
    }
    row_iid = row.data().iid;
    col = column_settings[ cell.index().column ].name;
    $.put("/api/ingredient", { iid: row_iid, field: col, value: data })
        .done(function(result) {
            if (result.status == "error") {
                cell.data(oldValue);
                alert("Error: " + result.message);
            }
            else if (result.status == "success") {
                if (result.data.iid == row_iid) {
                    row.data(result.data);
                    $(".toggle-switch").bootstrapToggle();
                }
                else {
                    console.log("Error: response missing or has incorrect 'iid'");
                }
            }
            else {
                console.log("Unknown formatted response: " + result);
            }
        });
};

function deleteRow(row) {
    var modal, msg;
    modal = $('#confirm-delete-ingredient');
    $.delete("/api/ingredient", { iid: row.data().iid })
        .done(function(result) {
            modal.find('.btn-danger').addClass('d-none');
            if (result.status == "error") {
                msg = "Error: " + result.message;
            }
            else if (result.status == "success") {
                if (result.data.iid == row.data().iid) {
                    console.log("DEL: "+result.message);
                    msg = 'Successfully removed '+ row.data().Kind +' ('+ row.data().Type +').';
                    row.remove().draw();
                }
                else {
                    msg = "Error: response missing or has incorrect 'iid'";
                }
            }
            else {
                msg = "Unknown formatted response: " + result;
            }
            modal.find('p').text(msg);
        });
};

function deleteConfirm(callingElement) {
    var modal = $('#confirm-delete-ingredient');
    var table = $(callingElement).closest("table").DataTable().table();
    var row = table.row($(callingElement).parents('tr'));
    var text = 'Are you sure you want to remove '+ row.data().Kind +' ('+ row.data().Type +') from the database?';
    modal.find('p').text(text);
    var button = $('#confirm-delete-button').removeClass('d-none').data('rowSelector', row.id(true));
    button.on('click', function(e) {
        $(callingElement).deleteEditableRow($('#confirm-delete-button').data('rowSelector'));
    });
    modal.modal('show');
};

function cloneIngredient(callingElement) {
    var modal = $('#add-ingredient');
    var row = $(callingElement).closest("table").DataTable().table().row($(callingElement).parents('tr'));
    modal.find('input[name="kind"]').val(row.data().Kind)
    modal.find('input[name="category"]').val(row.data().Category)
    modal.find('input[name="type_"]').val(row.data().Type)
    modal.find('input[name="abv"]').val(row.data().ABV)
    modal.find('input[name="size"]').val(row.data().Size_mL)
    modal.find('input[name="price"]').val(row.data().Price_Paid)
    modal.modal('show');
};

function clearModalForm() {
    var modal = $('#add-ingredient');
    modal.find('input[name="kind"]').val('')
    modal.find('input[name="category"]').val('')
    modal.find('input[name="type_"]').val('')
    modal.find('input[name="abv"]').val('')
    modal.find('input[name="size"]').val('')
    modal.find('input[name="price"]').val('')
}

