
// toggle up and down arrows on the navdrops
$(document).ready( function () {
    // TODO somehow make this smarter
    // bar selector
    $("#barNavdrop").on("shown.bs.collapse", function() {
        $("#barNavdropIcon").removeClass("fa-caret-down").addClass("fa-caret-up");
    });
    $("#barNavdrop").on("hidden.bs.collapse", function() {
        $("#barNavdropIcon").removeClass("fa-caret-up").addClass("fa-caret-down");
    });
    $("#barDropdown").on("shown.bs.dropdown", function() {
        $("#barDropdownIcon").removeClass("fa-caret-down").addClass("fa-caret-up");
    });
    $("#barDropdown").on("hidden.bs.dropdown", function() {
        $("#barDropdownIcon").removeClass("fa-caret-up").addClass("fa-caret-down");
    });
    // admin selector
    $("#adminNavdrop").on("shown.bs.collapse", function() {
        $("#adminNavdropIcon").removeClass("fa-caret-down").addClass("fa-caret-up");
    });
    $("#adminNavdrop").on("hidden.bs.collapse", function() {
        $("#adminNavdropIcon").removeClass("fa-caret-up").addClass("fa-caret-down");
    });
    $("#adminDropdown").on("shown.bs.dropdown", function() {
        $("#adminDropdownIcon").removeClass("fa-caret-down").addClass("fa-caret-up");
    });
    $("#adminDropdown").on("hidden.bs.dropdown", function() {
        $("#adminDropdownIcon").removeClass("fa-caret-up").addClass("fa-caret-down");
    });
    // bar management
    $("#currentBarNavdrop").on("shown.bs.collapse", function() {
        $("#currentBarNavdropIcon").removeClass("fa-caret-down").addClass("fa-caret-up");
    });
    $("#currentBarNavdrop").on("hidden.bs.collapse", function() {
        $("#currentBarNavdropIcon").removeClass("fa-caret-up").addClass("fa-caret-down");
    });
    $("#currentBarDropdown").on("shown.bs.dropdown", function() {
        $("#currentBarDropdownIcon").removeClass("fa-caret-down").addClass("fa-caret-up");
    });
    $("#currentBarDropdown").on("hidden.bs.dropdown", function() {
        $("#currentBarDropdownIcon").removeClass("fa-caret-up").addClass("fa-caret-down");
    });
});
