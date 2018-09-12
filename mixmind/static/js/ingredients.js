$.fn.dataTable.render.money_fmt = function(data, type, row, meta) {
    if (true) {
    //if (type === "display") {
        var value = (data+0.001).toFixed(2);
        return ret = "$" + " ".repeat(7-value.length) + value;
    }
    return data;
}

$(document).ready( function () {
	$("#barstock-table").DataTable( {
		"paging": false,
		"ajax": "/api/load_ingredients",
        "columns": [
            {data: "Category"}, // TODO use an enum def to sort by caregory
            {data: "Type"},
            {data: "Bottle"},
            {data: "In_Stock"},
            {data: "Proof", className: "text-right", render: function(data, type, row, meta){
                if (type === "display"){
                    return ((data / 2.0)+0.01).toFixed(1) + " %";
                }
                return data;
            }},
            {data: "Size_oz", className: "text-right", render: $.fn.dataTable.render.number('','.',1,''," oz")},
            {data: "Price_Paid", className: "text-right", render: $.fn.dataTable.render.money_fmt},
            {data: "Cost_per_oz", className: "text-right", render: $.fn.dataTable.render.money_fmt}
        ]
		});
} );
