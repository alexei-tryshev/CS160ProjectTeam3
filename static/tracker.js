// Quick-add buttons fill in a form field; the user still presses Save.
document.querySelectorAll("button[data-amount]").forEach(function (button) {
    button.addEventListener("click", function () {
        var input = button.form.elements[button.dataset.target];
        input.value = button.dataset.amount;
        input.focus();
    });
});
