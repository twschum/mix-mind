
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
    // admin selector
    $("#adminNavdrop").on("shown.bs.collapse", function() {
        $("#adminNavdropIcon").removeClass("fa-caret-down").addClass("fa-caret-up");
    });
    $("#adminNavdrop").on("hidden.bs.collapse", function() {
        $("#adminNavdropIcon").removeClass("fa-caret-up").addClass("fa-caret-down");
    });
});
