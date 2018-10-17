/* Collapse remember
 * Use a cookie to "remember" the state of bootstrap collapse divs
 * use the 'collapse-remember' class to get this functionality
 */
$(document).ready(function () {
    const state_cookie_c = 'collapse-remember';
    var page = window.location.pathname;
    var state = Cookies.getJSON(state_cookie_c);
    if (state === undefined) {
        state = {};
        Cookies.set(state_cookie_c, state);
    }
    if (state.hasOwnProperty(page)) {
        Object.keys(state[page]).forEach(function (collapse_id) {
            if (state[page][collapse_id] === true) {
                $('#'+collapse_id).collapse('show');
            }
            else if (state[page][collapse_id] === false) {
                $('#'+collapse_id).collapse('hide');
            }
        });
    }
    $(".collapse-remember").on('shown.bs.collapse', function () {
        state = Cookies.getJSON(state_cookie_c);
        if (state[page] === undefined) {
            state[page] = {};
        }
        var id = $(this).attr('id');
        state[page][id] = true;
        Cookies.set(state_cookie_c, state);
    });
    $(".collapse-remember").on('hidden.bs.collapse', function () {
        state = Cookies.getJSON(state_cookie_c);
        if (state[page] === undefined) {
            state[page] = {};
        }
        var id = $(this).attr('id');
        state[page][id] = false;
        Cookies.set(state_cookie_c, state);
    });
});
