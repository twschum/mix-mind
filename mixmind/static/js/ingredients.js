$(document).ready( function () {
	$('#barstock-table').DataTable( {
		"paging": false,
		"ajax": "/api/load_ingredients",
        "columns": [
            {data: "Category", title: "ASDF"},
            {data: "Type"},
            {data: "Bottle"},
            {data: "In_Stock"},
            {data: "Proof", render: function(data, type, row, meta){
                if (type === "display"){
                    return ((data / 2.0)+0.01).toFixed(1) + "%";
                }
                return data;
            }},
            {data: "Size_oz"},
            {data: "Price_Paid", render: function(data, type, row, meta){
                return "$" + data;
            }},
            {data: "Cost_per_oz"}
        ]
		});
} );
