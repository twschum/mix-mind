/*! CellEdit 1.0.19
 * ©2016 Elliott Beaty - datatables.net/license
 */

/**
 * @summary     CellEdit
 * @description Make a cell editable when clicked upon
 * @version     1.0.19
 * @file        dataTables.editCell.js
 * @author      Elliott Beaty
 * @contact     elliott@elliottbeaty.com
 * @copyright   Copyright 2016 Elliott Beaty
 *
 * This source file is free software, available under the following license:
 *   MIT license - http://datatables.net/license/mit
 *
 * This source file is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE. See the license files for details.
 *
 * For details please refer to: http://www.datatables.net
 */

jQuery.fn.dataTable.Api.register('MakeCellsEditable()', function (settings) {
    var table = this.table();

    jQuery.fn.extend({
        // UPDATE
        updateEditableCell: function (callingElement) {
            // Need to redeclare table here for situations where we have more than one datatable on the page. See issue6 on github
            var table = $(callingElement).closest("table").DataTable().table();
            var row = table.row($(callingElement).parents('tr'));
            var cell = table.cell($(callingElement).parents('td'));
            var columnIndex = cell.index().column;
            var inputField = getInputField(callingElement);

            // Update
            var newValue = inputField.val();
            if (!newValue && ((settings.allowNulls) && settings.allowNulls != true)) {
                // If columns specified
                if (settings.allowNulls.columns) {
                    // If current column allows nulls
                    if (settings.allowNulls.columns.indexOf(columnIndex) > -1) {
                        _update(newValue);
                    } else {
                        _addValidationCss();
                    }
                    // No columns allow null
                } else if (!newValue) {
                    _addValidationCss();
                }
                //All columns allow null
            } else {
                _update(newValue);
            }
            function _addValidationCss() {
                // Show validation error
                if (settings.allowNulls.errorClass) {
                    $(inputField).addClass(settings.allowNulls.errorClass)
                } else {
                    $(inputField).css({ "border": "red solid 1px" });
                }
            }
            function _update(newValue) {
                var oldValue = cell.data();
                cell.data(newValue);
                //Return cell & row.
                settings.onUpdate(cell, row, oldValue);
            }
            // Get current page
            var currentPageIndex = table.page.info().page;

            //Redraw table
            table.page(currentPageIndex).draw(false);
        },
        // CANCEL
        cancelEditableCell: function (callingElement) {
            var table = $(callingElement).closest("table").DataTable().table();
            var cell = table.cell($(callingElement).parents('td'));
            // Set cell to it's original value
            cell.data(cell.data());

            // Redraw table
            table.draw();
        },
        // DELETE
        deleteEditableRow: function(rowSelector) {
            var table = $(rowSelector).closest("table").DataTable().table();
            var row = table.row(rowSelector);
            // Handler should call remove on the row
            settings.onDelete(row);

            // Get current page
            var currentPageIndex = table.page.info().page;
            // Redraw table
            table.page(currentPageIndex).draw(false);
        }
    });

    // Destroy
    if (settings === "destroy") {
        $(table.body()).off("click", "td");
        table = null;
    }

    if (table != null) {
        // On cell click
        $(table.body()).on('click', 'td', function () {

            var currentColumnIndex = table.cell(this).index().column;

            // DETERMINE WHAT COLUMNS CAN BE EDITED
            if ((settings.columns && settings.columns.indexOf(currentColumnIndex) > -1) || (!settings.columns)) {
                var row = table.row($(this).parents('tr'));
                editableCellsRow = row;

                var cell = table.cell(this).node();
                var oldValue = table.cell(this).data();
                // Sanitize value
                oldValue = sanitizeCellValue(oldValue);

                // Show input
                if (!$(cell).find('input').length && !$(cell).find('select').length && !$(cell).find('textarea').length) {
                    // Input CSS
                    var input = getInputHtml(currentColumnIndex, settings, oldValue);
                    $(cell).html(input.html);
                    if (input.focus) {
                        $('#ejbeatycelledit').focus();
                    }
                }
            }
        });
    }

});

function onEnterHandler(event, callingElement) {
    // Allow submit-on-enter from text form fields
    // cancel-on-esc broken in chrome
    if (event.key === "Enter") {
        $(callingElement).updateEditableCell(callingElement);
    }
    else if (event.key === "Esc" || event.key === "Escape") {
        $(callingElement).cancelEditableCell(callingElement);
    }
};

function getInputHtml(currentColumnIndex, settings, oldValue) {
    var inputSetting, inputType, input, inputCss, confirmCss, cancelCss, confirmValue, cancelValue;
    var registerOnEnter = "onkeyup='onEnterHandler(event, this)'";

    input = {"focus":true,"html":null}

    if(settings.inputTypes){
        $.each(settings.inputTypes, function (index, setting) {
            if (setting.column == currentColumnIndex) {
                inputSetting = setting;
                inputType = inputSetting.type.toLowerCase();
            }
        });
    }

    inputCss = "form-control form-control-sm "
    if (settings.inputCss) {
        inputCss += settings.inputCss;
    }

    if (settings.confirmationButton) {
        inputType = inputType + "-confirm";
        // TODO min widths here
        input.html = "<div class='input-group' style='min-width:9rem;'>";
    }
    else {
    input.html = "";
    }
    switch (inputType) {
        case "list":
            input.html += "<select class='" + inputCss + "' onchange='$(this).updateEditableCell(this);'>";
            $.each(inputSetting.options, function (index, option) {
                if (oldValue == option.value) {
                   input.html += "<option value='" + option.value + "' selected>" + option.display + "</option>"
                } else {
                   input.html += "<option value='" + option.value + "' >" + option.display + "</option>"
                }
            });
            input.html += "</select>";
            input.focus = false;
            break;
        case "list-confirm": // List w/ confirm
            input.html += "<select class='" + inputCss + "'>";
            $.each(inputSetting.options, function (index, option) {
                if (oldValue == option.value) {
                   input.html += "<option value='" + option.value + "' selected>" + option.display + "</option>"
                } else {
                   input.html += "<option value='" + option.value + "' >" + option.display + "</option>"
                }
            });

            input.html += "</select>"
            input.focus = false;
            break;
        case "datepicker": //Both datepicker options work best when confirming the values
        case "datepicker-confirm":
            // Makesure jQuery UI is loaded on the page
            if (typeof jQuery.ui == 'undefined') {
                alert("jQuery UI is required for the DatePicker control but it is not loaded on the page!");
                break;
            }
            jQuery(".datepick").datepicker("destroy");
            input.html += "<input id='ejbeatycelledit' type='text' name='date' class='datepick " + inputCss + "'   value='" + oldValue + "'></input>";
            setTimeout(function () { //Set timeout to allow the script to write the input.html before triggering the datepicker
                var icon = "http://jqueryui.com/resources/demos/datepicker/images/calendar.gif";
                // Allow the user to provide icon
                if (typeof inputSetting.options !== 'undefined' && typeof inputSetting.options.icon !== 'undefined') {
                    icon = inputSetting.options.icon;
                }
                var self = jQuery('.datepick').datepicker(
                    {
                        showOn: "button",
                        buttonImage: icon,
                        buttonImageOnly: true,
                        buttonText: "Select date"
                    });
            },100);
            break;
        case "undefined-confirm": // text input w/ confirm
        case "text-confirm": // text input w/ confirm
            input.html += "<input id='ejbeatycelledit' class='"+ inputCss +"' "+ registerOnEnter +" value='"+ oldValue +"'></input>";
            break;
        case "textarea":
        case "textarea-confirm":
            input.html += "<textarea id='ejbeatycelledit' class='"+ inputCss +"' "+ registerOnEnter +">"+ oldValue +"</textarea>";
            break;
        default: // text input
            input.html += "<input id='ejbeatycelledit' class='" + inputCss + "' onfocusout='$(this).updateEditableCell(this)' value='" + oldValue + "'></input>";
            break;
    }
    if (settings.confirmationButton) {
        confirmCss = settings.confirmationButton.confirmCss;
        confirmValue = settings.confirmationButton.confirmValue;
        cancelCss = settings.confirmationButton.cancelCss;
        cancelValue = settings.confirmationButton.cancelValue;
        input.html += "<div class='input-group-append form-ht-sm'>"
        input.html += "<div class='input-group-text p-0'><a href='javascript:void(0);' class='" + confirmCss + "' onclick='$(this).updateEditableCell(this)'>" + confirmValue + "</a>";
        input.html += "<a href='javascript:void(0);' class='" + cancelCss + "' onclick='$(this).cancelEditableCell(this)'>" + cancelValue + "</a></div>";
        input.html += "</div>"; // from the input-group-append
        input.html += "</div>"; // from the input-group
    }
    return input;
}

function getInputField(callingElement) {
    // Update datatables cell value
    var inputField;
    switch ($(callingElement).prop('nodeName').toLowerCase()) {
        case 'a': // This means they're using confirmation buttons
            if ($(callingElement).parents('td').find('input').length > 0) {
                inputField = $(callingElement).parents('td').find('input');
            }
            if ($(callingElement).parents('td').find('select').length > 0) {
                inputField = $(callingElement).parents('td').find('select');
            }
            if ($(callingElement).parents('td').find('textarea').length > 0) {
                inputField = $(callingElement).parents('td').find('textarea');
            }
        break;
        default:
            inputField = $(callingElement);
    }
    return inputField;
}

function sanitizeCellValue(cellValue) {
    if (typeof (cellValue) === 'undefined' || cellValue === null || cellValue.length < 1) {
        return "";
    }

    // If not a number
    if (isNaN(cellValue)) {
        // escape single quote
        cellValue = cellValue.replace(/'/g, "&#39;");
    }
    return cellValue;
}
